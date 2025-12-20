# Reimbursement Claims Management Solution
# Configurable Hybrid Architecture Research Report

**Research Date**: December 18, 2025
**Focus**: Provider-Agnostic Architecture with Swappable Commercial/Open-Source Components
**Researcher**: Claude Code (AI Assistant)

---

## 1. Executive Summary

This document defines a **configurable hybrid architecture** where each AI/ML component can be dynamically switched between commercial providers (GPT-4, Azure, Google) and open-source alternatives (Qwen2.5-VL, PaddleOCR, BioMistral). This approach provides:

- **Cost Optimization**: Use open-source by default, commercial for edge cases
- **Flexibility**: A/B test providers, gradual migration
- **Resilience**: Automatic failover between providers
- **Compliance**: Keep sensitive data on-premises with local models

### Key Design Principle: Provider Abstraction Layer

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│              (Claims Processing, Validation)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Provider Abstraction Layer                  │
│     (Unified Interface for all AI/ML Services)              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │   LLM   │  │   OCR   │  │  Trans  │  │  Rules  │  ...   │
│  │ Gateway │  │ Gateway │  │ Gateway │  │ Gateway │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
└───────┼────────────┼────────────┼────────────┼──────────────┘
        │            │            │            │
   ┌────┴────┐  ┌────┴────┐  ┌────┴────┐  ┌────┴────┐
   ▼         ▼  ▼         ▼  ▼         ▼  ▼         ▼
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│GPT-4│ │Qwen │ │Azure│ │Paddle│ │Azure│ │Libre│ │Drools│ │ZEN  │
│     │ │2.5  │ │OCR  │ │OCR  │ │Trans│ │Trans│ │     │ │     │
└─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘
Commercial  Open   Commercial Open  Commercial Open  Commercial Open
```

---

## 2. Configurable Components Overview

### Provider Matrix

| Component | Commercial Provider | Open-Source Alternative | Config Key |
|-----------|--------------------|-----------------------|------------|
| **Document LLM** | GPT-4 Vision | Qwen2.5-VL (Ollama) | `LLM_PROVIDER` |
| **Medical LLM** | GPT-4 / Claude | BioMistral (vLLM) | `MEDICAL_LLM_PROVIDER` |
| **OCR Engine** | Azure AI Doc Intelligence | PaddleOCR | `OCR_PROVIDER` |
| **Handwriting ICR** | Azure / Google Vision | TrOCR | `ICR_PROVIDER` |
| **Translation** | Azure Translator | LibreTranslate | `TRANSLATION_PROVIDER` |
| **Rules Engine** | InRule / Nected | GoRules ZEN | `RULES_PROVIDER` |
| **Currency API** | Xe / Fixer.io | fawazahmed0 API | `CURRENCY_PROVIDER` |
| **Medical NLP** | AWS Comprehend Medical | MedCAT + medspaCy | `MEDICAL_NLP_PROVIDER` |
| **Fraud Detection** | Third-party SaaS | XGBoost (self-hosted) | `FWA_PROVIDER` |
| **Message Queue** | Confluent Kafka | Redis Streams / NATS | `MESSAGE_QUEUE_PROVIDER` |

---

## 3. LLM Provider Abstraction

### 3.1 Recommended Tool: LiteLLM

**Source**: [GitHub - BerriAI/litellm](https://github.com/BerriAI/litellm)
**License**: MIT

LiteLLM provides a Python SDK and Proxy Server (AI Gateway) to call 100+ LLM APIs in OpenAI-compatible format.

**Supported Providers**:
- OpenAI (GPT-4, GPT-4 Vision)
- Anthropic (Claude)
- Azure OpenAI
- Google Vertex AI
- AWS Bedrock
- Ollama (local models)
- vLLM (self-hosted)
- HuggingFace
- Cohere, Mistral, and 90+ more

### 3.2 Configuration Schema

```python
# config/llm_config.py

from enum import Enum
from pydantic import BaseSettings

class LLMProvider(str, Enum):
    OPENAI = "openai"           # GPT-4 Vision
    AZURE_OPENAI = "azure"      # Azure OpenAI
    ANTHROPIC = "anthropic"     # Claude
    OLLAMA = "ollama"           # Local (Qwen2.5-VL, BioMistral)
    VLLM = "vllm"               # Self-hosted production
    BEDROCK = "bedrock"         # AWS Bedrock

class LLMSettings(BaseSettings):
    # Primary LLM for document understanding
    LLM_PROVIDER: LLMProvider = LLMProvider.OLLAMA
    LLM_MODEL: str = "qwen2.5-vl:7b"  # Default: open-source
    LLM_FALLBACK_PROVIDER: LLMProvider = LLMProvider.OPENAI
    LLM_FALLBACK_MODEL: str = "gpt-4-vision-preview"

    # Medical LLM for clinical validation
    MEDICAL_LLM_PROVIDER: LLMProvider = LLMProvider.OLLAMA
    MEDICAL_LLM_MODEL: str = "biomistral:7b"
    MEDICAL_LLM_FALLBACK_PROVIDER: LLMProvider = LLMProvider.OPENAI
    MEDICAL_LLM_FALLBACK_MODEL: str = "gpt-4-turbo"

    # Provider-specific settings
    OPENAI_API_KEY: str = ""
    AZURE_API_KEY: str = ""
    AZURE_API_BASE: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    VLLM_BASE_URL: str = "http://localhost:8000"

    # Behavior settings
    LLM_TIMEOUT: int = 60
    LLM_MAX_RETRIES: int = 3
    LLM_ENABLE_FALLBACK: bool = True
    LLM_CONFIDENCE_THRESHOLD: float = 0.85  # Fallback if below this

    class Config:
        env_file = ".env"
```

### 3.3 LLM Gateway Implementation

```python
# services/llm_gateway.py

from litellm import completion, acompletion
from litellm.exceptions import APIError, RateLimitError
import litellm
from typing import Optional, List, Dict, Any
from config.llm_config import LLMSettings, LLMProvider

