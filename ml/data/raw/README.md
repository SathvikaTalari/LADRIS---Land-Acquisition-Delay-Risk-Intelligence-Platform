# LandPulse AI ML Raw Data Directory
This directory is intended for raw, un-transformed dataset files ingested from official government portals or public data releases.

**Rules for Raw Data**:
1. Do NOT commit raw dataset files (.csv, .xlsx, .json, .parquet) to Git version control.
2. Every raw dataset placed here MUST be registered in `data_provenance.json` with its official source URL, organization, retrieval date, and license.
3. Synthetic or fake data MUST NOT be placed in this folder or marked as official data.
