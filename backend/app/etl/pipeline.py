"""
LADRIS — Master ETL Pipeline
===================================
Orchestrates ingestion from all real government data sources:

  Phase 1 — GIS & Census (fastest, fully offline from bundled files)
  Phase 2 — data.gov.in API (requires DATA_GOV_IN_API_KEY in .env)
  Phase 3 — BhoomiRashi Scraper (public web scraping, no login needed)
  Phase 4 — Normalize & Deduplicate all project records
  Phase 5 — Upsert everything into PostgreSQL

Run with: python run_etl.py
Or:       python run_etl.py --phases 1,2,3
Or:       python run_etl.py --phases 2 (only data.gov.in)
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database import AsyncSessionLocal
from app.config import get_settings

from app.etl.bhoomirashi_scraper import run_all_states as scrape_bhoomirashi
from app.etl.data_gov_in import DataGovInClient
from app.etl.gis_census_loader import (
    load_district_centroids,
    load_district_centroids_from_geojson,
    load_census_data,
)
from app.etl.normalizer import normalize_project, deduplicate_projects
from app.etl.db_loader import upsert_projects, upsert_districts, get_real_data_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ladris.etl")


class ETLPipeline:
    def __init__(self, phases: Optional[List[int]] = None):
        self.settings = get_settings()
        self.phases = phases or [1, 2, 3, 4, 5]
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.stats: Dict[str, Any] = {
            "run_id": self.run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "phases_run": self.phases,
        }

    async def run(self):
        logger.info(f"=" * 60)
        logger.info(f"LADRIS ETL Pipeline — Run ID: {self.run_id}")
        logger.info(f"Phases: {self.phases}")
        logger.info(f"=" * 60)

        all_projects: List[Dict[str, Any]] = []
        district_map: Dict[str, Any] = {}

        # ─── Phase 1: GIS & Census ───────────────────────────────────────────
        if 1 in self.phases:
            logger.info("\n[Phase 1] Loading GIS District Centroids & Census 2011...")
            start = time.time()

            # Load district centroids (try CSV first, then GeoJSON, then fallback)
            districts = load_district_centroids()
            if not districts:
                logger.info("  Falling back to GeoJSON centroid computation...")
                districts = load_district_centroids_from_geojson()

            # Load Census data
            census_records = load_census_data()

            # Merge census into district records
            census_map = {
                r["district_code"]: r for r in census_records if r.get("district_code")
            }
            for d in districts:
                code = d.get("district_code", "")
                if code in census_map:
                    d.update({
                        "total_population": census_map[code].get("total_population", 0),
                        "rural_population": census_map[code].get("rural_population", 0),
                        "urban_population": census_map[code].get("urban_population", 0),
                        "total_households": census_map[code].get("total_households", 0),
                        "area_sq_km": census_map[code].get("area_sq_km"),
                    })

            # Build lookup map for normalizer
            district_map = {
                d.get("district_name", "").lower(): d for d in districts
            }

            # Upsert districts
            if districts:
                async with AsyncSessionLocal() as db:
                    count = await upsert_districts(db, districts)
                    self.stats["districts_upserted"] = count

            elapsed = time.time() - start
            logger.info(f"  Phase 1 complete: {len(districts)} districts, {len(census_records)} census records ({elapsed:.1f}s)")

        # ─── Phase 2: data.gov.in API ─────────────────────────────────────────
        if 2 in self.phases:
            logger.info("\n[Phase 2] Fetching data.gov.in Open Datasets...")
            start = time.time()

            api_key = self.settings.DATAGOV_API_KEY
            if not api_key:
                logger.warning(
                    "  DATA_GOV_IN_API_KEY not set in .env — skipping Phase 2.\n"
                    "  → Register at https://data.gov.in and add the key to .env"
                )
                self.stats["data_gov_in"] = "SKIPPED_NO_API_KEY"
            else:
                client = DataGovInClient(api_key=api_key)
                data = client.fetch_all()

                # Use NH LA status as primary project source from data.gov.in
                nh_projects = data.get("nh_la_status", [])
                all_projects.extend(nh_projects)

                # Store expenditure data for analytics enrichment
                self.stats["data_gov_in"] = {
                    "nh_projects": len(nh_projects),
                    "expenditure_records": len(data.get("morth_la_expenditure", [])),
                    "nh_length_records": len(data.get("nh_length_statewise", [])),
                }
                elapsed = time.time() - start
                logger.info(f"  Phase 2 complete: {len(nh_projects)} NH projects from data.gov.in ({elapsed:.1f}s)")

        # ─── Phase 3: BhoomiRashi Scraper ─────────────────────────────────────
        if 3 in self.phases:
            logger.info("\n[Phase 3] Scraping BhoomiRashi Public Highway Register...")
            logger.info("  This may take 10–15 minutes for all states. Ctrl+C to stop early.")
            start = time.time()

            try:
                bhoomirashi_projects = scrape_bhoomirashi(
                    agencies=["NHAI", "NHIDCL", "MoRTH"],
                    delay_seconds=2.0,
                    max_projects_per_state=500,
                )
                all_projects.extend(bhoomirashi_projects)
                elapsed = time.time() - start
                self.stats["bhoomirashi"] = {
                    "raw_projects": len(bhoomirashi_projects),
                    "elapsed_seconds": round(elapsed, 1),
                }
                logger.info(f"  Phase 3 complete: {len(bhoomirashi_projects)} projects scraped ({elapsed:.1f}s)")
            except KeyboardInterrupt:
                logger.warning("  BhoomiRashi scrape interrupted by user — using partial data")

        # ─── Phase 4: Normalize & Deduplicate ────────────────────────────────
        if 4 in self.phases and all_projects:
            logger.info(f"\n[Phase 4] Normalizing {len(all_projects)} raw records...")
            start = time.time()

            normalized = []
            skipped = 0
            for raw in all_projects:
                result = normalize_project(raw, district_map=district_map)
                if result:
                    normalized.append(result)
                else:
                    skipped += 1

            deduped = deduplicate_projects(normalized)
            elapsed = time.time() - start
            self.stats["normalization"] = {
                "raw": len(all_projects),
                "normalized": len(normalized),
                "deduplicated": len(deduped),
                "skipped": skipped,
            }
            logger.info(
                f"  Phase 4 complete: {len(all_projects)} raw → "
                f"{len(normalized)} normalized → {len(deduped)} unique ({elapsed:.1f}s)"
            )
            all_projects = deduped

        # ─── Phase 5: Database Upsert ─────────────────────────────────────────
        if 5 in self.phases and all_projects:
            logger.info(f"\n[Phase 5] Upserting {len(all_projects)} projects to PostgreSQL...")
            start = time.time()

            async with AsyncSessionLocal() as db:
                result = await upsert_projects(db, all_projects)
                self.stats["db_upsert"] = result

                # Print final summary
                summary = await get_real_data_summary(db)
                self.stats["final_db_state"] = summary

            elapsed = time.time() - start
            logger.info(f"  Phase 5 complete ({elapsed:.1f}s)")

        # ─── Final Report ─────────────────────────────────────────────────────
        self.stats["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("\n" + "=" * 60)
        logger.info("ETL PIPELINE COMPLETE")
        logger.info("=" * 60)

        if "normalization" in self.stats:
            n = self.stats["normalization"]
            logger.info(f"  Raw records processed : {n['raw']}")
            logger.info(f"  Unique projects loaded: {n['deduplicated']}")
            logger.info(f"  Records skipped       : {n['skipped']}")

        if "db_upsert" in self.stats:
            u = self.stats["db_upsert"]
            logger.info(f"  DB upsert success     : {u.get('inserted', 0)}")
            logger.info(f"  DB upsert errors      : {u.get('errors', 0)}")

        if "districts_upserted" in self.stats:
            logger.info(f"  Districts loaded      : {self.stats['districts_upserted']}")

        return self.stats