class LLMGateway:
    """
    Unified LLM interface supporting multiple providers.
    Provides automatic failover and provider switching.
    """

    def __init__(self, settings: LLMSettings):
        self.settings = settings
        self._configure_providers()

    def _configure_providers(self):
        """Configure LiteLLM with provider credentials."""
        litellm.openai_key = self.settings.OPENAI_API_KEY
        litellm.anthropic_key = self.settings.ANTHROPIC_API_KEY

        # Set custom API bases for self-hosted
        if self.settings.LLM_PROVIDER == LLMProvider.OLLAMA:
            litellm.api_base = self.settings.OLLAMA_BASE_URL
        elif self.settings.LLM_PROVIDER == LLMProvider.VLLM:
            litellm.api_base = self.settings.VLLM_BASE_URL

    def _get_model_string(self, provider: LLMProvider, model: str) -> str:
        """Convert provider + model to LiteLLM model string."""
        provider_prefixes = {
            LLMProvider.OPENAI: "",
            LLMProvider.AZURE_OPENAI: "azure/",
            LLMProvider.ANTHROPIC: "anthropic/",
            LLMProvider.OLLAMA: "ollama/",
            LLMProvider.VLLM: "openai/",  # vLLM uses OpenAI-compatible API
            LLMProvider.BEDROCK: "bedrock/",
        }
        return f"{provider_prefixes.get(provider, '')}{model}"

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send completion request with automatic fallback.

        Args:
            messages: Chat messages in OpenAI format
            provider: Override default provider
            model: Override default model
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            Response dict with content and metadata
        """
        provider = provider or self.settings.LLM_PROVIDER
        model = model or self.settings.LLM_MODEL
        model_string = self._get_model_string(provider, model)

        try:
            response = await acompletion(
                model=model_string,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.settings.LLM_TIMEOUT,
                **kwargs
            )

            return {
                "content": response.choices[0].message.content,
                "provider": provider.value,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "fallback_used": False
            }

        except (APIError, RateLimitError, Exception) as e:
            if self.settings.LLM_ENABLE_FALLBACK:
                return await self._fallback_complete(
                    messages, temperature, max_tokens, original_error=str(e), **kwargs
                )
            raise

    async def _fallback_complete(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        original_error: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute fallback to commercial provider."""
        fallback_provider = self.settings.LLM_FALLBACK_PROVIDER
        fallback_model = self.settings.LLM_FALLBACK_MODEL
        model_string = self._get_model_string(fallback_provider, fallback_model)

        response = await acompletion(
            model=model_string,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=self.settings.LLM_TIMEOUT,
            **kwargs
        )

        return {
            "content": response.choices[0].message.content,
            "provider": fallback_provider.value,
            "model": fallback_model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "fallback_used": True,
            "original_error": original_error
        }

    async def complete_with_vision(
        self,
        prompt: str,
        image_url: str,
        provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Vision completion for document understanding.
        Supports GPT-4 Vision and Qwen2.5-VL.
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]
        return await self.complete(messages, provider=provider, **kwargs)
```

### 3.4 Usage Example

```python
# Example: Document Understanding with Configurable LLM

from services.llm_gateway import LLMGateway
from config.llm_config import LLMSettings, LLMProvider

# Load settings from environment
settings = LLMSettings()

# Initialize gateway
llm = LLMGateway(settings)

# Use default provider (Qwen2.5-VL via Ollama)
result = await llm.complete_with_vision(
    prompt="Extract all diagnosis codes and procedures from this medical claim document.",
    image_url="data:image/png;base64,..."
)
print(f"Provider used: {result['provider']}")  # "ollama"
print(f"Fallback used: {result['fallback_used']}")  # False

# Force commercial provider for complex documents
result = await llm.complete_with_vision(
    prompt="Extract all diagnosis codes...",
    image_url="data:image/png;base64,...",
    provider=LLMProvider.OPENAI  # Force GPT-4 Vision
)
```

### 3.5 Environment Configuration

```bash
# .env file

# === LLM Configuration ===
# Options: openai, azure, anthropic, ollama, vllm, bedrock
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-vl:7b
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_MODEL=gpt-4-vision-preview
LLM_ENABLE_FALLBACK=true
LLM_CONFIDENCE_THRESHOLD=0.85

# Medical LLM
MEDICAL_LLM_PROVIDER=ollama
MEDICAL_LLM_MODEL=biomistral:7b
MEDICAL_LLM_FALLBACK_PROVIDER=openai
MEDICAL_LLM_FALLBACK_MODEL=gpt-4-turbo

# Provider API Keys (only needed if using that provider)
OPENAI_API_KEY=sk-...
AZURE_API_KEY=...
AZURE_API_BASE=https://your-resource.openai.azure.com/
ANTHROPIC_API_KEY=sk-ant-...

# Self-hosted endpoints
OLLAMA_BASE_URL=http://localhost:11434
VLLM_BASE_URL=http://localhost:8000
```

---

## 4. OCR Provider Abstraction

### 4.1 Configuration Schema

```python
# config/ocr_config.py

from enum import Enum
from pydantic import BaseSettings

class OCRProvider(str, Enum):
    AZURE = "azure"                    # Azure AI Document Intelligence
    GOOGLE = "google"                  # Google Cloud Vision
    AWS = "aws"                        # AWS Textract
    PADDLEOCR = "paddleocr"           # PaddleOCR (open-source)
    TESSERACT = "tesseract"           # Tesseract (open-source)
    EASYOCR = "easyocr"               # EasyOCR (open-source)

class ICRProvider(str, Enum):
    AZURE = "azure"                    # Azure AI (handwriting)
    GOOGLE = "google"                  # Google Vision (handwriting)
    TROCR = "trocr"                    # Microsoft TrOCR (open-source)
    PADDLEOCR = "paddleocr"           # PaddleOCR handwriting

class OCRSettings(BaseSettings):
    # Primary OCR
    OCR_PROVIDER: OCRProvider = OCRProvider.PADDLEOCR
    OCR_FALLBACK_PROVIDER: OCRProvider = OCRProvider.AZURE
    OCR_ENABLE_FALLBACK: bool = True
    OCR_CONFIDENCE_THRESHOLD: float = 0.90

    # Handwriting ICR
    ICR_PROVIDER: ICRProvider = ICRProvider.TROCR
    ICR_FALLBACK_PROVIDER: ICRProvider = ICRProvider.AZURE

    # Language settings
    OCR_LANGUAGES: list = ["en", "ar"]

    # Provider credentials
    AZURE_DOCUMENT_ENDPOINT: str = ""
    AZURE_DOCUMENT_KEY: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    class Config:
        env_file = ".env"
