"""
ML Models for FWA Detection.

Source: Design Document 06_high_value_enhancements_design.md
Verified: 2025-12-19

Provides machine learning models for fraud, waste, and abuse detection:
- Isolation Forest for anomaly detection
- Statistical anomaly detection
- Feature engineering for claims
"""

import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
import hashlib


class AnomalyType(str, Enum):
    """Types of anomalies detected."""
    BILLING_ANOMALY = "billing_anomaly"
    PATTERN_ANOMALY = "pattern_anomaly"
    FREQUENCY_ANOMALY = "frequency_anomaly"
    COST_ANOMALY = "cost_anomaly"
    TIMING_ANOMALY = "timing_anomaly"
    PROVIDER_ANOMALY = "provider_anomaly"
    CLUSTER_ANOMALY = "cluster_anomaly"


@dataclass
class ClaimFeatures:
    """Engineered features for claim analysis."""

    # Basic claim features
    claim_id: str
    total_charged: float
    num_procedures: int
    num_diagnoses: int
    service_date: date

    # Temporal features
    is_weekend: bool = False
    is_holiday: bool = False
    is_month_end: bool = False
    is_year_end: bool = False
    days_since_last_claim: int = 0

    # Provider features
    provider_id: Optional[str] = None
    provider_claim_count: int = 0
    provider_avg_charge: float = 0.0
    provider_denial_rate: float = 0.0
    provider_specialty_risk: float = 0.0

    # Member features
    member_id: Optional[str] = None
    member_claim_count_30d: int = 0
    member_total_charged_30d: float = 0.0
    member_unique_providers_30d: int = 0
    member_unique_diagnoses_30d: int = 0

    # Procedure features
    has_high_value_procedure: bool = False
    procedure_complexity: float = 0.0
    procedure_modifier_count: int = 0

    # Derived features
    charge_per_procedure: float = 0.0
    diagnosis_procedure_ratio: float = 0.0

    def to_vector(self) -> List[float]:
        """Convert features to numeric vector for ML models."""
        return [
            self.total_charged,
            float(self.num_procedures),
            float(self.num_diagnoses),
            1.0 if self.is_weekend else 0.0,
            1.0 if self.is_holiday else 0.0,
            1.0 if self.is_month_end else 0.0,
            float(self.days_since_last_claim),
            float(self.provider_claim_count),
            self.provider_avg_charge,
            self.provider_denial_rate,
            self.provider_specialty_risk,
            float(self.member_claim_count_30d),
            self.member_total_charged_30d,
            float(self.member_unique_providers_30d),
            1.0 if self.has_high_value_procedure else 0.0,
            self.procedure_complexity,
            self.charge_per_procedure,
            self.diagnosis_procedure_ratio,
        ]


@dataclass
class AnomalyScore:
    """Anomaly detection score."""

    claim_id: str
    is_anomaly: bool
    anomaly_score: float  # 0-1, higher = more anomalous
    anomaly_type: Optional[AnomalyType] = None
    confidence: float = 0.0
    contributing_factors: List[str] = field(default_factory=list)
    explanation: Optional[str] = None


@dataclass
class FeatureStatistics:
    """Statistics for a feature used in anomaly detection."""

    name: str
    mean: float
    std: float
    min_val: float
    max_val: float
    percentile_25: float
    percentile_75: float
    count: int


