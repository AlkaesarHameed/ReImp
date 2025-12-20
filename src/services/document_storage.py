"""
Document Storage Service with MinIO.

Provides:
- File upload to MinIO object storage
- File download and presigned URLs
- Tenant-isolated bucket management
- Duplicate detection via content hashing

Source: https://min.io/docs/minio/linux/developers/python/API.html
Verified: 2025-12-18
"""

import hashlib
import io
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import BinaryIO, Optional
from uuid import uuid4

from src.core.enums import DocumentType

logger = logging.getLogger(__name__)


@dataclass
class StorageConfig:
    """MinIO storage configuration."""

    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    region: str = "us-east-1"
    default_bucket: str = "claims-documents"
    presigned_url_expiry: int = 3600  # 1 hour


@dataclass
class UploadResult:
    """Result of a document upload operation."""

    success: bool
    document_id: str = ""
    storage_path: str = ""
    storage_bucket: str = ""
    file_hash: str = ""
    file_size: int = 0
    content_type: str = ""
    error: Optional[str] = None
    is_duplicate: bool = False
    duplicate_document_id: Optional[str] = None


@dataclass
class DownloadResult:
    """Result of a document download operation."""

    success: bool
    data: Optional[bytes] = None
    content_type: str = ""
    file_size: int = 0
    error: Optional[str] = None


@dataclass
class PresignedUrlResult:
    """Result of presigned URL generation."""

    success: bool
    url: str = ""
    expires_in: int = 0
    error: Optional[str] = None


# =============================================================================
# Content Type Validation
# =============================================================================

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/gif",
    "image/bmp",
    "image/webp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def validate_content_type(content_type: str) -> bool:
    """Validate if content type is allowed for upload."""
    return content_type.lower() in ALLOWED_CONTENT_TYPES


def get_extension_from_content_type(content_type: str) -> str:
    """Get file extension from content type."""
    mapping = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/tiff": ".tiff",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/webp": ".webp",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }
    return mapping.get(content_type.lower(), ".bin")


# =============================================================================
# Document Storage Service
# =============================================================================