```

### 4.2 OCR Gateway Implementation

```python
# services/ocr_gateway.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from PIL import Image
import io

from config.ocr_config import OCRSettings, OCRProvider, ICRProvider

@dataclass
class OCRResult:
    text: str
    confidence: float
    bounding_boxes: List[Dict[str, Any]]
    provider: str
    language: str
    fallback_used: bool = False
    raw_response: Optional[Dict] = None

class BaseOCRProvider(ABC):
    """Abstract base class for OCR providers."""

    @abstractmethod
    async def extract_text(self, image: bytes, languages: List[str]) -> OCRResult:
        pass

    @abstractmethod
    async def extract_structured(self, image: bytes) -> Dict[str, Any]:
        """Extract structured data (tables, forms, etc.)"""
        pass

class PaddleOCRProvider(BaseOCRProvider):
    """Open-source PaddleOCR implementation."""

    def __init__(self, languages: List[str] = ["en"]):
        from paddleocr import PaddleOCR
        # Map language codes
        lang = "ar" if "ar" in languages else "en"
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=True)

    async def extract_text(self, image: bytes, languages: List[str]) -> OCRResult:
        import numpy as np
        from PIL import Image

        # Convert bytes to numpy array
        img = Image.open(io.BytesIO(image))
        img_array = np.array(img)

        # Run OCR
        result = self.ocr.ocr(img_array, cls=True)

        # Parse results
        texts = []
        boxes = []
        confidences = []

        for line in result[0]:
            box, (text, confidence) = line
            texts.append(text)
            boxes.append({"coordinates": box, "text": text, "confidence": confidence})
            confidences.append(confidence)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return OCRResult(
            text="\n".join(texts),
            confidence=avg_confidence,
            bounding_boxes=boxes,
            provider="paddleocr",
            language=languages[0] if languages else "en"
        )

    async def extract_structured(self, image: bytes) -> Dict[str, Any]:
        from paddleocr import PPStructure

        img = Image.open(io.BytesIO(image))
        img_array = np.array(img)

        table_engine = PPStructure(show_log=False)
        result = table_engine(img_array)

        return {"tables": result, "provider": "paddleocr"}

class AzureOCRProvider(BaseOCRProvider):
    """Azure AI Document Intelligence implementation."""

    def __init__(self, endpoint: str, key: str):
        from azure.ai.formrecognizer import DocumentAnalysisClient
        from azure.core.credentials import AzureKeyCredential

        self.client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

    async def extract_text(self, image: bytes, languages: List[str]) -> OCRResult:
        poller = self.client.begin_analyze_document(
            "prebuilt-read",
            document=image,
            locale=languages[0] if languages else "en-US"
        )
        result = poller.result()

        texts = []
        boxes = []
        confidences = []

        for page in result.pages:
            for line in page.lines:
                texts.append(line.content)
                boxes.append({
                    "coordinates": [p.to_dict() for p in line.polygon],
                    "text": line.content
                })

        for paragraph in result.paragraphs:
            if hasattr(paragraph, 'confidence'):
                confidences.append(paragraph.confidence)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.95

        return OCRResult(
            text="\n".join(texts),
            confidence=avg_confidence,
            bounding_boxes=boxes,
            provider="azure",
            language=languages[0] if languages else "en"
        )

    async def extract_structured(self, image: bytes) -> Dict[str, Any]:
        poller = self.client.begin_analyze_document(
            "prebuilt-document",
            document=image
        )
        result = poller.result()

        return {
            "tables": [t.to_dict() for t in result.tables],
            "key_value_pairs": [kv.to_dict() for kv in result.key_value_pairs],
            "provider": "azure"
        }

class TrOCRProvider(BaseOCRProvider):
    """Microsoft TrOCR for handwriting recognition."""

    def __init__(self):
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        self.processor = TrOCRProcessor.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        self.model = VisionEncoderDecoderModel.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )

    async def extract_text(self, image: bytes, languages: List[str]) -> OCRResult:
        import torch

        img = Image.open(io.BytesIO(image)).convert("RGB")

        pixel_values = self.processor(img, return_tensors="pt").pixel_values

        with torch.no_grad():
            generated_ids = self.model.generate(pixel_values)

        text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        return OCRResult(
            text=text,
            confidence=0.90,  # TrOCR doesn't provide confidence directly
            bounding_boxes=[],
            provider="trocr",
            language="en"
        )

    async def extract_structured(self, image: bytes) -> Dict[str, Any]:
        # TrOCR is line-based, no structured extraction
        result = await self.extract_text(image, ["en"])
        return {"text": result.text, "provider": "trocr"}