class IsolationForestModel:
    """
    Isolation Forest-inspired anomaly detection.

    Implements a simplified version of Isolation Forest that works without
    scikit-learn, suitable for claim anomaly detection.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_samples: int = 256,
        contamination: float = 0.1,
        random_seed: int = 42,
    ):
        """
        Initialize Isolation Forest model.

        Args:
            n_estimators: Number of isolation trees
            max_samples: Number of samples per tree
            contamination: Expected proportion of anomalies
            random_seed: Random seed for reproducibility
        """
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.random_seed = random_seed

        self.trees: List[Dict] = []
        self.threshold: float = 0.5
        self.feature_stats: Dict[int, FeatureStatistics] = {}
        self.is_fitted = False

    def _random_split(self, feature_idx: int, min_val: float, max_val: float) -> float:
        """Generate random split point."""
        if max_val == min_val:
            return min_val
        return min_val + random.random() * (max_val - min_val)

    def _build_tree(
        self,
        data: List[List[float]],
        current_depth: int,
        max_depth: int,
    ) -> Dict:
        """Build an isolation tree."""
        n_samples = len(data)

        # Terminal conditions
        if current_depth >= max_depth or n_samples <= 1:
            return {"type": "leaf", "size": n_samples}

        # Random feature selection
        n_features = len(data[0]) if data else 0
        if n_features == 0:
            return {"type": "leaf", "size": n_samples}

        feature_idx = random.randint(0, n_features - 1)

        # Get min/max for selected feature
        feature_values = [row[feature_idx] for row in data]
        min_val = min(feature_values)
        max_val = max(feature_values)

        if min_val == max_val:
            return {"type": "leaf", "size": n_samples}

        # Random split point
        split_value = self._random_split(feature_idx, min_val, max_val)

        # Split data
        left_data = [row for row in data if row[feature_idx] < split_value]
        right_data = [row for row in data if row[feature_idx] >= split_value]

        return {
            "type": "split",
            "feature": feature_idx,
            "threshold": split_value,
            "left": self._build_tree(left_data, current_depth + 1, max_depth),
            "right": self._build_tree(right_data, current_depth + 1, max_depth),
        }

    def fit(self, data: List[List[float]]) -> "IsolationForestModel":
        """
        Fit the model on training data.

        Args:
            data: List of feature vectors

        Returns:
            Self for chaining
        """
        random.seed(self.random_seed)

        n_samples = len(data)
        if n_samples == 0:
            return self

        # Calculate feature statistics
        n_features = len(data[0])
        for i in range(n_features):
            values = sorted([row[i] for row in data])
            self.feature_stats[i] = FeatureStatistics(
                name=f"feature_{i}",
                mean=sum(values) / len(values),
                std=math.sqrt(sum((v - sum(values)/len(values))**2 for v in values) / len(values)),
                min_val=values[0],
                max_val=values[-1],
                percentile_25=values[int(len(values) * 0.25)],
                percentile_75=values[int(len(values) * 0.75)],
                count=len(values),
            )

        # Calculate max depth
        max_depth = int(math.ceil(math.log2(max(self.max_samples, 2))))

        # Build trees
        self.trees = []
        for _ in range(self.n_estimators):
            # Subsample
            sample_size = min(self.max_samples, n_samples)
            sample = random.sample(data, sample_size)

            tree = self._build_tree(sample, 0, max_depth)
            self.trees.append(tree)

        # Set threshold based on contamination
        if data:
            scores = [self._compute_anomaly_score(row) for row in data]
            scores.sort(reverse=True)
            threshold_idx = int(len(scores) * self.contamination)
            self.threshold = scores[threshold_idx] if threshold_idx < len(scores) else 0.5

        self.is_fitted = True
        return self

    def _path_length(self, point: List[float], tree: Dict, current_depth: int) -> float:
        """Compute path length for a point in a tree."""
        if tree["type"] == "leaf":
            # Add average path length for remaining points
            size = tree["size"]
            if size <= 1:
                return float(current_depth)
            else:
                # Harmonic number approximation
                c = 2 * (math.log(size - 1) + 0.5772156649) - 2 * (size - 1) / size
                return current_depth + c

        feature_idx = tree["feature"]
        threshold = tree["threshold"]

        if point[feature_idx] < threshold:
            return self._path_length(point, tree["left"], current_depth + 1)
        else:
            return self._path_length(point, tree["right"], current_depth + 1)

    def _compute_anomaly_score(self, point: List[float]) -> float:
        """Compute anomaly score for a single point."""
        if not self.trees:
            return 0.5

        # Average path length across trees
        avg_path_length = sum(
            self._path_length(point, tree, 0) for tree in self.trees
        ) / len(self.trees)

        # Normalize using expected path length
        n = self.max_samples
        c_n = 2 * (math.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n

        # Anomaly score (higher = more anomalous)
        if c_n == 0:
            return 0.5
        return 2 ** (-avg_path_length / c_n)

    def predict(self, features: ClaimFeatures) -> AnomalyScore:
        """
        Predict if a claim is anomalous.

        Args:
            features: Claim features

        Returns:
            AnomalyScore with detection results
        """
        point = features.to_vector()
        score = self._compute_anomaly_score(point)
        is_anomaly = score > self.threshold

        # Determine contributing factors
        factors = []
        if features.total_charged > self.feature_stats.get(0, FeatureStatistics("", 0, 1, 0, 0, 0, 0, 0)).percentile_75:
            factors.append("High charge amount")
        if features.num_procedures > 10:
            factors.append("Many procedures")
        if features.is_weekend:
            factors.append("Weekend service")
        if features.provider_denial_rate > 0.2:
            factors.append("High provider denial rate")

        return AnomalyScore(
            claim_id=features.claim_id,
            is_anomaly=is_anomaly,
            anomaly_score=score,
            anomaly_type=AnomalyType.CLUSTER_ANOMALY if is_anomaly else None,
            confidence=min(1.0, score * 1.2),
            contributing_factors=factors,
            explanation=f"Isolation score: {score:.3f}" + (", above threshold" if is_anomaly else ""),
        )


class StatisticalAnomalyModel:
    """
    Statistical anomaly detection using z-scores and IQR.

    Provides interpretable anomaly detection based on statistical measures.
    """

    def __init__(
        self,
        z_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
    ):
        """
        Initialize statistical anomaly model.

        Args:
            z_threshold: Z-score threshold for anomalies
            iqr_multiplier: IQR multiplier for outlier detection
        """
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        self.feature_stats: Dict[str, FeatureStatistics] = {}
        self.is_fitted = False

    def fit(self, claims_data: List[Dict[str, Any]]) -> "StatisticalAnomalyModel":
        """
        Fit model on historical claim data.

        Args:
            claims_data: List of claim dictionaries

        Returns:
            Self for chaining
        """
        if not claims_data:
            return self

        # Calculate statistics for key features
        features_to_track = [
            "total_charged",
            "num_procedures",
            "num_diagnoses",
            "charge_per_procedure",
        ]

        for feature in features_to_track:
            values = []
            for claim in claims_data:
                val = claim.get(feature)
                if val is not None:
                    values.append(float(val))

            if values:
                values.sort()
                n = len(values)
                mean = sum(values) / n
                variance = sum((v - mean) ** 2 for v in values) / n
                std = math.sqrt(variance) if variance > 0 else 1.0

                self.feature_stats[feature] = FeatureStatistics(
                    name=feature,
                    mean=mean,
                    std=std,
                    min_val=values[0],
                    max_val=values[-1],
                    percentile_25=values[int(n * 0.25)],
                    percentile_75=values[int(n * 0.75)],
                    count=n,
                )

        self.is_fitted = True
        return self

    def _z_score(self, value: float, stats: FeatureStatistics) -> float:
        """Calculate z-score for a value."""
        if stats.std == 0:
            return 0.0
        return (value - stats.mean) / stats.std

    def _is_iqr_outlier(self, value: float, stats: FeatureStatistics) -> bool:
        """Check if value is IQR outlier."""
        iqr = stats.percentile_75 - stats.percentile_25
        lower_bound = stats.percentile_25 - self.iqr_multiplier * iqr
        upper_bound = stats.percentile_75 + self.iqr_multiplier * iqr
        return value < lower_bound or value > upper_bound

    def detect_anomalies(self, features: ClaimFeatures) -> List[AnomalyScore]:
        """
        Detect anomalies using statistical methods.

        Args:
            features: Claim features

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Check charge amount
        if "total_charged" in self.feature_stats:
            stats = self.feature_stats["total_charged"]
            z = self._z_score(features.total_charged, stats)
            if abs(z) > self.z_threshold:
                anomalies.append(AnomalyScore(
                    claim_id=features.claim_id,
                    is_anomaly=True,
                    anomaly_score=min(1.0, abs(z) / (self.z_threshold * 2)),
                    anomaly_type=AnomalyType.COST_ANOMALY,
                    confidence=0.8,
                    contributing_factors=[f"Charge z-score: {z:.2f}"],
                    explanation=f"Charge ${features.total_charged:.2f} is {z:.1f} std devs from mean ${stats.mean:.2f}",
                ))

        # Check procedure count
        if "num_procedures" in self.feature_stats:
            stats = self.feature_stats["num_procedures"]
            if self._is_iqr_outlier(features.num_procedures, stats):
                anomalies.append(AnomalyScore(
                    claim_id=features.claim_id,
                    is_anomaly=True,
                    anomaly_score=0.6,
                    anomaly_type=AnomalyType.BILLING_ANOMALY,
                    confidence=0.7,
                    contributing_factors=["Unusual procedure count"],
                    explanation=f"Procedure count {features.num_procedures} outside IQR range [{stats.percentile_25:.0f}, {stats.percentile_75:.0f}]",
                ))

        # Check temporal patterns
        if features.is_weekend and features.total_charged > 5000:
            anomalies.append(AnomalyScore(
                claim_id=features.claim_id,
                is_anomaly=True,
                anomaly_score=0.5,
                anomaly_type=AnomalyType.TIMING_ANOMALY,
                confidence=0.6,
                contributing_factors=["High-value weekend service"],
                explanation="High-value services on weekends warrant review",
            ))

        # Check member frequency
        if features.member_claim_count_30d > 15:
            anomalies.append(AnomalyScore(
                claim_id=features.claim_id,
                is_anomaly=True,
                anomaly_score=0.55,
                anomaly_type=AnomalyType.FREQUENCY_ANOMALY,
                confidence=0.7,
                contributing_factors=["High member claim frequency"],
                explanation=f"Member has {features.member_claim_count_30d} claims in 30 days",
            ))

        # Check provider patterns
        if features.provider_denial_rate > 0.25:
            anomalies.append(AnomalyScore(
                claim_id=features.claim_id,
                is_anomaly=True,
                anomaly_score=0.6,
                anomaly_type=AnomalyType.PROVIDER_ANOMALY,
                confidence=0.75,
                contributing_factors=["High provider denial rate"],
                explanation=f"Provider has {features.provider_denial_rate*100:.1f}% denial rate",
            ))

        return anomalies

    def predict(self, features: ClaimFeatures) -> AnomalyScore:
        """
        Get combined anomaly prediction.

        Args:
            features: Claim features

        Returns:
            Combined AnomalyScore
        """
        anomalies = self.detect_anomalies(features)

        if not anomalies:
            return AnomalyScore(
                claim_id=features.claim_id,
                is_anomaly=False,
                anomaly_score=0.0,
                confidence=0.9,
                contributing_factors=[],
                explanation="No statistical anomalies detected",
            )

        # Combine anomaly scores
        max_score = max(a.anomaly_score for a in anomalies)
        combined_score = min(1.0, sum(a.anomaly_score for a in anomalies) / 2)
        all_factors = []
        for a in anomalies:
            all_factors.extend(a.contributing_factors)

        # Get primary anomaly type
        primary_type = max(anomalies, key=lambda a: a.anomaly_score).anomaly_type

        return AnomalyScore(
            claim_id=features.claim_id,
            is_anomaly=True,
            anomaly_score=combined_score,
            anomaly_type=primary_type,
            confidence=sum(a.confidence for a in anomalies) / len(anomalies),
            contributing_factors=list(set(all_factors)),
            explanation=f"Detected {len(anomalies)} anomalies: " + ", ".join(a.explanation or "" for a in anomalies[:3]),
        )


