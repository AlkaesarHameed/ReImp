"""
MinIO Object Storage Service
S3-compatible object storage
Source: https://min.io/docs/minio/linux/developers/python/minio-py.html
Verified: 2025-11-14
"""

from io import BytesIO
from typing import BinaryIO

from anyio import to_thread
from minio import Minio
from minio.error import S3Error

from src.api.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """
    MinIO storage service for file uploads and assets.

    Evidence: S3-compatible storage for cloud-native applications
    Source: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
    Verified: 2025-11-14
    """

    def __init__(self):
        # Initialize MinIO client
        # Evidence: MinIO client configuration
        # Source: https://min.io/docs/minio/linux/developers/python/API.html
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        logger.info(f"MinIO client initialized: {settings.MINIO_ENDPOINT}")

    def _ensure_bucket_sync(self, bucket_name: str) -> None:
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)
            logger.info(f"Created bucket: {bucket_name}")

    async def ensure_bucket(self, bucket_name: str) -> None:
        """Ensure bucket exists, running the blocking client call in a worker thread."""
        try:
            await to_thread.run_sync(self._ensure_bucket_sync, bucket_name)
        except S3Error as e:
            logger.error(f"Error ensuring bucket {bucket_name}: {e}")
            raise

    async def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_data: BinaryIO,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            bucket_name: Target bucket
            object_name: Object path/name
            file_data: File-like object
            content_type: MIME type
            metadata: Optional metadata dict

        Returns:
            Object URL

        Evidence: Object upload best practices
        Source: https://docs.aws.amazon.com/AmazonS3/latest/userguide/upload-objects.html
        """
        try:
            return await to_thread.run_sync(
                self._upload_file_sync,
                bucket_name,
                object_name,
                file_data,
                content_type,
                metadata,
            )
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            raise

    async def download_file(
        self,
        bucket_name: str,
        object_name: str,
    ) -> BytesIO:
        """
        Download a file from MinIO.

        Args:
            bucket_name: Source bucket
            object_name: Object path/name

        Returns:
            File data as BytesIO

        Evidence: Object retrieval
        Source: https://docs.aws.amazon.com/AmazonS3/latest/userguide/download-objects.html
        """
        try:
            return await to_thread.run_sync(self._download_file_sync, bucket_name, object_name)
        except S3Error as e:
            logger.error(f"Error downloading file: {e}")
            raise

    async def delete_file(
        self,
        bucket_name: str,
        object_name: str,
    ) -> None:
        """
        Delete a file from MinIO.

        Args:
            bucket_name: Target bucket
            object_name: Object path/name
        """
        try:
            await to_thread.run_sync(self._delete_file_sync, bucket_name, object_name)
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            raise

    async def get_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires_seconds: int = 3600,
    ) -> str:
        """
        Get a presigned URL for temporary access to a file.

        Args:
            bucket_name: Source bucket
            object_name: Object path/name
            expires_seconds: URL expiration time

        Returns:
            Presigned URL

        Evidence: Presigned URLs for secure temporary access
        Source: https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html
        """
        try:
            return await to_thread.run_sync(
                self._get_presigned_url_sync,
                bucket_name,
                object_name,
                expires_seconds,
            )
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

    # ------------------------------------------------------------------
    # Blocking helpers (run via anyio.to_thread)
    # ------------------------------------------------------------------

    def _upload_file_sync(
        self,
        bucket_name: str,
        object_name: str,
        file_data: BinaryIO,
        content_type: str,
        metadata: dict | None,
    ) -> str:
        self._ensure_bucket_sync(bucket_name)

        file_data.seek(0, 2)
        file_size = file_data.tell()
        file_data.seek(0)

        self.client.put_object(
            bucket_name,
            object_name,
            file_data,
            file_size,
            content_type=content_type,
            metadata=metadata or {},
        )

        logger.info(f"Uploaded file: {bucket_name}/{object_name}")
        return f"/{bucket_name}/{object_name}"

    def _download_file_sync(self, bucket_name: str, object_name: str) -> BytesIO:
        response = self.client.get_object(bucket_name, object_name)
        data = BytesIO(response.read())
        response.close()
        response.release_conn()

        logger.info(f"Downloaded file: {bucket_name}/{object_name}")
        return data

    def _delete_file_sync(self, bucket_name: str, object_name: str) -> None:
        self.client.remove_object(bucket_name, object_name)
        logger.info(f"Deleted file: {bucket_name}/{object_name}")

    def _get_presigned_url_sync(
        self,
        bucket_name: str,
        object_name: str,
        expires_seconds: int,
    ) -> str:
        return self.client.presigned_get_object(
            bucket_name,
            object_name,
            expires=expires_seconds,
        )


# Global storage instance
storage = StorageService()
