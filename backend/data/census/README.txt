Place Census 2011 district CSV file here.

Filename: district_census_2011.csv

Download from:
  Census India Primary Census Abstract (PCA):
  https://censusindia.gov.in/nada/index.php/catalog/42626
  → Download "District Level" → "Primary Census Abstract"

Expected CSV format (minimum required columns):
  district_code, district_name, state_code, state_name,
  Total_Population, Rural_Population, Urban_Population,
  Total_Households, Area_sq_km

NOTE: If this file is absent, ETL Phase 1 will skip population enrichment
but district centroids will still be loaded from the GIS file.