class OCRGateway:
    """
    Unified OCR interface supporting multiple providers.
    """

    def __init__(self, settings: OCRSettings):
        self.settings = settings
        self.providers: Dict[OCRProvider, BaseOCRProvider] = {}
        self.icr_providers: Dict[ICRProvider, BaseOCRProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Lazy initialization of configured providers."""
        # Initialize primary OCR provider
        if self.settings.OCR_PROVIDER == OCRProvider.PADDLEOCR:
            self.providers[OCRProvider.PADDLEOCR] = PaddleOCRProvider(
                self.settings.OCR_LANGUAGES
            )

        # Initialize fallback if enabled
        if self.settings.OCR_ENABLE_FALLBACK:
            if self.settings.OCR_FALLBACK_PROVIDER == OCRProvider.AZURE:
                self.providers[OCRProvider.AZURE] = AzureOCRProvider(
                    self.settings.AZURE_DOCUMENT_ENDPOINT,
                    self.settings.AZURE_DOCUMENT_KEY
                )

        # Initialize ICR providers
        if self.settings.ICR_PROVIDER == ICRProvider.TROCR:
            self.icr_providers[ICRProvider.TROCR] = TrOCRProvider()

    async def extract_text(
        self,
        image: bytes,
        languages: Optional[List[str]] = None,
        provider: Optional[OCRProvider] = None
    ) -> OCRResult:
        """
        Extract text from image with automatic fallback.
        """
        provider = provider or self.settings.OCR_PROVIDER
        languages = languages or self.settings.OCR_LANGUAGES

        ocr_provider = self.providers.get(provider)
        if not ocr_provider:
            raise ValueError(f"Provider {provider} not initialized")

        try:
            result = await ocr_provider.extract_text(image, languages)

            # Check confidence threshold for fallback
            if (self.settings.OCR_ENABLE_FALLBACK and
                result.confidence < self.settings.OCR_CONFIDENCE_THRESHOLD):
                return await self._fallback_extract(image, languages, result)

            return result

        except Exception as e:
            if self.settings.OCR_ENABLE_FALLBACK:
                return await self._fallback_extract(image, languages, error=str(e))
            raise

    async def _fallback_extract(
        self,
        image: bytes,
        languages: List[str],
        original_result: Optional[OCRResult] = None,
        error: Optional[str] = None
    ) -> OCRResult:
        """Execute fallback to commercial provider."""
        fallback = self.providers.get(self.settings.OCR_FALLBACK_PROVIDER)
        if not fallback:
            if original_result:
                return original_result
            raise ValueError("Fallback provider not configured")

        result = await fallback.extract_text(image, languages)
        result.fallback_used = True
        return result

    async def extract_handwriting(
        self,
        image: bytes,
        provider: Optional[ICRProvider] = None
    ) -> OCRResult:
        """Extract handwritten text."""
        provider = provider or self.settings.ICR_PROVIDER
        icr_provider = self.icr_providers.get(provider)

        if not icr_provider:
            raise ValueError(f"ICR Provider {provider} not initialized")

        return await icr_provider.extract_text(image, ["en"])
```

### 4.3 Environment Configuration

```bash
# .env file

# === OCR Configuration ===
# Options: azure, google, aws, paddleocr, tesseract, easyocr
OCR_PROVIDER=paddleocr
OCR_FALLBACK_PROVIDER=azure
OCR_ENABLE_FALLBACK=true
OCR_CONFIDENCE_THRESHOLD=0.90
OCR_LANGUAGES=en,ar

# Handwriting ICR
# Options: azure, google, trocr, paddleocr
ICR_PROVIDER=trocr
ICR_FALLBACK_PROVIDER=azure

# Azure credentials (only needed if using Azure)
AZURE_DOCUMENT_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_KEY=your-key-here

# Google credentials (only needed if using Google)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# AWS credentials (only needed if using AWS Textract)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

---

## 5. Translation Provider Abstraction

### 5.1 Configuration Schema

```python
# config/translation_config.py

from enum import Enum
from pydantic import BaseSettings

class TranslationProvider(str, Enum):
    AZURE = "azure"              # Azure Translator
    GOOGLE = "google"            # Google Translate
    AWS = "aws"                  # AWS Translate
    DEEPL = "deepl"              # DeepL
    LIBRETRANSLATE = "libre"     # LibreTranslate (open-source)
    ARGOS = "argos"              # Argos Translate (open-source)

class TranslationSettings(BaseSettings):
    TRANSLATION_PROVIDER: TranslationProvider = TranslationProvider.LIBRETRANSLATE
    TRANSLATION_FALLBACK_PROVIDER: TranslationProvider = TranslationProvider.AZURE
    TRANSLATION_ENABLE_FALLBACK: bool = True

    # LibreTranslate settings
    LIBRETRANSLATE_URL: str = "http://localhost:5000"

    # Commercial API keys
    AZURE_TRANSLATOR_KEY: str = ""
    AZURE_TRANSLATOR_REGION: str = "global"
    GOOGLE_TRANSLATE_KEY: str = ""
    DEEPL_API_KEY: str = ""

    class Config:
        env_file = ".env"
```

### 5.2 Translation Gateway Implementation

```python
# services/translation_gateway.py

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass

from config.translation_config import TranslationSettings, TranslationProvider

@dataclass
class TranslationResult:
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    fallback_used: bool = False

class BaseTranslationProvider(ABC):
    @abstractmethod
    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> TranslationResult:
        pass

class LibreTranslateProvider(BaseTranslationProvider):
    """Open-source LibreTranslate implementation."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> TranslationResult:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/translate",
                json={
                    "q": text,
                    "source": source_lang,
                    "target": target_lang,
                    "format": "text"
                }
            )
            result = response.json()

        return TranslationResult(
            translated_text=result["translatedText"],
            source_language=source_lang,
            target_language=target_lang,
            provider="libretranslate"
        )

class AzureTranslateProvider(BaseTranslationProvider):
    """Azure Translator implementation."""

    def __init__(self, key: str, region: str):
        self.key = key
        self.region = region
        self.endpoint = "https://api.cognitive.microsofttranslator.com"

    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> TranslationResult:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/translate",
                params={"api-version": "3.0", "to": target_lang, "from": source_lang},
                headers={
                    "Ocp-Apim-Subscription-Key": self.key,
                    "Ocp-Apim-Subscription-Region": self.region,
                    "Content-Type": "application/json"
                },
                json=[{"text": text}]
            )
            result = response.json()

        return TranslationResult(
            translated_text=result[0]["translations"][0]["text"],
            source_language=source_lang,
            target_language=target_lang,
            provider="azure"
        )

