#!/usr/bin/env python
"""
LADRIS — ETL Runner
==========================
Run this script to ingest real data from government sources.

Usage:
    python run_etl.py                    # run all phases
    python run_etl.py --phases 1         # only GIS/Census
    python run_etl.py --phases 1,2       # GIS + data.gov.in only
    python run_etl.py --phases 3,4,5     # BhoomiRashi + normalize + DB
    python run_etl.py --dry-run          # validate without writing to DB

Credentials needed (set in .env BEFORE running):
    DATA_GOV_IN_API_KEY = <your key from data.gov.in>

No credentials needed for:
    Phase 1 — Census/GIS files (bundled in data/)
    Phase 3 — BhoomiRashi (public web scraping, no login)
"""

import argparse
import asyncio
import json
import sys
import os

# Ensure project root on path
sys.path.insert(0, os.path.dirname(__file__))

from app.etl.pipeline import ETLPipeline


def parse_args():
    parser = argparse.ArgumentParser(
        description="LADRIS Real Data ETL Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--phases",
        type=str,
        default="1,2,3,4,5",
        help="Comma-separated list of phases to run (1=GIS/Census, 2=data.gov.in, 3=BhoomiRashi, 4=Normalize, 5=DB)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing to database (validate only)",
    )
    parser.add_argument(
        "--states",
        type=str,
        default="ALL",
        help="Comma-separated state codes to scrape, or ALL (default: ALL)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    # Parse phases
    try:
        phases = [int(p.strip()) for p in args.phases.split(",")]
    except ValueError:
        print(f"Invalid --phases argument: {args.phases}")
        sys.exit(1)

    if args.dry_run:
        # In dry-run, skip DB phase
        phases = [p for p in phases if p != 5]
        print("[DRY RUN MODE] Phase 5 (DB upsert) will be skipped.")

    print(f"\nLADRIS ETL -- Phases: {phases}")
    print("=" * 60)
    print("\n[CREDENTIALS NEEDED]")
    print("   Phase 2 (data.gov.in): Set DATA_GOV_IN_API_KEY in backend/.env")
    print("                           Register free at: https://data.gov.in")
    print("   Phase 3 (BhoomiRashi): No login needed (public web scraping)")
    print("   Phase 1 (GIS/Census): No internet needed (bundled data files)")
    print("\n[DATA FILES EXPECTED AT]")
    print("   backend/data/census/district_census_2011.csv")
    print("   backend/data/gis/india_districts_centroids.csv")
    print("   backend/data/gis/india_districts.geojson")
    print("\n   If missing, Phase 1 will use state-level coordinate fallback.")
    print("=" * 60)

    pipeline = ETLPipeline(phases=phases)
    stats = await pipeline.run()

    print("\n[RUN STATISTICS]")
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