class DocumentStorageService:
    """
    Service for document storage using MinIO.

    Handles:
    - File upload with deduplication
    - File download
    - Presigned URL generation
    - Tenant-isolated bucket management
    """

    def __init__(
        self,
        config: Optional[StorageConfig] = None,
        minio_client=None,
    ):
        """
        Initialize the document storage service.

        Args:
            config: Storage configuration
            minio_client: Optional pre-configured MinIO client (for testing)
        """
        self.config = config or StorageConfig()
        self._client = minio_client
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize MinIO client and ensure buckets exist."""
        if self._initialized:
            return

        if self._client is None:
            try:
                from minio import Minio

                self._client = Minio(
                    endpoint=self.config.endpoint,
                    access_key=self.config.access_key,
                    secret_key=self.config.secret_key,
                    secure=self.config.secure,
                    region=self.config.region,
                )
                logger.info(f"MinIO client initialized: {self.config.endpoint}")
            except ImportError:
                logger.warning(
                    "minio package not installed. Using in-memory storage for development."
                )
                self._client = InMemoryStorage()
            except Exception as e:
                logger.error(f"Failed to initialize MinIO client: {e}")
                self._client = InMemoryStorage()

        # Ensure default bucket exists
        await self._ensure_bucket(self.config.default_bucket)
        self._initialized = True

    async def _ensure_bucket(self, bucket_name: str) -> None:
        """Ensure bucket exists, create if not."""
        try:
            if isinstance(self._client, InMemoryStorage):
                self._client.ensure_bucket(bucket_name)
            else:
                if not self._client.bucket_exists(bucket_name):
                    self._client.make_bucket(bucket_name)
                    logger.info(f"Created bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to ensure bucket {bucket_name}: {e}")
            raise

    def _get_tenant_bucket(self, tenant_id: str) -> str:
        """Get or create tenant-specific bucket name."""
        # Use a prefix pattern: claims-documents-{tenant_id}
        # For simplicity, we'll use the default bucket with tenant prefixes in paths
        return self.config.default_bucket

    def _generate_storage_path(
        self,
        tenant_id: str,
        document_type: DocumentType,
        filename: str,
        document_id: str,
    ) -> str:
        """
        Generate a storage path for the document.

        Path structure: {tenant_id}/{document_type}/{YYYY}/{MM}/{document_id}/{filename}
        """
        from datetime import datetime

        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")

        # Sanitize filename
        safe_filename = "".join(
            c for c in filename if c.isalnum() or c in ".-_"
        ).rstrip()
        if not safe_filename:
            safe_filename = "document"

        return f"{tenant_id}/{document_type.value}/{year}/{month}/{document_id}/{safe_filename}"

    def _compute_file_hash(self, data: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(data).hexdigest()

    async def upload_document(
        self,
        tenant_id: str,
        document_type: DocumentType,
        filename: str,
        data: BinaryIO | bytes,
        content_type: str,
        check_duplicate: bool = True,
        existing_hashes: Optional[set[str]] = None,
    ) -> UploadResult:
        """
        Upload a document to storage.

        Args:
            tenant_id: Tenant ID for isolation
            document_type: Type of document
            filename: Original filename
            data: File data (bytes or file-like object)
            content_type: MIME type
            check_duplicate: Whether to check for duplicates
            existing_hashes: Set of existing file hashes for duplicate detection

        Returns:
            UploadResult with storage details
        """
        await self.initialize()

        # Validate content type
        if not validate_content_type(content_type):
            return UploadResult(
                success=False,
                error=f"Content type not allowed: {content_type}",
            )

        # Read data if file-like object
        if hasattr(data, "read"):
            file_bytes = data.read()
        else:
            file_bytes = data

        # Validate file size
        file_size = len(file_bytes)
        if file_size > MAX_FILE_SIZE:
            return UploadResult(
                success=False,
                error=f"File size {file_size} exceeds maximum {MAX_FILE_SIZE}",
            )

        if file_size == 0:
            return UploadResult(
                success=False,
                error="Empty file not allowed",
            )

        # Compute hash
        file_hash = self._compute_file_hash(file_bytes)

        # Check for duplicates
        if check_duplicate and existing_hashes and file_hash in existing_hashes:
            return UploadResult(
                success=True,
                file_hash=file_hash,
                is_duplicate=True,
                error="Duplicate document detected",
            )

        # Generate document ID and path
        document_id = str(uuid4())
        bucket = self._get_tenant_bucket(tenant_id)
        storage_path = self._generate_storage_path(
            tenant_id, document_type, filename, document_id
        )

        try:
            if isinstance(self._client, InMemoryStorage):
                self._client.put_object(
                    bucket, storage_path, file_bytes, content_type
                )
            else:
                self._client.put_object(
                    bucket_name=bucket,
                    object_name=storage_path,
                    data=io.BytesIO(file_bytes),
                    length=file_size,
                    content_type=content_type,
                )

            logger.info(f"Uploaded document {document_id} to {bucket}/{storage_path}")

            return UploadResult(
                success=True,
                document_id=document_id,
                storage_path=storage_path,
                storage_bucket=bucket,
                file_hash=file_hash,
                file_size=file_size,
                content_type=content_type,
            )

        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            return UploadResult(
                success=False,
                error=f"Upload failed: {str(e)}",
            )

    async def download_document(
        self,
        bucket: str,
        storage_path: str,
    ) -> DownloadResult:
        """
        Download a document from storage.

        Args:
            bucket: Storage bucket
            storage_path: Object path

        Returns:
            DownloadResult with file data
        """
        await self.initialize()

        try:
            if isinstance(self._client, InMemoryStorage):
                data, content_type = self._client.get_object(bucket, storage_path)
                return DownloadResult(
                    success=True,
                    data=data,
                    content_type=content_type,
                    file_size=len(data),
                )
            else:
                response = self._client.get_object(bucket, storage_path)
                data = response.read()
                content_type = response.headers.get("Content-Type", "application/octet-stream")
                response.close()
                response.release_conn()

                return DownloadResult(
                    success=True,
                    data=data,
                    content_type=content_type,
                    file_size=len(data),
                )

        except Exception as e:
            logger.error(f"Failed to download document: {e}")
            return DownloadResult(
                success=False,
                error=f"Download failed: {str(e)}",
            )

    async def get_presigned_url(
        self,
        bucket: str,
        storage_path: str,
        expires_in: Optional[int] = None,
    ) -> PresignedUrlResult:
        """
        Generate a presigned URL for document access.

        Args:
            bucket: Storage bucket
            storage_path: Object path
            expires_in: URL expiry in seconds

        Returns:
            PresignedUrlResult with URL
        """
        await self.initialize()

        expiry = expires_in or self.config.presigned_url_expiry

        try:
            if isinstance(self._client, InMemoryStorage):
                # In-memory storage doesn't support presigned URLs
                return PresignedUrlResult(
                    success=False,
                    error="Presigned URLs not supported in development mode",
                )

            url = self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=storage_path,
                expires=timedelta(seconds=expiry),
            )

            return PresignedUrlResult(
                success=True,
                url=url,
                expires_in=expiry,
            )

        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return PresignedUrlResult(
                success=False,
                error=f"URL generation failed: {str(e)}",
            )

    async def delete_document(
        self,
        bucket: str,
        storage_path: str,
    ) -> bool:
        """
        Delete a document from storage.

        Args:
            bucket: Storage bucket
            storage_path: Object path

        Returns:
            True if deleted successfully
        """
        await self.initialize()

        try:
            if isinstance(self._client, InMemoryStorage):
                return self._client.remove_object(bucket, storage_path)
            else:
                self._client.remove_object(bucket, storage_path)
                logger.info(f"Deleted document: {bucket}/{storage_path}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    async def list_documents(
        self,
        tenant_id: str,
        prefix: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        List documents for a tenant.

        Args:
            tenant_id: Tenant ID
            prefix: Optional path prefix
            limit: Maximum results

        Returns:
            List of document metadata
        """
        await self.initialize()

        bucket = self._get_tenant_bucket(tenant_id)
        full_prefix = f"{tenant_id}/"
        if prefix:
            full_prefix += prefix

        try:
            if isinstance(self._client, InMemoryStorage):
                return self._client.list_objects(bucket, full_prefix, limit)
            else:
                objects = self._client.list_objects(
                    bucket,
                    prefix=full_prefix,
                    recursive=True,
                )
                results = []
                for obj in objects:
                    if len(results) >= limit:
                        break
                    results.append({
                        "name": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                        "etag": obj.etag,
                    })
                return results

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []

    async def document_exists(
        self,
        bucket: str,
        storage_path: str,
    ) -> bool:
        """Check if a document exists in storage."""
        await self.initialize()

        try:
            if isinstance(self._client, InMemoryStorage):
                return self._client.object_exists(bucket, storage_path)
            else:
                self._client.stat_object(bucket, storage_path)
                return True
        except Exception:
            return False


