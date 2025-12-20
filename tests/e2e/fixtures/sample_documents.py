"""
Sample Document Fixtures for E2E Testing.

Contains predefined document metadata for PDF forensics testing.
"""

from datetime import datetime
from uuid import uuid4


# =============================================================================
# Clean Document Metadata
# =============================================================================

CLEAN_PDF_METADATA = {
    "id": str(uuid4()),
    "filename": "clean_medical_report.pdf",
    "file_size": 245760,  # ~240KB
    "mime_type": "application/pdf",
    "producer": "Adobe Acrobat Pro DC",
    "creator": "Microsoft Word 2019",
    "creation_date": "2025-12-15T10:30:00Z",
    "modification_date": "2025-12-15T10:35:00Z",
    "pdf_version": "1.7",
    "page_count": 3,
    "is_encrypted": False,
    "has_javascript": False,
    "has_embedded_files": False,
    "fonts": [
        {"name": "Arial", "type": "TrueType", "embedded": True},
        {"name": "Times New Roman", "type": "TrueType", "embedded": True},
    ],
    "forensic_analysis": {
        "is_suspicious": False,
        "fraud_score": 0.05,
        "signals": [],
        "confidence": 0.95,
    },
}


# =============================================================================
# Tampered Document Metadata
# =============================================================================

TAMPERED_PDF_METADATA = {
    "id": str(uuid4()),
    "filename": "suspicious_invoice.pdf",
    "file_size": 312456,
    "mime_type": "application/pdf",
    "producer": "Adobe Acrobat Pro DC",
    "creator": "Unknown",
    "creation_date": "2024-01-15T08:00:00Z",  # Old creation date
    "modification_date": "2025-12-14T23:45:00Z",  # Recent modification
    "pdf_version": "1.7",
    "page_count": 2,
    "is_encrypted": False,
    "has_javascript": False,
    "has_embedded_files": False,
    "fonts": [
        {"name": "Arial", "type": "TrueType", "embedded": True},
        {"name": "Calibri", "type": "TrueType", "embedded": False},  # Different font
        {"name": "Liberation Sans", "type": "Type1", "embedded": True},  # Third font
    ],
    "forensic_analysis": {
        "is_suspicious": True,
        "fraud_score": 0.85,
        "signals": [
            {
                "signal_type": "metadata_mismatch",
                "severity": "high",
                "description": "Creation date differs from modification date by >11 months",
                "confidence": 0.92,
                "details": {
                    "creation_date": "2024-01-15",
                    "modification_date": "2025-12-14",
                    "days_difference": 334,
                },
            },
            {
                "signal_type": "font_substitution",
                "severity": "critical",
                "description": "Multiple fonts detected in document - potential text replacement",
                "confidence": 0.88,
                "details": {
                    "font_count": 3,
                    "mixed_embedding": True,
                    "suspicious_fonts": ["Liberation Sans"],
                },
            },
            {
                "signal_type": "layer_anomaly",
                "severity": "medium",
                "description": "Hidden text layer detected below visible content",
                "confidence": 0.75,
                "details": {
                    "layer_count": 2,
                    "hidden_text_detected": True,
                },
            },
        ],
        "confidence": 0.85,
    },
}


# =============================================================================
# Suspicious Producer Metadata
# =============================================================================

SUSPICIOUS_PDF_METADATA = {
    "id": str(uuid4()),
    "filename": "edited_claim_form.pdf",
    "file_size": 189432,
    "mime_type": "application/pdf",
    "producer": "PDFescape Online Editor",  # Known online editor
    "creator": "PDFescape",
    "creation_date": "2025-12-01T14:20:00Z",
    "modification_date": "2025-12-14T16:30:00Z",
    "pdf_version": "1.4",
    "page_count": 1,
    "is_encrypted": False,
    "has_javascript": False,
    "has_embedded_files": False,
    "fonts": [
        {"name": "Helvetica", "type": "Type1", "embedded": False},
    ],
    "forensic_analysis": {
        "is_suspicious": True,
        "fraud_score": 0.65,
        "signals": [
            {
                "signal_type": "suspicious_producer",
                "severity": "medium",
                "description": "Document created with online PDF editor commonly used for form manipulation",
                "confidence": 0.82,
                "details": {
                    "producer": "PDFescape Online Editor",
                    "risk_category": "online_editor",
                    "known_abuse_tool": True,
                },
            },
        ],
        "confidence": 0.82,
    },
}


# =============================================================================
# Document with JavaScript (High Risk)
# =============================================================================

JAVASCRIPT_PDF_METADATA = {
    "id": str(uuid4()),
    "filename": "interactive_form.pdf",
    "file_size": 567890,
    "mime_type": "application/pdf",
    "producer": "Unknown PDF Generator",
    "creator": "Unknown",
    "creation_date": "2025-12-10T00:00:00Z",
    "modification_date": "2025-12-10T00:00:00Z",
    "pdf_version": "1.6",
    "page_count": 5,
    "is_encrypted": False,
    "has_javascript": True,  # Contains JavaScript
    "has_embedded_files": True,  # Contains embedded files
    "fonts": [
        {"name": "Arial", "type": "TrueType", "embedded": True},
    ],
    "forensic_analysis": {
        "is_suspicious": True,
        "fraud_score": 0.75,
        "signals": [
            {
                "signal_type": "javascript_detected",
                "severity": "high",
                "description": "Document contains JavaScript code which may be used for malicious purposes",
                "confidence": 0.90,
                "details": {
                    "script_count": 3,
                    "suspicious_functions": ["app.alert", "this.submitForm"],
                },
            },
            {
                "signal_type": "embedded_files",
                "severity": "medium",
                "description": "Document contains embedded files which could be malicious",
                "confidence": 0.85,
                "details": {
                    "embedded_count": 2,
                    "file_types": ["exe", "bat"],
                },
            },
        ],
        "confidence": 0.88,
    },
}