class TranslationGateway:
    """Unified translation interface."""

    def __init__(self, settings: TranslationSettings):
        self.settings = settings
        self.providers: Dict[TranslationProvider, BaseTranslationProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        if self.settings.TRANSLATION_PROVIDER == TranslationProvider.LIBRETRANSLATE:
            self.providers[TranslationProvider.LIBRETRANSLATE] = LibreTranslateProvider(
                self.settings.LIBRETRANSLATE_URL
            )

        if self.settings.TRANSLATION_FALLBACK_PROVIDER == TranslationProvider.AZURE:
            self.providers[TranslationProvider.AZURE] = AzureTranslateProvider(
                self.settings.AZURE_TRANSLATOR_KEY,
                self.settings.AZURE_TRANSLATOR_REGION
            )

    async def translate(
        self,
        text: str,
        source_lang: str = "ar",
        target_lang: str = "en",
        provider: Optional[TranslationProvider] = None
    ) -> TranslationResult:
        provider = provider or self.settings.TRANSLATION_PROVIDER
        translator = self.providers.get(provider)

        try:
            return await translator.translate(text, source_lang, target_lang)
        except Exception as e:
            if self.settings.TRANSLATION_ENABLE_FALLBACK:
                fallback = self.providers.get(self.settings.TRANSLATION_FALLBACK_PROVIDER)
                result = await fallback.translate(text, source_lang, target_lang)
                result.fallback_used = True
                return result
            raise
```

---

## 6. Rules Engine Provider Abstraction

### 6.1 Configuration Schema

```python
# config/rules_config.py

from enum import Enum
from pydantic import BaseSettings

class RulesProvider(str, Enum):
    ZEN = "zen"              # GoRules ZEN (open-source)
    DROOLS = "drools"        # Drools (open-source, Java)
    NECTED = "nected"        # Nected (commercial)
    INRULE = "inrule"        # InRule (commercial)
    CUSTOM = "custom"        # Custom Python rules

class RulesSettings(BaseSettings):
    RULES_PROVIDER: RulesProvider = RulesProvider.ZEN
    RULES_FALLBACK_PROVIDER: RulesProvider = RulesProvider.CUSTOM

    # ZEN settings
    ZEN_RULES_PATH: str = "./rules"

    # Nected settings
    NECTED_API_KEY: str = ""
    NECTED_WORKSPACE: str = ""

    class Config:
        env_file = ".env"
```

### 6.2 Rules Gateway Implementation

```python
# services/rules_gateway.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class RulesResult:
    output: Dict[str, Any]
    rules_executed: List[str]
    provider: str
    execution_time_ms: float

class BaseRulesProvider(ABC):
    @abstractmethod
    async def evaluate(self, rule_name: str, context: Dict[str, Any]) -> RulesResult:
        pass

class ZenRulesProvider(BaseRulesProvider):
    """GoRules ZEN open-source rules engine."""

    def __init__(self, rules_path: str):
        import zen
        self.engine = zen.ZenEngine()
        self.rules_path = rules_path

    async def evaluate(self, rule_name: str, context: Dict[str, Any]) -> RulesResult:
        import time
        import json

        start = time.time()

        # Load decision graph
        with open(f"{self.rules_path}/{rule_name}.json", "r") as f:
            graph = json.load(f)

        # Evaluate
        decision = self.engine.create_decision(graph)
        result = decision.evaluate(context)

        execution_time = (time.time() - start) * 1000

        return RulesResult(
            output=result,
            rules_executed=[rule_name],
            provider="zen",
            execution_time_ms=execution_time
        )

class CustomPythonRulesProvider(BaseRulesProvider):
    """Fallback Python-based rules engine."""

    def __init__(self):
        self.rules_registry = {}

    def register_rule(self, name: str, rule_func):
        self.rules_registry[name] = rule_func

    async def evaluate(self, rule_name: str, context: Dict[str, Any]) -> RulesResult:
        import time

        start = time.time()

        if rule_name not in self.rules_registry:
            raise ValueError(f"Rule {rule_name} not registered")

        result = self.rules_registry[rule_name](context)

        execution_time = (time.time() - start) * 1000

        return RulesResult(
            output=result,
            rules_executed=[rule_name],
            provider="custom_python",
            execution_time_ms=execution_time
        )

class RulesGateway:
    """Unified rules engine interface."""

    def __init__(self, settings: RulesSettings):
        self.settings = settings
        self.providers: Dict[RulesProvider, BaseRulesProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        if self.settings.RULES_PROVIDER == RulesProvider.ZEN:
            self.providers[RulesProvider.ZEN] = ZenRulesProvider(
                self.settings.ZEN_RULES_PATH
            )

        # Always initialize custom as fallback
        self.providers[RulesProvider.CUSTOM] = CustomPythonRulesProvider()

    async def evaluate_benefit(
        self,
        activity: Dict[str, Any],
        policy: Dict[str, Any],
        provider: Optional[RulesProvider] = None
    ) -> RulesResult:
        """Evaluate benefit rules for a claim activity."""
        provider = provider or self.settings.RULES_PROVIDER
        engine = self.providers.get(provider)

        context = {
            "activity": activity,
            "policy": policy,
            "benefitClass": policy.get("benefit_class"),
            "patientCategory": policy.get("patient_category")
        }

        return await engine.evaluate("benefit_calculation", context)

    async def evaluate_patient_share(
        self,
        activity: Dict[str, Any],
        benefit: Dict[str, Any],
        thresholds: Dict[str, Any]
    ) -> RulesResult:
        """Calculate patient share with threshold validation."""
        context = {
            "activity": activity,
            "benefit": benefit,
            "maxPatientShare": thresholds.get("max_patient_share"),
            "benefitClassThreshold": thresholds.get("benefit_class_threshold")
        }

        return await self.providers[self.settings.RULES_PROVIDER].evaluate(
            "patient_share_calculation", context
        )
```

---

## 7. Currency API Provider Abstraction

### 7.1 Configuration and Implementation

```python
# config/currency_config.py

from enum import Enum
from pydantic import BaseSettings

class CurrencyProvider(str, Enum):
    XE = "xe"                      # Xe (commercial)
    FIXER = "fixer"                # Fixer.io (commercial)
    EXCHANGERATE = "exchangerate"  # ExchangeRate-API (free tier)
    FRANKFURTER = "frankfurter"    # Frankfurter (open-source)
    FAWAZ = "fawaz"                # fawazahmed0 (free, unlimited)

class CurrencySettings(BaseSettings):
    CURRENCY_PROVIDER: CurrencyProvider = CurrencyProvider.FAWAZ
    CURRENCY_FALLBACK_PROVIDER: CurrencyProvider = CurrencyProvider.FIXER
    CURRENCY_CACHE_TTL: int = 3600  # 1 hour cache

    # API keys
    XE_API_KEY: str = ""
    FIXER_API_KEY: str = ""

    class Config:
        env_file = ".env"
```

```python
# services/currency_gateway.py

from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ExchangeRate:
    base_currency: str
    target_currency: str
    rate: float
    timestamp: datetime
    provider: str

class BaseCurrencyProvider(ABC):
    @abstractmethod
    async def get_rate(self, base: str, target: str) -> ExchangeRate:
        pass

class FawazCurrencyProvider(BaseCurrencyProvider):
    """Free, unlimited fawazahmed0 API."""

    async def get_rate(self, base: str, target: str) -> ExchangeRate:
        import httpx

        base_lower = base.lower()
        target_lower = target.lower()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base_lower}.json"
            )
            data = response.json()

        rate = data[base_lower].get(target_lower)

        return ExchangeRate(
            base_currency=base,
            target_currency=target,
            rate=rate,
            timestamp=datetime.utcnow(),
            provider="fawazahmed0"
        )

