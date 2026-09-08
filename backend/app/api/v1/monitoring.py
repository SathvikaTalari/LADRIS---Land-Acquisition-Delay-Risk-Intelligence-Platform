"""
LADRIS — API v1: Model Monitoring
=========================================
Exposes model monitoring summary statistics.
Access restricted to analyst-level users and above.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.dependencies import require_analyst
from app.models.user import User

monitoring_router = APIRouter(prefix="/monitoring", tags=["Model Monitoring"])


@monitoring_router.get("/summary")
async def get_monitoring_summary(
    current_user: User = Depends(require_analyst),
) -> Dict[str, Any]:
    """
    Get model monitoring summary.

    Returns rolling statistics from the prediction log:
    - prediction_count, eligible_count, ineligible_count
    - missing_data_rate
    - anomaly_rate (fraction scoring > 60%)
    - feature distribution snapshot
    - model_version distribution

    Does NOT trigger automatic retraining.
    Requires analyst-level access or higher.
    """
    from ml.monitoring.model_monitor import get_monitoring_summary
    return get_monitoring_summary()


@monitoring_router.get("/data-gap-report")
async def get_data_gap_report(
    current_user: User = Depends(require_analyst),
) -> Dict[str, Any]:
    """
    Return the documented data gap report explaining why supervised
    delay prediction training is currently deferred.
    """
    import json
    import sys
    from pathlib import Path

    BACKEND_DIR = Path(__file__).parent.parent.parent.parent
    ROOT_DIR = BACKEND_DIR.parent
    ML_DIR = Path("/ml") if Path("/ml").exists() else (ROOT_DIR / "ml")
    report_path = ML_DIR / "data" / "processed" / "data_gap_report.json"

    if report_path.exists():
        return json.loads(report_path.read_text(encoding="utf-8"))

    return {
        "status": "report_not_generated",
        "message": "Run ml/training/data_gap_report.py to generate the report.",
    }
