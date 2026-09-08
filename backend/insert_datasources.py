import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import AsyncSessionLocal

new_sources = [
    {
        "dataset_name": "DATA_GOV_IN_MORTH_EXPENDITURE",
        "description": "State-wise LA expenditure data from MoRTH via data.gov.in. Fields: state, year, expenditure_crore, area_acquired_ha.",
        "source_organization": "Open Government Data Platform India (data.gov.in)",
        "source_url": "https://data.gov.in/catalog/morth-la-expenditure-state-wise",
        "data_status": "OFFICIAL_PUBLIC",
        "file_format": "JSON (REST API)",
        "license": "Government Open Data License",
        "record_count": 350,
        "fields_obtained": ["state", "year", "expenditure_crore", "area_acquired_ha"],
    },
    {
        "dataset_name": "DATA_GOV_IN_NH_STATUS",
        "description": "NH project-wise land acquisition status via data.gov.in.",
        "source_organization": "Open Government Data Platform India (data.gov.in)",
        "source_url": "https://data.gov.in/catalog/nh-project-wise-land-acquisition-status",
        "data_status": "OFFICIAL_PUBLIC",
        "file_format": "JSON (REST API)",
        "license": "Government Open Data License",
        "record_count": 2500,
        "fields_obtained": ["project_name", "nh_number", "state", "total_area_ha", "area_acquired_ha", "notification_3a_date", "notification_3d_date"],
    },
    {
        "dataset_name": "DATA_GOV_IN_NH_LENGTH",
        "description": "National highway length state-wise via data.gov.in.",
        "source_organization": "Open Government Data Platform India (data.gov.in)",
        "source_url": "https://data.gov.in/catalog/national-highway-length-state-wise",
        "data_status": "OFFICIAL_PUBLIC",
        "file_format": "JSON (REST API)",
        "license": "Government Open Data License",
        "record_count": 36,
        "fields_obtained": ["state", "total_nh_length_km", "year"],
    },
    {
        "dataset_name": "CENSUS_2011_DISTRICT",
        "description": "Census India Primary Census Abstract (PCA) 2011 for district-level population and area data.",
        "source_organization": "Census of India",
        "source_url": "https://censusindia.gov.in/nada/index.php/catalog/42626",
        "data_status": "OFFICIAL_PUBLIC",
        "file_format": "CSV",
        "license": "Government Open Data License",
        "record_count": 640,
        "fields_obtained": ["district_code", "district_name", "state_code", "Total_Population", "Rural_Population", "Urban_Population", "Area_sq_km"],
    }
]

async def main():
    async with AsyncSessionLocal() as session:
        for ds in new_sources:
            query = text("""
                INSERT INTO data_sources (
                    dataset_name, description, source_organization, source_url, 
                    data_status, file_format, license, record_count, fields_obtained
                ) VALUES (
                    :dataset_name, :description, :source_organization, :source_url,
                    CAST(:data_status AS data_status), :file_format, :license, :record_count, :fields_obtained
                )
                ON CONFLICT (dataset_name) DO UPDATE SET
                    description = EXCLUDED.description,
                    source_organization = EXCLUDED.source_organization,
                    source_url = EXCLUDED.source_url,
                    data_status = EXCLUDED.data_status,
                    file_format = EXCLUDED.file_format,
                    license = EXCLUDED.license,
                    record_count = EXCLUDED.record_count,
                    fields_obtained = EXCLUDED.fields_obtained
            """)
            await session.execute(query, ds)
            print(f"Upserted {ds['dataset_name']}")
        
        await session.commit()
        print("Commit complete.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