class FeatureEngineer:
    """
    Feature engineering for claim ML models.

    Transforms raw claim data into features suitable for ML models.
    """

    # High-value procedure codes
    HIGH_VALUE_PROCEDURES = {
        "27447", "27130", "63030", "47562", "19301",
        "33533", "35301", "43239", "44140", "49505",
        "27446", "27487", "63047", "43280",
    }

    # Federal holidays (simplified)
    FEDERAL_HOLIDAYS = {
        (1, 1), (7, 4), (12, 25),  # New Year, July 4, Christmas
    }

    def __init__(self):
        """Initialize feature engineer."""
        pass

    def extract_features(
        self,
        claim_data: Dict[str, Any],
        provider_profile: Optional[Dict[str, Any]] = None,
        member_history: Optional[List[Dict[str, Any]]] = None,
    ) -> ClaimFeatures:
        """
        Extract ML features from claim data.

        Args:
            claim_data: Raw claim data
            provider_profile: Provider statistics
            member_history: Member's recent claims

        Returns:
            ClaimFeatures object
        """
        # Basic features
        claim_id = claim_data.get("claim_id", "unknown")
        total_charged = float(claim_data.get("total_charged", 0))
        procedure_codes = claim_data.get("procedure_codes", [])
        diagnosis_codes = claim_data.get("diagnosis_codes", [])
        num_procedures = len(procedure_codes)
        num_diagnoses = len(diagnosis_codes)

        # Service date features
        service_date = claim_data.get("service_date")
        if isinstance(service_date, str):
            service_date = date.fromisoformat(service_date)
        elif not isinstance(service_date, date):
            service_date = date.today()

        is_weekend = service_date.weekday() >= 5
        is_holiday = (service_date.month, service_date.day) in self.FEDERAL_HOLIDAYS
        is_month_end = service_date.day >= 28
        is_year_end = service_date.month == 12 and service_date.day >= 28

        # Provider features
        provider_id = claim_data.get("provider_id")
        provider_claim_count = 0
        provider_avg_charge = 0.0
        provider_denial_rate = 0.0
        provider_specialty_risk = 0.0

        if provider_profile:
            provider_claim_count = provider_profile.get("total_claims", 0)
            provider_avg_charge = float(provider_profile.get("avg_claim_amount", 0))
            provider_denial_rate = float(provider_profile.get("denial_rate", 0))
            provider_specialty_risk = float(provider_profile.get("specialty_risk", 0))

        # Member features
        member_id = claim_data.get("member_id")
        member_claim_count_30d = 0
        member_total_charged_30d = 0.0
        member_unique_providers_30d = 0
        member_unique_diagnoses_30d = 0
        days_since_last_claim = 365  # Default if no history

        if member_history:
            member_claim_count_30d = len(member_history)
            member_total_charged_30d = sum(
                float(c.get("total_charged", 0)) for c in member_history
            )
            member_unique_providers_30d = len(
                set(c.get("provider_id") for c in member_history if c.get("provider_id"))
            )

            # All diagnoses from history
            all_diags = set()
            for c in member_history:
                all_diags.update(c.get("diagnosis_codes", []))
            member_unique_diagnoses_30d = len(all_diags)

            # Days since last claim
            if member_history:
                last_date = max(
                    c.get("service_date", service_date) for c in member_history
                )
                if isinstance(last_date, str):
                    last_date = date.fromisoformat(last_date)
                days_since_last_claim = (service_date - last_date).days

        # Procedure features
        has_high_value = any(code in self.HIGH_VALUE_PROCEDURES for code in procedure_codes)
        procedure_complexity = min(1.0, (num_procedures + num_diagnoses) / 15)
        procedure_modifier_count = sum(
            1 for code in procedure_codes if len(str(code)) > 5
        )

        # Derived features
        charge_per_procedure = total_charged / max(1, num_procedures)
        diagnosis_procedure_ratio = num_diagnoses / max(1, num_procedures)

        return ClaimFeatures(
            claim_id=claim_id,
            total_charged=total_charged,
            num_procedures=num_procedures,
            num_diagnoses=num_diagnoses,
            service_date=service_date,
            is_weekend=is_weekend,
            is_holiday=is_holiday,
            is_month_end=is_month_end,
            is_year_end=is_year_end,
            days_since_last_claim=days_since_last_claim,
            provider_id=provider_id,
            provider_claim_count=provider_claim_count,
            provider_avg_charge=provider_avg_charge,
            provider_denial_rate=provider_denial_rate,
            provider_specialty_risk=provider_specialty_risk,
            member_id=member_id,
            member_claim_count_30d=member_claim_count_30d,
            member_total_charged_30d=member_total_charged_30d,
            member_unique_providers_30d=member_unique_providers_30d,
            member_unique_diagnoses_30d=member_unique_diagnoses_30d,
            has_high_value_procedure=has_high_value,
            procedure_complexity=procedure_complexity,
            procedure_modifier_count=procedure_modifier_count,
            charge_per_procedure=charge_per_procedure,
            diagnosis_procedure_ratio=diagnosis_procedure_ratio,
        )


