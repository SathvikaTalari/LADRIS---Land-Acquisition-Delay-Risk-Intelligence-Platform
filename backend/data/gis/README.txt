Place district centroid CSV file here.

Filename: india_districts_centroids.csv

Download from either:
  A. Datameet India Maps (CC-BY License - Recommended):
     https://github.com/datameet/maps/tree/master/Districts
     → Download districts.geojson and run: python run_etl.py --phases 1

  B. Survey of India Open Maps:
     https://onlinemaps.surveyofindia.gov.in

Expected CSV format (minimum required columns):
  district_code, district_name, state_code, state_name, lat, lng

Example:
  district_code,district_name,state_code,state_name,lat,lng
  101,Mumbai Suburban,MH,Maharashtra,19.1624,72.9120
  102,Pune,MH,Maharashtra,18.5204,73.8567
  ...

NOTE: If this file is absent, ETL Phase 1 will try india_districts.geojson
in this same folder to compute centroids automatically.
If both are absent, state-level fallback coordinates are used.
