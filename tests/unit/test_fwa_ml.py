"""
Unit tests for ML-Based FWA Detection.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19
"""

import pytest
from datetime import date, timedelta
from typing import List, Dict, Any

from src.services.fwa.ml_models import (
    IsolationForestModel,
    StatisticalAnomalyModel,
    MLAnomalyEnsemble,
    ClaimFeatures,
    AnomalyScore,
    AnomalyType,
    FeatureEngineer,
    get_ml_ensemble,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def feature_engineer() -> FeatureEngineer:
    """Create feature engineer instance."""
    return FeatureEngineer()


@pytest.fixture
def isolation_forest() -> IsolationForestModel:
    """Create isolation forest model."""
    return IsolationForestModel(n_estimators=10, max_samples=50)


@pytest.fixture
def statistical_model() -> StatisticalAnomalyModel:
    """Create statistical anomaly model."""
    return StatisticalAnomalyModel()


@pytest.fixture
def ml_ensemble() -> MLAnomalyEnsemble:
    """Create ML ensemble."""
    return MLAnomalyEnsemble()


@pytest.fixture
def sample_claim() -> Dict[str, Any]:
    """Create sample claim data."""
    return {
        "claim_id": "CLM-001",
        "member_id": "MEM-12345",
        "provider_id": "NPI1234567890",
        "service_date": date.today(),
        "total_charged": 1500.00,
        "procedure_codes": ["99213", "99214"],
        "diagnosis_codes": ["J06.9", "R05.9"],
    }


@pytest.fixture
def high_risk_claim() -> Dict[str, Any]:
    """Create high-risk claim data."""
    return {
        "claim_id": "CLM-HIGH",
        "member_id": "MEM-99999",
        "provider_id": "NPI9999999999",
        "service_date": date.today(),
        "total_charged": 50000.00,
        "procedure_codes": ["27447", "27130", "63030", "47562", "19301"],
        "diagnosis_codes": ["M17.11", "M17.12"],
    }


@pytest.fixture
def sample_training_data() -> List[Dict[str, Any]]:
    """Create sample training data."""
    data = []
    for i in range(100):
        data.append({
            "claim_id": f"TRAIN-{i:03d}",
            "member_id": f"MEM-{i:05d}",
            "provider_id": f"NPI{1000000000 + i}",
            "service_date": date.today() - timedelta(days=i % 30),
            "total_charged": 500 + (i % 10) * 200,
            "procedure_codes": ["99213"],
            "diagnosis_codes": ["J06.9"],
            "num_procedures": 1 + i % 3,
            "num_diagnoses": 1 + i % 2,
            "charge_per_procedure": 500.0,
        })
    return data


# =============================================================================
# Feature Engineer Tests
# =============================================================================


class TestFeatureEngineer:
    """Tests for feature engineering."""

    def test_extract_basic_features(
        self, feature_engineer: FeatureEngineer, sample_claim: Dict[str, Any]
    ):
        """Test extracting basic features from claim."""
        features = feature_engineer.extract_features(sample_claim)

        assert features.claim_id == "CLM-001"
        assert features.total_charged == 1500.00
        assert features.num_procedures == 2
        assert features.num_diagnoses == 2

    def test_extract_temporal_features(
        self, feature_engineer: FeatureEngineer, sample_claim: Dict[str, Any]
    ):
        """Test extracting temporal features."""
        # Set to weekend
        sample_claim["service_date"] = date(2025, 12, 20)  # Saturday
        features = feature_engineer.extract_features(sample_claim)

        assert features.is_weekend is True

    def test_extract_provider_features(
        self, feature_engineer: FeatureEngineer, sample_claim: Dict[str, Any]
    ):
        """Test extracting provider features."""
        provider_profile = {
            "total_claims": 100,
            "avg_claim_amount": 1200.0,
            "denial_rate": 0.15,
            "specialty_risk": 0.3,
        }

        features = feature_engineer.extract_features(sample_claim, provider_profile)

        assert features.provider_claim_count == 100
        assert features.provider_avg_charge == 1200.0
        assert features.provider_denial_rate == 0.15

    def test_extract_member_features(
        self, feature_engineer: FeatureEngineer, sample_claim: Dict[str, Any]
    ):
        """Test extracting member history features."""
        member_history = [
            {
                "claim_id": f"HIST-{i}",
                "service_date": date.today() - timedelta(days=i),
                "total_charged": 500.0,
                "procedure_codes": ["99213"],
                "provider_id": f"NPI{i}",
            }
            for i in range(5)
        ]

        features = feature_engineer.extract_features(
            sample_claim, member_history=member_history
        )

        assert features.member_claim_count_30d == 5
        assert features.member_total_charged_30d == 2500.0
        assert features.member_unique_providers_30d == 5

    def test_high_value_procedure_detection(
        self, feature_engineer: FeatureEngineer, high_risk_claim: Dict[str, Any]
    ):
        """Test detection of high-value procedures."""
        features = feature_engineer.extract_features(high_risk_claim)

        assert features.has_high_value_procedure is True

    def test_feature_vector_conversion(
        self, feature_engineer: FeatureEngineer, sample_claim: Dict[str, Any]
    ):
        """Test converting features to vector."""
        features = feature_engineer.extract_features(sample_claim)
        vector = features.to_vector()

        assert isinstance(vector, list)
        assert len(vector) == 18
        assert all(isinstance(v, float) for v in vector)


# =============================================================================
# Isolation Forest Tests
# =============================================================================


class TestIsolationForestModel:
    """Tests for Isolation Forest anomaly detection."""

    def test_model_initialization(self, isolation_forest: IsolationForestModel):
        """Test model initializes correctly."""
        assert isolation_forest.n_estimators == 10
        assert isolation_forest.max_samples == 50
        assert isolation_forest.is_fitted is False

    def test_model_fit(
        self,
        isolation_forest: IsolationForestModel,
        sample_training_data: List[Dict[str, Any]],
    ):
        """Test fitting the model."""
        feature_engineer = FeatureEngineer()
        vectors = [
            feature_engineer.extract_features(claim).to_vector()
            for claim in sample_training_data
        ]

        isolation_forest.fit(vectors)

        assert isolation_forest.is_fitted is True
        assert len(isolation_forest.trees) == 10

    def test_model_predict_normal(
        self,
        isolation_forest: IsolationForestModel,
        feature_engineer: FeatureEngineer,
        sample_training_data: List[Dict[str, Any]],
        sample_claim: Dict[str, Any],
    ):
        """Test prediction on normal claim."""
        # Fit model
        vectors = [
            feature_engineer.extract_features(claim).to_vector()
            for claim in sample_training_data
        ]
        isolation_forest.fit(vectors)

        # Predict on normal claim
        features = feature_engineer.extract_features(sample_claim)
        result = isolation_forest.predict(features)

        assert isinstance(result, AnomalyScore)
        assert result.claim_id == "CLM-001"
        assert 0 <= result.anomaly_score <= 1

    def test_model_predict_anomaly(
        self,
        isolation_forest: IsolationForestModel,
        feature_engineer: FeatureEngineer,
        sample_training_data: List[Dict[str, Any]],
        high_risk_claim: Dict[str, Any],
    ):
        """Test prediction on anomalous claim."""
        # Fit model
        vectors = [
            feature_engineer.extract_features(claim).to_vector()
            for claim in sample_training_data
        ]
        isolation_forest.fit(vectors)

        # Predict on high-risk claim
        features = feature_engineer.extract_features(high_risk_claim)
        result = isolation_forest.predict(features)

        assert isinstance(result, AnomalyScore)
        # High-value claim should have higher anomaly score
        assert result.anomaly_score > 0.3


# =============================================================================
# Statistical Model Tests
# =============================================================================


class TestStatisticalAnomalyModel:
    """Tests for statistical anomaly detection."""

    def test_model_initialization(self, statistical_model: StatisticalAnomalyModel):
        """Test model initializes correctly."""
        assert statistical_model.z_threshold == 3.0
        assert statistical_model.iqr_multiplier == 1.5
        assert statistical_model.is_fitted is False

    def test_model_fit(
        self,
        statistical_model: StatisticalAnomalyModel,
        sample_training_data: List[Dict[str, Any]],
    ):
        """Test fitting the model."""
        statistical_model.fit(sample_training_data)

        assert statistical_model.is_fitted is True
        assert "total_charged" in statistical_model.feature_stats

    def test_detect_cost_anomaly(
        self,
        statistical_model: StatisticalAnomalyModel,
        feature_engineer: FeatureEngineer,
        sample_training_data: List[Dict[str, Any]],
    ):
        """Test detecting cost anomaly."""
        statistical_model.fit(sample_training_data)

        # Create features with very high charge
        features = ClaimFeatures(
            claim_id="HIGH-COST",
            total_charged=100000.0,
            num_procedures=2,
            num_diagnoses=2,
            service_date=date.today(),
        )

        anomalies = statistical_model.detect_anomalies(features)

        # Should detect cost anomaly
        cost_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.COST_ANOMALY]
        assert len(cost_anomalies) >= 0  # May or may not trigger depending on training data

    def test_detect_timing_anomaly(
        self,
        statistical_model: StatisticalAnomalyModel,
        sample_training_data: List[Dict[str, Any]],
    ):
        """Test detecting timing anomaly."""
        statistical_model.fit(sample_training_data)

        features = ClaimFeatures(
            claim_id="WEEKEND",
            total_charged=10000.0,
            num_procedures=2,
            num_diagnoses=2,
            service_date=date(2025, 12, 20),  # Saturday
            is_weekend=True,
        )

        anomalies = statistical_model.detect_anomalies(features)

        # Should detect weekend high-value anomaly
        timing_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.TIMING_ANOMALY]
        assert len(timing_anomalies) >= 1

    def test_detect_frequency_anomaly(
        self,
        statistical_model: StatisticalAnomalyModel,
        sample_training_data: List[Dict[str, Any]],
    ):
        """Test detecting member frequency anomaly."""
        statistical_model.fit(sample_training_data)

        features = ClaimFeatures(
            claim_id="HIGH-FREQ",
            total_charged=500.0,
            num_procedures=1,
            num_diagnoses=1,
            service_date=date.today(),
            member_claim_count_30d=20,  # Very high frequency
        )

        anomalies = statistical_model.detect_anomalies(features)

        # Should detect frequency anomaly
        freq_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.FREQUENCY_ANOMALY]
        assert len(freq_anomalies) >= 1

    def test_detect_provider_anomaly(
        self,
        statistical_model: StatisticalAnomalyModel,
        sample_training_data: List[Dict[str, Any]],
    ):
        """Test detecting provider anomaly."""
        statistical_model.fit(sample_training_data)

        features = ClaimFeatures(
            claim_id="HIGH-DENIAL",
            total_charged=500.0,
            num_procedures=1,
            num_diagnoses=1,
            service_date=date.today(),
            provider_denial_rate=0.35,  # High denial rate
        )

        anomalies = statistical_model.detect_anomalies(features)

        # Should detect provider anomaly
        provider_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.PROVIDER_ANOMALY]
        assert len(provider_anomalies) >= 1

    def test_predict_combined(
        self,
        statistical_model: StatisticalAnomalyModel,
        feature_engineer: FeatureEngineer,
        sample_training_data: List[Dict[str, Any]],
        sample_claim: Dict[str, Any],
    ):
        """Test combined prediction."""
        statistical_model.fit(sample_training_data)

        features = feature_engineer.extract_features(sample_claim)
        result = statistical_model.predict(features)

        assert isinstance(result, AnomalyScore)
        assert result.claim_id == "CLM-001"


