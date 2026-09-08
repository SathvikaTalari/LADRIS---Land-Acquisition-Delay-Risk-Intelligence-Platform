"""
LADRIS — Tests: Data Sources Registry API
"""

import pytest


def test_data_source_structure():
    sample = {
        "id": "ds-0001",
        "dataset_name": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "source_organization": "Ministry of Road Transport and Highways (MoRTH)",
        "data_status": "OFFICIAL_PUBLIC",
        "record_count": 56,
        "fields_obtained": [
            "state", "district", "agency", "land_required_ha",
            "sanctioned_la_cost_crore", "notification_3a_date", "notification_3d_date"
        ],
    }
    assert sample["data_status"] == "OFFICIAL_PUBLIC"
    assert len(sample["fields_obtained"]) == 7