# =============================================================================
# Encrypted Document
# =============================================================================

ENCRYPTED_PDF_METADATA = {
    "id": str(uuid4()),
    "filename": "protected_document.pdf",
    "file_size": 423567,
    "mime_type": "application/pdf",
    "producer": "Adobe Acrobat Pro DC",
    "creator": "Microsoft Word",
    "creation_date": "2025-12-05T09:00:00Z",
    "modification_date": "2025-12-05T09:15:00Z",
    "pdf_version": "1.7",
    "page_count": None,  # Cannot determine - encrypted
    "is_encrypted": True,
    "encryption_level": "AES-256",
    "has_javascript": None,  # Cannot determine
    "has_embedded_files": None,  # Cannot determine
    "fonts": [],  # Cannot extract
    "forensic_analysis": {
        "is_suspicious": True,
        "fraud_score": 0.55,
        "signals": [
            {
                "signal_type": "encrypted_document",
                "severity": "medium",
                "description": "Document is encrypted and cannot be fully analyzed",
                "confidence": 1.0,
                "details": {
                    "encryption_type": "AES-256",
                    "analysis_limited": True,
                },
            },
        ],
        "confidence": 0.60,
        "analysis_complete": False,
        "reason": "Document encryption prevents full forensic analysis",
    },
}


# =============================================================================
# Document Collections
# =============================================================================

ALL_DOCUMENT_METADATA = [
    CLEAN_PDF_METADATA,
    TAMPERED_PDF_METADATA,
    SUSPICIOUS_PDF_METADATA,
    JAVASCRIPT_PDF_METADATA,
    ENCRYPTED_PDF_METADATA,
]

CLEAN_DOCUMENTS = [CLEAN_PDF_METADATA]

SUSPICIOUS_DOCUMENTS = [
    TAMPERED_PDF_METADATA,
    SUSPICIOUS_PDF_METADATA,
    JAVASCRIPT_PDF_METADATA,
    ENCRYPTED_PDF_METADATA,
]

HIGH_RISK_DOCUMENTS = [
    TAMPERED_PDF_METADATA,
    JAVASCRIPT_PDF_METADATA,
]


# =============================================================================
# Suspicious Producer List
# =============================================================================

SUSPICIOUS_PDF_PRODUCERS = [
    "PDFescape Online Editor",
    "Smallpdf",
    "iLovePDF",
    "PDF-XChange Editor",
    "Foxit PhantomPDF",
    "Nitro Pro",
    "Unknown",
    "Unknown PDF Generator",
    "",
    None,
]


# =============================================================================
# Helper Functions
# =============================================================================


def create_document_with_fraud_score(score: float, **overrides) -> dict:
    """Create document metadata with specified fraud score."""
    doc = CLEAN_PDF_METADATA.copy()
    doc["id"] = str(uuid4())
    doc["filename"] = f"test_doc_{uuid4().hex[:8]}.pdf"
    doc["forensic_analysis"] = doc["forensic_analysis"].copy()
    doc["forensic_analysis"]["fraud_score"] = score
    doc["forensic_analysis"]["is_suspicious"] = score >= 0.5
    doc.update(overrides)
    return doc


def create_document_with_signals(signals: list, **overrides) -> dict:
    """Create document metadata with specified forensic signals."""
    doc = CLEAN_PDF_METADATA.copy()
    doc["id"] = str(uuid4())
    doc["filename"] = f"test_doc_{uuid4().hex[:8]}.pdf"
    doc["forensic_analysis"] = doc["forensic_analysis"].copy()
    doc["forensic_analysis"]["signals"] = signals
    doc["forensic_analysis"]["is_suspicious"] = len(signals) > 0
    doc.update(overrides)
    return doc


def create_document_with_producer(producer: str, **overrides) -> dict:
    """Create document metadata with specified producer."""
    doc = CLEAN_PDF_METADATA.copy()
    doc["id"] = str(uuid4())
    doc["filename"] = f"test_doc_{uuid4().hex[:8]}.pdf"
    doc["producer"] = producer

    # Mark as suspicious if producer is in suspicious list
    if producer in SUSPICIOUS_PDF_PRODUCERS:
        doc["forensic_analysis"] = doc["forensic_analysis"].copy()
        doc["forensic_analysis"]["is_suspicious"] = True
        doc["forensic_analysis"]["fraud_score"] = 0.6
        doc["forensic_analysis"]["signals"] = [
            {
                "signal_type": "suspicious_producer",
                "severity": "medium",
                "description": f"Document created with suspicious producer: {producer}",
                "confidence": 0.8,
            }
        ]

    doc.update(overrides)
    return doc