class FixerCurrencyProvider(BaseCurrencyProvider):
    """Fixer.io commercial API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_rate(self, base: str, target: str) -> ExchangeRate:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://data.fixer.io/api/latest",
                params={"access_key": self.api_key, "base": base, "symbols": target}
            )
            data = response.json()

        return ExchangeRate(
            base_currency=base,
            target_currency=target,
            rate=data["rates"][target],
            timestamp=datetime.fromtimestamp(data["timestamp"]),
            provider="fixer"
        )

class CurrencyGateway:
    """Unified currency exchange interface with caching."""

    def __init__(self, settings: CurrencySettings, cache):
        self.settings = settings
        self.cache = cache
        self.providers: Dict[CurrencyProvider, BaseCurrencyProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        self.providers[CurrencyProvider.FAWAZ] = FawazCurrencyProvider()

        if self.settings.FIXER_API_KEY:
            self.providers[CurrencyProvider.FIXER] = FixerCurrencyProvider(
                self.settings.FIXER_API_KEY
            )

    async def get_exchange_rate(
        self,
        base: str,
        target: str,
        provider: Optional[CurrencyProvider] = None
    ) -> ExchangeRate:
        # Check cache first
        cache_key = f"exchange_rate:{base}:{target}"
        cached = await self.cache.get(cache_key)
        if cached:
            return ExchangeRate(**cached)

        provider = provider or self.settings.CURRENCY_PROVIDER
        currency_provider = self.providers.get(provider)

        try:
            rate = await currency_provider.get_rate(base, target)

            # Cache the result
            await self.cache.set(
                cache_key,
                rate.__dict__,
                ttl=self.settings.CURRENCY_CACHE_TTL
            )

            return rate

        except Exception as e:
            # Fallback to commercial provider
            fallback = self.providers.get(self.settings.CURRENCY_FALLBACK_PROVIDER)
            if fallback:
                return await fallback.get_rate(base, target)
            raise

    async def convert_amount(
        self,
        amount: float,
        from_currency: str,
        to_currency: str
    ) -> Dict[str, Any]:
        rate = await self.get_exchange_rate(from_currency, to_currency)
        converted = amount * rate.rate

        return {
            "original_amount": amount,
            "original_currency": from_currency,
            "converted_amount": round(converted, 2),
            "target_currency": to_currency,
            "exchange_rate": rate.rate,
            "rate_timestamp": rate.timestamp.isoformat(),
            "provider": rate.provider
        }
```

---

## 8. Medical NLP Provider Abstraction

### 8.1 Configuration and Implementation

```python
# config/medical_nlp_config.py

from enum import Enum
from pydantic import BaseSettings

class MedicalNLPProvider(str, Enum):
    AWS_COMPREHEND = "aws_comprehend"    # AWS Comprehend Medical
    AZURE_TEXT = "azure_text"            # Azure Text Analytics for Health
    MEDCAT = "medcat"                    # MedCAT (open-source)
    MEDSPACY = "medspacy"                # medspaCy (open-source)
    SCISPACY = "scispacy"                # scispaCy (open-source)

class MedicalNLPSettings(BaseSettings):
    MEDICAL_NLP_PROVIDER: MedicalNLPProvider = MedicalNLPProvider.MEDCAT
    MEDICAL_NLP_FALLBACK_PROVIDER: MedicalNLPProvider = MedicalNLPProvider.AWS_COMPREHEND

    # UMLS settings for MedCAT
    UMLS_PATH: str = "./models/umls"

    class Config:
        env_file = ".env"
```

```python
# services/medical_nlp_gateway.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class MedicalEntity:
    text: str
    type: str  # DIAGNOSIS, PROCEDURE, MEDICATION, etc.
    code: str  # ICD-10, CPT, RxNorm, etc.
    code_system: str
    confidence: float
    start: int
    end: int

@dataclass
class MedicalNLPResult:
    entities: List[MedicalEntity]
    negations: List[str]
    provider: str

class BaseMedicalNLPProvider(ABC):
    @abstractmethod
    async def extract_entities(self, text: str) -> MedicalNLPResult:
        pass

class MedCATProvider(BaseMedicalNLPProvider):
    """Open-source MedCAT implementation."""

    def __init__(self, model_path: str):
        from medcat.cat import CAT
        self.cat = CAT.load_model_pack(model_path)

    async def extract_entities(self, text: str) -> MedicalNLPResult:
        doc = self.cat(text)

        entities = []
        for ent in doc.ents:
            entities.append(MedicalEntity(
                text=ent.text,
                type=ent._.type,
                code=ent._.cui,
                code_system="UMLS",
                confidence=ent._.confidence,
                start=ent.start_char,
                end=ent.end_char
            ))

        # Extract negations
        negations = [ent.text for ent in doc.ents if ent._.negex]

        return MedicalNLPResult(
            entities=entities,
            negations=negations,
            provider="medcat"
        )

class MedspaCyProvider(BaseMedicalNLPProvider):
    """Open-source medspaCy implementation."""

    def __init__(self):
        import medspacy
        self.nlp = medspacy.load()

    async def extract_entities(self, text: str) -> MedicalNLPResult:
        doc = self.nlp(text)

        entities = []
        for ent in doc.ents:
            entities.append(MedicalEntity(
                text=ent.text,
                type=ent.label_,
                code="",
                code_system="",
                confidence=0.9,
                start=ent.start_char,
                end=ent.end_char
            ))

        # Extract negations using ConText
        negations = []
        for ent in doc.ents:
            if ent._.is_negated:
                negations.append(ent.text)

        return MedicalNLPResult(
            entities=entities,
            negations=negations,
            provider="medspacy"
        )

class MedicalNLPGateway:
    """Unified medical NLP interface."""

    def __init__(self, settings: MedicalNLPSettings):
        self.settings = settings
        self.providers: Dict[MedicalNLPProvider, BaseMedicalNLPProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        if self.settings.MEDICAL_NLP_PROVIDER == MedicalNLPProvider.MEDCAT:
            self.providers[MedicalNLPProvider.MEDCAT] = MedCATProvider(
                self.settings.UMLS_PATH
            )
        elif self.settings.MEDICAL_NLP_PROVIDER == MedicalNLPProvider.MEDSPACY:
            self.providers[MedicalNLPProvider.MEDSPACY] = MedspaCyProvider()

    async def extract_medical_entities(self, text: str) -> MedicalNLPResult:
        provider = self.providers.get(self.settings.MEDICAL_NLP_PROVIDER)
        return await provider.extract_entities(text)

    async def extract_diagnosis_codes(self, text: str) -> List[MedicalEntity]:
        result = await self.extract_medical_entities(text)
        return [e for e in result.entities if e.type in ["DIAGNOSIS", "PROBLEM"]]

    async def extract_procedure_codes(self, text: str) -> List[MedicalEntity]:
        result = await self.extract_medical_entities(text)
        return [e for e in result.entities if e.type in ["PROCEDURE", "TREATMENT"]]
```

---

## 9. Complete Configuration Example

### 9.1 Master Configuration File

```python
# config/settings.py

from pydantic import BaseSettings
from config.llm_config import LLMSettings
from config.ocr_config import OCRSettings
from config.translation_config import TranslationSettings
from config.rules_config import RulesSettings
from config.currency_config import CurrencySettings
from config.medical_nlp_config import MedicalNLPSettings

class Settings(BaseSettings):
    """Master settings combining all provider configurations."""

    # Application
    APP_NAME: str = "ReImp Claims Processing"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Provider configurations (nested)
    llm: LLMSettings = LLMSettings()
    ocr: OCRSettings = OCRSettings()
    translation: TranslationSettings = TranslationSettings()
    rules: RulesSettings = RulesSettings()
    currency: CurrencySettings = CurrencySettings()
    medical_nlp: MedicalNLPSettings = MedicalNLPSettings()

    # Global fallback behavior
    ENABLE_FALLBACK_GLOBALLY: bool = True
    LOG_PROVIDER_USAGE: bool = True
    METRICS_ENABLED: bool = True

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

# Singleton instance
settings = Settings()
```

### 9.2 Complete .env Example

```bash
# ============================================================
# REIMP CLAIMS PROCESSING - CONFIGURABLE PROVIDER SETTINGS
# ============================================================

# === Application ===
APP_NAME=ReImp Claims Processing
ENVIRONMENT=production
DEBUG=false
ENABLE_FALLBACK_GLOBALLY=true
LOG_PROVIDER_USAGE=true

# ============================================================
# LLM PROVIDERS
# ============================================================

# Primary LLM (Document Understanding)
# Options: openai, azure, anthropic, ollama, vllm, bedrock
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-vl:7b

# Fallback LLM (when primary fails or low confidence)
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_MODEL=gpt-4-vision-preview
LLM_ENABLE_FALLBACK=true
LLM_CONFIDENCE_THRESHOLD=0.85

# Medical LLM (Clinical Validation)
MEDICAL_LLM_PROVIDER=ollama
MEDICAL_LLM_MODEL=biomistral:7b
MEDICAL_LLM_FALLBACK_PROVIDER=openai
MEDICAL_LLM_FALLBACK_MODEL=gpt-4-turbo

# Self-hosted endpoints
OLLAMA_BASE_URL=http://localhost:11434
VLLM_BASE_URL=http://localhost:8000

# Commercial API Keys (only fill if using)
OPENAI_API_KEY=sk-your-key-here
AZURE_API_KEY=
AZURE_API_BASE=
ANTHROPIC_API_KEY=

# ============================================================
# OCR PROVIDERS
# ============================================================

# Primary OCR
# Options: azure, google, aws, paddleocr, tesseract, easyocr
OCR_PROVIDER=paddleocr
OCR_FALLBACK_PROVIDER=azure
OCR_ENABLE_FALLBACK=true
OCR_CONFIDENCE_THRESHOLD=0.90
OCR_LANGUAGES=en,ar

# Handwriting ICR
# Options: azure, google, trocr, paddleocr
ICR_PROVIDER=trocr
ICR_FALLBACK_PROVIDER=azure

# Azure Document Intelligence (if using)
AZURE_DOCUMENT_ENDPOINT=
AZURE_DOCUMENT_KEY=

# ============================================================
# TRANSLATION PROVIDERS
# ============================================================

# Primary Translation
# Options: azure, google, deepl, libre, argos
TRANSLATION_PROVIDER=libre
TRANSLATION_FALLBACK_PROVIDER=azure
TRANSLATION_ENABLE_FALLBACK=true

# LibreTranslate (self-hosted)
LIBRETRANSLATE_URL=http://localhost:5000

# Azure Translator (if using)
AZURE_TRANSLATOR_KEY=
AZURE_TRANSLATOR_REGION=global

# ============================================================
# RULES ENGINE PROVIDERS
# ============================================================

# Primary Rules Engine
# Options: zen, drools, nected, inrule, custom
RULES_PROVIDER=zen
RULES_FALLBACK_PROVIDER=custom

# ZEN settings
ZEN_RULES_PATH=./rules

# Nected (if using commercial)
NECTED_API_KEY=
NECTED_WORKSPACE=

# ============================================================
# CURRENCY PROVIDERS
# ============================================================

# Primary Currency API
# Options: xe, fixer, exchangerate, frankfurter, fawaz
CURRENCY_PROVIDER=fawaz
CURRENCY_FALLBACK_PROVIDER=fixer
CURRENCY_CACHE_TTL=3600

# Commercial APIs (if using)
XE_API_KEY=
FIXER_API_KEY=

# ============================================================
# MEDICAL NLP PROVIDERS
# ============================================================

# Primary Medical NLP
# Options: aws_comprehend, azure_text, medcat, medspacy, scispacy
MEDICAL_NLP_PROVIDER=medcat
MEDICAL_NLP_FALLBACK_PROVIDER=aws_comprehend

# MedCAT model path
UMLS_PATH=./models/umls

# ============================================================
# MESSAGE QUEUE PROVIDERS
# ============================================================

# Options: kafka, redis_streams, nats, rabbitmq
MESSAGE_QUEUE_PROVIDER=redis_streams

# Redis (if using Redis Streams)
REDIS_URL=redis://localhost:6379

# Kafka (if using)
KAFKA_BOOTSTRAP_SERVERS=
KAFKA_SECURITY_PROTOCOL=

# NATS (if using)
NATS_URL=nats://localhost:4222

# ============================================================
# FRAUD DETECTION PROVIDERS
# ============================================================

# Options: custom_ml, third_party
FWA_PROVIDER=custom_ml
FWA_MODEL_PATH=./models/fwa_xgboost.pkl
```

---

## 10. Provider Selection Decision Matrix

### 10.1 When to Use Commercial vs Open-Source

| Scenario | Recommended Provider | Rationale |
|----------|---------------------|-----------|
| **Development/Testing** | Open-Source | No cost, fast iteration |
| **Simple Documents** | Open-Source | PaddleOCR handles 98%+ accurately |
| **Complex Handwriting** | Commercial Fallback | Higher accuracy needed |
| **Medical Validation** | Hybrid | Open-source primary, GPT-4 for edge cases |
| **Sensitive Data** | Open-Source | Data never leaves infrastructure |
| **High Volume** | Open-Source | No per-request costs |
| **Critical Decisions** | Commercial Fallback | Higher accuracy/reliability |
| **Arabic Documents** | Hybrid | Test both, use best performer |

### 10.2 Automatic Fallback Triggers

| Condition | Action |
|-----------|--------|
| OCR confidence < 90% | Fallback to Azure |
| LLM response uncertain | Fallback to GPT-4 |
| Translation quality low | Fallback to Azure Translator |
| Open-source service down | Automatic failover |
| Rate limit exceeded | Switch provider |
| Latency > threshold | Try alternative |

---

## 11. Cost Optimization Strategies

### 11.1 Tiered Processing

```python
# Example: Tiered document processing based on complexity

async def process_document_tiered(document: bytes, complexity: str):
    """
    Process documents with tiered provider selection.

    Tiers:
    - simple: Open-source only (free)
    - standard: Open-source with commercial fallback
    - complex: Commercial primary (higher accuracy)
    """

    if complexity == "simple":
        # Use only open-source
        result = await ocr_gateway.extract_text(
            document,
            provider=OCRProvider.PADDLEOCR
        )
        # Disable fallback
        return result

    elif complexity == "standard":
        # Open-source with automatic fallback
        return await ocr_gateway.extract_text(document)

    elif complexity == "complex":
        # Commercial primary for complex documents
        return await ocr_gateway.extract_text(
            document,
            provider=OCRProvider.AZURE
        )
```

### 11.2 Estimated Cost by Configuration

| Configuration | Monthly Cost (10K claims) | Quality |
|--------------|---------------------------|---------|
| **100% Open-Source** | ~$500 (infra only) | 90-95% |
| **90% Open + 10% Commercial** | ~$1,500 | 95-97% |
| **70% Open + 30% Commercial** | ~$5,000 | 97-99% |
| **100% Commercial** | ~$20,000+ | 99%+ |

---

## 12. Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Set up provider abstraction layer
- [ ] Implement LLM Gateway with LiteLLM
- [ ] Implement OCR Gateway
- [ ] Configure environment variables
- [ ] Set up Ollama with Qwen2.5-VL and BioMistral

### Phase 2: Additional Providers
- [ ] Implement Translation Gateway
- [ ] Implement Rules Gateway (GoRules ZEN)
- [ ] Implement Currency Gateway
- [ ] Implement Medical NLP Gateway

### Phase 3: Fallback & Monitoring
- [ ] Configure fallback providers
- [ ] Implement confidence-based routing
- [ ] Add provider usage metrics
- [ ] Set up alerts for fallback usage

### Phase 4: Optimization
- [ ] Implement tiered processing
- [ ] Add caching layer
- [ ] Fine-tune confidence thresholds
- [ ] A/B test provider accuracy

---

## 13. Evidence Citations

### Primary Sources

| Tool | URL | License |
|------|-----|---------|
| LiteLLM | https://github.com/BerriAI/litellm | MIT |
| GoRules ZEN | https://github.com/gorules/zen | MIT |
| PaddleOCR | https://github.com/PaddlePaddle/PaddleOCR | Apache 2.0 |
| TrOCR | https://huggingface.co/microsoft/trocr-base-handwritten | MIT |
| Qwen2.5-VL | https://github.com/QwenLM/Qwen2-VL | Apache 2.0 |
| BioMistral | https://huggingface.co/BioMistral/BioMistral-7B | Apache 2.0 |
| LibreTranslate | https://github.com/LibreTranslate/LibreTranslate | AGPL-3.0 |
| MedCAT | https://github.com/CogStack/MedCAT | MIT |
| medspaCy | https://github.com/medspacy/medspacy | MIT |

### Research References

| Topic | Source |
|-------|--------|
| LLM Gateways 2025 | https://dev.to/kuldeep_paul/list-of-top-5-llm-gateways-in-2025-3iak |
| Strategy Pattern for ML | https://ajisamudra.medium.com/strategy-design-pattern-for-effective-ml-pipeline |
| ML Pipeline Architecture | https://neptune.ai/blog/ml-pipeline-architecture-design-patterns |

---

## 14. Summary

This configurable hybrid architecture enables:

1. **Cost Control**: Default to open-source, fallback to commercial
2. **Flexibility**: Switch providers via environment variables
3. **Resilience**: Automatic failover on failures
4. **Privacy**: Keep sensitive data on-premises
5. **Quality**: Use commercial APIs for complex edge cases
6. **Scalability**: No per-request limits with open-source

**Recommended Starting Configuration**:
- LLM: Qwen2.5-VL (Ollama) → GPT-4 Vision fallback
- OCR: PaddleOCR → Azure fallback
- Translation: LibreTranslate → Azure fallback
- Rules: GoRules ZEN
- Currency: fawazahmed0 API → Fixer fallback
- Medical NLP: MedCAT + medspaCy

---

**Document Version**: 1.0
**Last Updated**: December 18, 2025
**Related Documents**:
- [01_reimbursement_claims_solution_research.md](01_reimbursement_claims_solution_research.md) - Commercial Stack
- [02_cost_effective_alternatives_research.md](02_cost_effective_alternatives_research.md) - Open-Source Stack