# =============================================================================
# Ensemble Predictor
# =============================================================================


class MLAnomalyEnsemble:
    """
    Ensemble of ML models for anomaly detection.

    Combines multiple models for robust anomaly detection.
    """

    def __init__(self):
        """Initialize ensemble."""
        self.isolation_forest = IsolationForestModel()
        self.statistical_model = StatisticalAnomalyModel()
        self.feature_engineer = FeatureEngineer()
        self.is_fitted = False

    def fit(self, claims_data: List[Dict[str, Any]]) -> "MLAnomalyEnsemble":
        """
        Fit all models on training data.

        Args:
            claims_data: Historical claim data

        Returns:
            Self for chaining
        """
        # Extract features from all claims
        feature_vectors = []
        for claim in claims_data:
            features = self.feature_engineer.extract_features(claim)
            feature_vectors.append(features.to_vector())

        # Fit models
        self.isolation_forest.fit(feature_vectors)
        self.statistical_model.fit(claims_data)

        self.is_fitted = True
        return self

    def predict(
        self,
        claim_data: Dict[str, Any],
        provider_profile: Optional[Dict[str, Any]] = None,
        member_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[AnomalyScore, List[AnomalyScore]]:
        """
        Predict anomaly using ensemble.

        Args:
            claim_data: Claim to analyze
            provider_profile: Provider statistics
            member_history: Member's recent claims

        Returns:
            Tuple of (combined_score, individual_scores)
        """
        # Extract features
        features = self.feature_engineer.extract_features(
            claim_data, provider_profile, member_history
        )

        # Get predictions from each model
        individual_scores = []

        # Isolation Forest
        if self.isolation_forest.is_fitted:
            if_score = self.isolation_forest.predict(features)
            if_score.anomaly_type = AnomalyType.CLUSTER_ANOMALY
            individual_scores.append(if_score)

        # Statistical model
        if self.statistical_model.is_fitted:
            stat_score = self.statistical_model.predict(features)
            individual_scores.append(stat_score)

        # Combine scores
        if not individual_scores:
            combined = AnomalyScore(
                claim_id=features.claim_id,
                is_anomaly=False,
                anomaly_score=0.0,
                confidence=0.5,
                explanation="Models not fitted",
            )
        else:
            # Weighted combination
            weights = [0.4, 0.6]  # IF, Statistical
            weighted_score = sum(
                s.anomaly_score * w
                for s, w in zip(individual_scores, weights[:len(individual_scores)])
            )

            is_anomaly = any(s.is_anomaly for s in individual_scores)
            all_factors = []
            for s in individual_scores:
                all_factors.extend(s.contributing_factors)

            combined = AnomalyScore(
                claim_id=features.claim_id,
                is_anomaly=is_anomaly,
                anomaly_score=weighted_score,
                anomaly_type=individual_scores[0].anomaly_type if is_anomaly else None,
                confidence=sum(s.confidence for s in individual_scores) / len(individual_scores),
                contributing_factors=list(set(all_factors)),
                explanation=f"Ensemble score: {weighted_score:.3f} from {len(individual_scores)} models",
            )

        return combined, individual_scores


# =============================================================================
# Factory Functions
# =============================================================================


_ml_ensemble: Optional[MLAnomalyEnsemble] = None


def get_ml_ensemble() -> MLAnomalyEnsemble:
    """Get singleton ML ensemble instance."""
    global _ml_ensemble
    if _ml_ensemble is None:
        _ml_ensemble = MLAnomalyEnsemble()
        # Initialize with sample data
        _ml_ensemble.fit(_generate_sample_training_data())
    return _ml_ensemble


def _generate_sample_training_data() -> List[Dict[str, Any]]:
    """Generate sample training data for model initialization."""
    random.seed(42)
    samples = []

    for i in range(500):
        samples.append({
            "claim_id": f"TRAIN-{i:05d}",
            "total_charged": random.gauss(1500, 800),
            "num_procedures": random.randint(1, 8),
            "num_diagnoses": random.randint(1, 5),
            "procedure_codes": [f"9921{random.randint(1,5)}" for _ in range(random.randint(1, 4))],
            "diagnosis_codes": [f"J{random.randint(0,99):02d}" for _ in range(random.randint(1, 3))],
            "service_date": date.today() - timedelta(days=random.randint(1, 365)),
            "provider_id": f"NPI{random.randint(1000000000, 9999999999)}",
            "member_id": f"MEM{random.randint(10000, 99999)}",
            "charge_per_procedure": random.gauss(400, 200),
        })

    return samples