# =============================================================================
# In-Memory Storage (Development/Testing)
# =============================================================================


class InMemoryStorage:
    """
    In-memory storage for development and testing.

    Provides a MinIO-like interface without requiring MinIO.
    """

    def __init__(self):
        self._buckets: dict[str, dict[str, tuple[bytes, str]]] = {}

    def ensure_bucket(self, bucket_name: str) -> None:
        """Ensure bucket exists."""
        if bucket_name not in self._buckets:
            self._buckets[bucket_name] = {}

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists."""
        return bucket_name in self._buckets

    def make_bucket(self, bucket_name: str) -> None:
        """Create a bucket."""
        self._buckets[bucket_name] = {}

    def put_object(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Store an object."""
        self.ensure_bucket(bucket)
        self._buckets[bucket][path] = (data, content_type)

    def get_object(
        self,
        bucket: str,
        path: str,
    ) -> tuple[bytes, str]:
        """Get an object."""
        if bucket not in self._buckets or path not in self._buckets[bucket]:
            raise FileNotFoundError(f"Object not found: {bucket}/{path}")
        return self._buckets[bucket][path]

    def remove_object(self, bucket: str, path: str) -> bool:
        """Remove an object."""
        if bucket in self._buckets and path in self._buckets[bucket]:
            del self._buckets[bucket][path]
            return True
        return False

    def object_exists(self, bucket: str, path: str) -> bool:
        """Check if object exists."""
        return bucket in self._buckets and path in self._buckets[bucket]

    def list_objects(
        self,
        bucket: str,
        prefix: str,
        limit: int,
    ) -> list[dict]:
        """List objects with prefix."""
        if bucket not in self._buckets:
            return []

        results = []
        for path, (data, _) in self._buckets[bucket].items():
            if path.startswith(prefix):
                results.append({
                    "name": path,
                    "size": len(data),
                    "last_modified": None,
                    "etag": None,
                })
                if len(results) >= limit:
                    break
        return results

    def clear(self) -> None:
        """Clear all storage."""
        self._buckets.clear()


# =============================================================================
# Factory Functions
# =============================================================================


_storage_service: Optional[DocumentStorageService] = None


def get_document_storage_service(
    config: Optional[StorageConfig] = None,
) -> DocumentStorageService:
    """Get document storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = DocumentStorageService(config=config)
    return _storage_service


async def create_document_storage_service(
    config: Optional[StorageConfig] = None,
) -> DocumentStorageService:
    """Create and initialize document storage service."""
    service = DocumentStorageService(config=config)
    await service.initialize()
    return service
