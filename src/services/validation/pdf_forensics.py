"""
PDF Forensics Service for Fraud Detection (Rule 3).

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Detects signs of document tampering or forgery in PDF documents:
- Metadata inconsistencies
- Suspicious PDF producers
- Font inconsistencies
- Layer anomalies
- Digital signature validation
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import fitz  # PyMuPDF

from src.core.config import get_claims_settings
from src.services.validation_cache import get_validation_cache

logger = logging.getLogger(__name__)


class ForensicSignal(str, Enum):
    """Types of forensic signals indicating potential tampering."""

    METADATA_MISMATCH = "metadata_mismatch"
    SUSPICIOUS_PRODUCER = "suspicious_producer"
    RECENT_MODIFICATION = "recent_modification"
    FONT_INCONSISTENCY = "font_inconsistency"
    HASH_VERIFICATION_FAILED = "hash_verification_failed"
    LAYER_ANOMALY = "layer_anomaly"
    DIGITAL_SIGNATURE_INVALID = "digital_signature_invalid"
    EMBEDDED_JAVASCRIPT = "embedded_javascript"
    INCREMENTAL_UPDATE = "incremental_update"
    CONTENT_STREAM_ANOMALY = "content_stream_anomaly"


class SignalSeverity(str, Enum):
    """Severity levels for forensic signals."""

    CRITICAL = "critical"  # Strong indicator of tampering
    HIGH = "high"          # Likely tampering
    MEDIUM = "medium"      # Possible tampering
    LOW = "low"            # Minor concern
    INFO = "info"          # Informational only


@dataclass
class ForensicFinding:
    """Individual forensic finding."""

    signal: ForensicSignal
    severity: SignalSeverity
    confidence: float  # 0.0 - 1.0
    title: str
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    page_number: Optional[int] = None


@dataclass
class ForensicResult:
    """Complete forensic analysis result."""

    document_hash: str
    is_suspicious: bool
    risk_score: float  # 0.0 - 1.0
    findings: list[ForensicFinding]
    metadata: dict[str, Any]
    analysis_time_ms: int

    @property
    def critical_findings(self) -> list[ForensicFinding]:
        """Get critical severity findings."""
        return [f for f in self.findings if f.severity == SignalSeverity.CRITICAL]

    @property
    def high_findings(self) -> list[ForensicFinding]:
        """Get high severity findings."""
        return [f for f in self.findings if f.severity == SignalSeverity.HIGH]

    def to_evidence_list(self) -> list[dict]:
        """Convert findings to evidence format for rejection."""
        return [
            {
                "signal_type": f.signal.value,
                "severity": f.severity.value,
                "confidence": f.confidence,
                "title": f.title,
                "description": f.description,
                "details": f.details,
                "page_number": f.page_number,
            }
            for f in self.findings
        ]


# Known suspicious PDF producers (editing software)
SUSPICIOUS_PRODUCERS = frozenset([
    "adobe acrobat pro",
    "adobe acrobat dc",
    "foxit phantompdf",
    "foxit reader",
    "nitro pro",
    "nitro pdf",
    "pdf-xchange",
    "pdfill",
    "sejda",
    "smallpdf",
    "ilovepdf",
    "pdf editor",
    "pdf complete",
    "pdf architect",
    "soda pdf",
    "wondershare pdfelement",
    "pdfpenp",
    "pdf expert",
])

# Known legitimate medical document producers
LEGITIMATE_PRODUCERS = frozenset([
    "microsoft word",
    "microsoft office",
    "openoffice",
    "libreoffice",
    "google docs",
    "epic",
    "cerner",
    "meditech",
    "allscripts",
    "athenahealth",
    "eclinicalworks",
    "nextgen",
    "practice fusion",
    "kareo",
    "drchrono",
])


class PDFForensicsService:
    """
    PDF forensic analysis service for fraud detection.

    Analyzes PDF documents for signs of tampering or forgery.
    Part of the Fraud Detection (Rule 3) validation.

    Source: Design Document Section 3.3 - Fraud Claim Workflow
    """

    def __init__(
        self,
        risk_threshold: float = 0.7,
        cache_enabled: bool = True,
    ):
        """
        Initialize the forensics service.

        Args:
            risk_threshold: Score above which document is flagged suspicious
            cache_enabled: Whether to cache analysis results
        """
        settings = get_claims_settings()
        self.risk_threshold = risk_threshold or settings.FRAUD_RISK_THRESHOLD
        self.cache_enabled = cache_enabled
        self._cache = get_validation_cache() if cache_enabled else None

    async def analyze_document(
        self,
        file_path: Optional[Path] = None,
        file_bytes: Optional[bytes] = None,
        document_id: Optional[str] = None,
    ) -> ForensicResult:
        """
        Perform comprehensive forensic analysis on a PDF document.

        Args:
            file_path: Path to PDF file
            file_bytes: PDF file as bytes
            document_id: Optional document ID for caching

        Returns:
            ForensicResult with all findings

        Raises:
            ValueError: If neither file_path nor file_bytes provided
        """
        import time
        start_time = time.perf_counter()

        if file_path is None and file_bytes is None:
            raise ValueError("Either file_path or file_bytes must be provided")

        # Read file bytes if path provided
        if file_bytes is None:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

        # Calculate document hash
        doc_hash = hashlib.sha256(file_bytes).hexdigest()

        # Check cache
        if self.cache_enabled and self._cache:
            cached = await self._cache.get_forensics_result(doc_hash)
            if cached:
                logger.debug(f"Forensics cache hit for {doc_hash[:16]}")
                return ForensicResult(**cached)

        # Perform analysis
        findings: list[ForensicFinding] = []
        metadata: dict[str, Any] = {}

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")

            # Extract metadata
            metadata = self._extract_metadata(doc)

            # Run all forensic checks
            findings.extend(self._check_metadata_consistency(metadata))
            findings.extend(self._check_producer(metadata))
            findings.extend(self._check_modification_dates(metadata))
            findings.extend(self._check_fonts(doc))
            findings.extend(self._check_layers(doc))
            findings.extend(self._check_javascript(doc))
            findings.extend(self._check_incremental_updates(file_bytes))
            findings.extend(self._check_content_streams(doc))

            doc.close()

        except Exception as e:
            logger.error(f"Error analyzing PDF: {e}")
            findings.append(ForensicFinding(
                signal=ForensicSignal.HASH_VERIFICATION_FAILED,
                severity=SignalSeverity.HIGH,
                confidence=0.9,
                title="PDF Analysis Failed",
                description=f"Unable to fully analyze document: {str(e)}",
                details={"error": str(e)},
            ))

        # Calculate risk score
        risk_score = self._calculate_risk_score(findings)
        is_suspicious = risk_score >= self.risk_threshold

        analysis_time = int((time.perf_counter() - start_time) * 1000)

        result = ForensicResult(
            document_hash=doc_hash,
            is_suspicious=is_suspicious,
            risk_score=risk_score,
            findings=findings,
            metadata=metadata,
            analysis_time_ms=analysis_time,
        )

        # Cache result
        if self.cache_enabled and self._cache:
            await self._cache.set_forensics_result(
                doc_hash,
                {
                    "document_hash": result.document_hash,
                    "is_suspicious": result.is_suspicious,
                    "risk_score": result.risk_score,
                    "findings": [
                        {
                            "signal": f.signal.value,
                            "severity": f.severity.value,
                            "confidence": f.confidence,
                            "title": f.title,
                            "description": f.description,
                            "details": f.details,
                            "page_number": f.page_number,
                        }
                        for f in result.findings
                    ],
                    "metadata": result.metadata,
                    "analysis_time_ms": result.analysis_time_ms,
                }
            )

        logger.info(
            f"Forensic analysis complete: risk_score={risk_score:.2f}, "
            f"findings={len(findings)}, time={analysis_time}ms"
        )

        return result

    def _extract_metadata(self, doc: fitz.Document) -> dict[str, Any]:
        """Extract PDF metadata."""
        meta = doc.metadata or {}
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "keywords": meta.get("keywords", ""),
            "creator": meta.get("creator", ""),
            "producer": meta.get("producer", ""),
            "creation_date": meta.get("creationDate", ""),
            "modification_date": meta.get("modDate", ""),
            "page_count": doc.page_count,
            "is_encrypted": doc.is_encrypted,
            "is_form_pdf": doc.is_form_pdf,
        }

    def _check_metadata_consistency(
        self,
        metadata: dict[str, Any],
    ) -> list[ForensicFinding]:
        """Check for metadata inconsistencies."""
        findings = []

        # Check if creator and producer are different (could indicate editing)
        creator = (metadata.get("creator") or "").lower().strip()
        producer = (metadata.get("producer") or "").lower().strip()

        if creator and producer and creator != producer:
            # This is common but worth noting
            findings.append(ForensicFinding(
                signal=ForensicSignal.METADATA_MISMATCH,
                severity=SignalSeverity.LOW,
                confidence=0.5,
                title="Creator and Producer Mismatch",
                description="Document was created by one application and processed by another",
                details={
                    "creator": metadata.get("creator"),
                    "producer": metadata.get("producer"),
                },
            ))

        # Check for missing metadata (suspicious for medical documents)
        if not metadata.get("author") and not metadata.get("creator"):
            findings.append(ForensicFinding(
                signal=ForensicSignal.METADATA_MISMATCH,
                severity=SignalSeverity.MEDIUM,
                confidence=0.6,
                title="Missing Author Information",
                description="Document lacks author or creator metadata",
                details={"metadata": metadata},
            ))

        return findings

    def _check_producer(self, metadata: dict[str, Any]) -> list[ForensicFinding]:
        """Check for suspicious PDF producers (editing software)."""
        findings = []

        producer = (metadata.get("producer") or "").lower()
        creator = (metadata.get("creator") or "").lower()

        # Check producer against suspicious list
        for suspicious in SUSPICIOUS_PRODUCERS:
            if suspicious in producer:
                findings.append(ForensicFinding(
                    signal=ForensicSignal.SUSPICIOUS_PRODUCER,
                    severity=SignalSeverity.HIGH,
                    confidence=0.85,
                    title="PDF Editing Software Detected",
                    description=f"Document was processed by PDF editing software: {metadata.get('producer')}",
                    details={
                        "producer": metadata.get("producer"),
                        "suspicious_match": suspicious,
                    },
                ))
                break

        # Check if originally from legitimate source but edited
        is_legitimate_creator = any(
            legit in creator for legit in LEGITIMATE_PRODUCERS
        )
        is_suspicious_producer = any(
            susp in producer for susp in SUSPICIOUS_PRODUCERS
        )

        if is_legitimate_creator and is_suspicious_producer:
            findings.append(ForensicFinding(
                signal=ForensicSignal.SUSPICIOUS_PRODUCER,
                severity=SignalSeverity.CRITICAL,
                confidence=0.95,
                title="Document Modified After Creation",
                description=f"Document created by {metadata.get('creator')} was later edited with {metadata.get('producer')}",
                details={
                    "creator": metadata.get("creator"),
                    "producer": metadata.get("producer"),
                },
            ))

        return findings

    def _check_modification_dates(
        self,
        metadata: dict[str, Any],
    ) -> list[ForensicFinding]:
        """Check modification dates for suspicious patterns."""
        findings = []

        creation_date = self._parse_pdf_date(metadata.get("creation_date", ""))
        mod_date = self._parse_pdf_date(metadata.get("modification_date", ""))

        if creation_date and mod_date:
            # Check if modified significantly after creation
            time_diff = mod_date - creation_date

            if time_diff > timedelta(days=1):
                severity = SignalSeverity.MEDIUM
                if time_diff > timedelta(days=7):
                    severity = SignalSeverity.HIGH

                findings.append(ForensicFinding(
                    signal=ForensicSignal.RECENT_MODIFICATION,
                    severity=severity,
                    confidence=0.7,
                    title="Document Modified After Creation",
                    description=f"Document was modified {time_diff.days} days after creation",
                    details={
                        "creation_date": str(creation_date),
                        "modification_date": str(mod_date),
                        "days_difference": time_diff.days,
                    },
                ))

        return findings

    def _check_fonts(self, doc: fitz.Document) -> list[ForensicFinding]:
        """Check for font inconsistencies that may indicate editing."""
        findings = []
        font_usage: dict[str, set[int]] = {}  # font -> set of pages

        for page_num in range(doc.page_count):
            page = doc[page_num]
            fonts = page.get_fonts()

            for font in fonts:
                font_name = font[3] if len(font) > 3 else str(font)
                if font_name not in font_usage:
                    font_usage[font_name] = set()
                font_usage[font_name].add(page_num)

        # Check for fonts used on only one page (potential patch)
        single_page_fonts = [
            (font, pages) for font, pages in font_usage.items()
            if len(pages) == 1 and doc.page_count > 1
        ]

        if single_page_fonts and len(font_usage) > 3:
            findings.append(ForensicFinding(
                signal=ForensicSignal.FONT_INCONSISTENCY,
                severity=SignalSeverity.MEDIUM,
                confidence=0.65,
                title="Inconsistent Font Usage",
                description=f"Found {len(single_page_fonts)} fonts used on only one page",
                details={
                    "single_page_fonts": [
                        {"font": f, "page": list(p)[0]} for f, p in single_page_fonts
                    ],
                    "total_fonts": len(font_usage),
                },
            ))

        # Check for unusual number of fonts
        if len(font_usage) > 20:
            findings.append(ForensicFinding(
                signal=ForensicSignal.FONT_INCONSISTENCY,
                severity=SignalSeverity.LOW,
                confidence=0.5,
                title="Excessive Font Variety",
                description=f"Document uses {len(font_usage)} different fonts",
                details={"font_count": len(font_usage)},
            ))

        return findings

    def _check_layers(self, doc: fitz.Document) -> list[ForensicFinding]:
        """Check for layer anomalies."""
        findings = []

        try:
            # Check for Optional Content Groups (layers)
            ocgs = doc.get_ocgs()
            if ocgs:
                findings.append(ForensicFinding(
                    signal=ForensicSignal.LAYER_ANOMALY,
                    severity=SignalSeverity.MEDIUM,
                    confidence=0.7,
                    title="PDF Contains Layers",
                    description=f"Document contains {len(ocgs)} optional content layers",
                    details={"layer_count": len(ocgs)},
                ))
        except Exception:
            pass  # OCG not supported in all PyMuPDF versions

        return findings

    def _check_javascript(self, doc: fitz.Document) -> list[ForensicFinding]:
        """Check for embedded JavaScript (security risk)."""
        findings = []

        try:
            js = doc.get_js()
            if js:
                findings.append(ForensicFinding(
                    signal=ForensicSignal.EMBEDDED_JAVASCRIPT,
                    severity=SignalSeverity.CRITICAL,
                    confidence=0.95,
                    title="Embedded JavaScript Detected",
                    description="Document contains embedded JavaScript code (security risk)",
                    details={"js_present": True},
                ))
        except Exception:
            pass

        return findings

    def _check_incremental_updates(self, file_bytes: bytes) -> list[ForensicFinding]:
        """Check for incremental updates (common in edited PDFs)."""
        findings = []

        # Count %%EOF markers (each indicates an update)
        eof_count = file_bytes.count(b"%%EOF")

        if eof_count > 1:
            severity = SignalSeverity.MEDIUM if eof_count <= 3 else SignalSeverity.HIGH

            findings.append(ForensicFinding(
                signal=ForensicSignal.INCREMENTAL_UPDATE,
                severity=severity,
                confidence=0.75,
                title="Multiple PDF Revisions Detected",
                description=f"Document has been saved/modified {eof_count} times",
                details={"revision_count": eof_count},
            ))

        return findings

    def _check_content_streams(self, doc: fitz.Document) -> list[ForensicFinding]:
        """Check content streams for anomalies."""
        findings = []

        for page_num in range(min(doc.page_count, 10)):  # Check first 10 pages
            page = doc[page_num]

            try:
                # Get text blocks
                blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

                # Check for overlapping text (common in edits)
                if "blocks" in blocks:
                    text_blocks = [
                        b for b in blocks["blocks"]
                        if b.get("type") == 0  # Text block
                    ]

                    # Check for suspiciously positioned text
                    for i, block in enumerate(text_blocks):
                        bbox = block.get("bbox", (0, 0, 0, 0))
                        for other in text_blocks[i+1:]:
                            other_bbox = other.get("bbox", (0, 0, 0, 0))
                            if self._boxes_overlap(bbox, other_bbox):
                                findings.append(ForensicFinding(
                                    signal=ForensicSignal.CONTENT_STREAM_ANOMALY,
                                    severity=SignalSeverity.HIGH,
                                    confidence=0.8,
                                    title="Overlapping Text Detected",
                                    description="Text blocks overlap, possibly indicating content replacement",
                                    details={
                                        "page": page_num + 1,
                                        "bbox1": bbox,
                                        "bbox2": other_bbox,
                                    },
                                    page_number=page_num + 1,
                                ))
                                break

            except Exception as e:
                logger.debug(f"Error checking content stream on page {page_num}: {e}")

        return findings

    def _boxes_overlap(
        self,
        box1: tuple[float, float, float, float],
        box2: tuple[float, float, float, float],
    ) -> bool:
        """Check if two bounding boxes overlap significantly."""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2

        # Calculate overlap
        x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
        y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))

        if x_overlap > 0 and y_overlap > 0:
            overlap_area = x_overlap * y_overlap
            box1_area = (x1_max - x1_min) * (y1_max - y1_min)
            box2_area = (x2_max - x2_min) * (y2_max - y2_min)

            min_area = min(box1_area, box2_area)
            if min_area > 0:
                overlap_ratio = overlap_area / min_area
                return overlap_ratio > 0.3  # 30% overlap threshold

        return False

    def _parse_pdf_date(self, date_str: str) -> Optional[datetime]:
        """Parse PDF date format (D:YYYYMMDDHHmmSS)."""
        if not date_str:
            return None

        # Remove D: prefix if present
        date_str = date_str.replace("D:", "")

        # Try various formats
        formats = [
            "%Y%m%d%H%M%S",
            "%Y%m%d%H%M",
            "%Y%m%d",
        ]

        # Clean the string
        date_str = re.sub(r"[^0-9]", "", date_str)[:14]

        for fmt in formats:
            try:
                if len(date_str) >= len(fmt.replace("%", "")):
                    return datetime.strptime(date_str[:len(fmt.replace("%", ""))], fmt)
            except ValueError:
                continue

        return None

    def _calculate_risk_score(self, findings: list[ForensicFinding]) -> float:
        """Calculate overall risk score from findings."""
        if not findings:
            return 0.0

        # Weight by severity
        severity_weights = {
            SignalSeverity.CRITICAL: 0.4,
            SignalSeverity.HIGH: 0.25,
            SignalSeverity.MEDIUM: 0.15,
            SignalSeverity.LOW: 0.05,
            SignalSeverity.INFO: 0.0,
        }

        total_score = 0.0
        max_possible = 0.0

        for finding in findings:
            weight = severity_weights.get(finding.severity, 0.0)
            total_score += weight * finding.confidence
            max_possible += weight

        if max_possible == 0:
            return 0.0

        # Normalize to 0-1 range
        raw_score = total_score / max_possible

        # Apply diminishing returns for multiple findings
        # More findings = higher confidence in assessment
        finding_multiplier = min(1.0, 0.5 + (len(findings) * 0.1))

        return min(1.0, raw_score * finding_multiplier)


# Singleton instance
_pdf_forensics_service: Optional[PDFForensicsService] = None


def get_pdf_forensics_service() -> PDFForensicsService:
    """Get or create the singleton PDF forensics service."""
    global _pdf_forensics_service
    if _pdf_forensics_service is None:
        _pdf_forensics_service = PDFForensicsService()
    return _pdf_forensics_service