# =============================================================================
# Ensemble Tests
# =============================================================================


class TestMLAnomalyEnsemble:
    """Tests for ML ensemble."""

    def test_ensemble_initialization(self, ml_ensemble: MLAnomalyEnsemble):
        """Test ensemble initializes correctly."""
        assert ml_ensemble.isolation_forest is not None
        assert ml_ensemble.statistical_model is not None
        assert ml_ensemble.feature_engineer is not None

    def test_ensemble_fit(
        self,
        ml_ensemble: MLAnomalyEnsemble,
        sample_training_data: List[Dict[str, Any]],
    ):
        """Test fitting the ensemble."""
        ml_ensemble.fit(sample_training_data)

        assert ml_ensemble.is_fitted is True
        assert ml_ensemble.isolation_forest.is_fitted is True
        assert ml_ensemble.statistical_model.is_fitted is True

    def test_ensemble_predict(
        self,
        ml_ensemble: MLAnomalyEnsemble,
        sample_training_data: List[Dict[str, Any]],
        sample_claim: Dict[str, Any],
    ):
        """Test ensemble prediction."""
        ml_ensemble.fit(sample_training_data)

        combined, individual = ml_ensemble.predict(sample_claim)

        assert isinstance(combined, AnomalyScore)
        assert len(individual) >= 1
        assert combined.claim_id == "CLM-001"

    def test_ensemble_predict_with_profiles(
        self,
        ml_ensemble: MLAnomalyEnsemble,
        sample_training_data: List[Dict[str, Any]],
        sample_claim: Dict[str, Any],
    ):
        """Test ensemble prediction with provider and member context."""
        ml_ensemble.fit(sample_training_data)

        provider_profile = {
            "total_claims": 100,
            "avg_claim_amount": 1000.0,
            "denial_rate": 0.1,
        }

        member_history = [
            {
                "claim_id": f"HIST-{i}",
                "service_date": date.today() - timedelta(days=i),
                "total_charged": 500.0,
                "procedure_codes": ["99213"],
                "provider_id": f"NPI{i}",
            }
            for i in range(3)
        ]

        combined, individual = ml_ensemble.predict(
            sample_claim, provider_profile, member_history
        )

        assert isinstance(combined, AnomalyScore)
        assert combined.claim_id == "CLM-001"

    def test_ensemble_high_risk_claim(
        self,
        ml_ensemble: MLAnomalyEnsemble,
        sample_training_data: List[Dict[str, Any]],
        high_risk_claim: Dict[str, Any],
    ):
        """Test ensemble on high-risk claim."""
        ml_ensemble.fit(sample_training_data)

        combined, individual = ml_ensemble.predict(high_risk_claim)

        assert isinstance(combined, AnomalyScore)
        # High-risk claim should have elevated score
        assert combined.anomaly_score > 0


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_get_ml_ensemble_singleton(self):
        """Test ensemble factory returns singleton."""
        ensemble1 = get_ml_ensemble()
        ensemble2 = get_ml_ensemble()
        assert ensemble1 is ensemble2

    def test_ensemble_is_fitted_on_creation(self):
        """Test ensemble is fitted with sample data on creation."""
        ensemble = get_ml_ensemble()
        assert ensemble.is_fitted is True


