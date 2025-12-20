"""
Fraud, Waste, and Abuse (FWA) Detection Services.
Source: Design Document Section 4.2 - Fraud Detection
Verified: 2025-12-18

Provides comprehensive FWA detection including duplicate detection,
upcoding detection, pattern analysis, and ML-based risk scoring.
"""

from src.services.fwa.duplicate_detector import (
    DuplicateDetector,
    get_duplicate_detector,
)
from src.services.fwa.pattern_analyzer import (
    PatternAnalyzer,
    get_pattern_analyzer,
)
from src.services.fwa.upcoding_detector import (
    UpcodingDetector,
    get_upcoding_detector,
)
from src.services.fwa.risk_scorer import (
    FWARiskScorer,
    get_risk_scorer,
)
from src.services.fwa.service import (
    FWAService,
    get_fwa_service,
    create_fwa_service,
)
from src.services.fwa.ml_models import (
    MLAnomalyEnsemble,
    IsolationForestModel,
    StatisticalAnomalyModel,
    ClaimFeatures,
    AnomalyScore,
    AnomalyType,
    FeatureEngineer,
    get_ml_ensemble,
)

__all__ = [
    # Duplicate Detector
    "DuplicateDetector",
    "get_duplicate_detector",
    # Pattern Analyzer
    "PatternAnalyzer",
    "get_pattern_analyzer",
    # Upcoding Detector
    "UpcodingDetector",
    "get_upcoding_detector",
    # Risk Scorer
    "FWARiskScorer",
    "get_risk_scorer",
    # FWA Service
    "FWAService",
    "get_fwa_service",
    "create_fwa_service",
    # ML Models
    "MLAnomalyEnsemble",
    "IsolationForestModel",
    "StatisticalAnomalyModel",
    "ClaimFeatures",
    "AnomalyScore",
    "AnomalyType",
    "FeatureEngineer",
    "get_ml_ensemble",
]