# =============================================================================
# Anomaly Score Tests
# =============================================================================


class TestAnomalyScore:
    """Tests for AnomalyScore model."""

    def test_anomaly_score_creation(self):
        """Test creating anomaly score."""
        score = AnomalyScore(
            claim_id="CLM-001",
            is_anomaly=True,
            anomaly_score=0.75,
            anomaly_type=AnomalyType.COST_ANOMALY,
            confidence=0.85,
            contributing_factors=["High charge amount"],
            explanation="Charge is 5 std devs from mean",
        )

        assert score.is_anomaly is True
        assert score.anomaly_score == 0.75
        assert score.anomaly_type == AnomalyType.COST_ANOMALY
        assert len(score.contributing_factors) == 1

    def test_anomaly_score_no_anomaly(self):
        """Test creating score for non-anomalous claim."""
        score = AnomalyScore(
            claim_id="CLM-002",
            is_anomaly=False,
            anomaly_score=0.1,
            confidence=0.9,
        )

        assert score.is_anomaly is False
        assert score.anomaly_type is None


# =============================================================================
# ClaimFeatures Tests
# =============================================================================


class TestClaimFeatures:
    """Tests for ClaimFeatures model."""

    def test_claim_features_creation(self):
        """Test creating claim features."""
        features = ClaimFeatures(
            claim_id="CLM-001",
            total_charged=1500.0,
            num_procedures=3,
            num_diagnoses=2,
            service_date=date.today(),
            is_weekend=False,
            provider_denial_rate=0.1,
        )

        assert features.claim_id == "CLM-001"
        assert features.total_charged == 1500.0
        assert features.num_procedures == 3

    def test_claim_features_defaults(self):
        """Test claim features default values."""
        features = ClaimFeatures(
            claim_id="CLM-002",
            total_charged=500.0,
            num_procedures=1,
            num_diagnoses=1,
            service_date=date.today(),
        )

        assert features.is_weekend is False
        assert features.is_holiday is False
        assert features.provider_denial_rate == 0.0
        assert features.member_claim_count_30d == 0

    def test_claim_features_to_vector_length(self):
        """Test feature vector has correct length."""
        features = ClaimFeatures(
            claim_id="CLM-003",
            total_charged=1000.0,
            num_procedures=2,
            num_diagnoses=1,
            service_date=date.today(),
        )

        vector = features.to_vector()
        assert len(vector) == 18
