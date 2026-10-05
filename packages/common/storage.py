import logging

import boto3
from botocore.exceptions import ClientError

from packages.config.settings import settings

logger = logging.getLogger(__name__)


class MinioStorageProvider:
    def __init__(self):  # type: ignore[no-untyped-def]
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name="us-east-1",  # Default for MinIO
        )
        self.bucket = settings.S3_BUCKET
        self._ensure_bucket()  # type: ignore[no-untyped-call]

    def _ensure_bucket(self):  # type: ignore[no-untyped-def]
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.s3_client.create_bucket(Bucket=self.bucket)

    def upload_file(self, file_path: str, object_name: str) -> bool:
        try:
            self.s3_client.upload_file(file_path, self.bucket, object_name)
            return True
        except ClientError as e:
            logger.error(f"Failed to upload to storage: {e}")
            return False

    def download_file(self, object_name: str, file_path: str) -> bool:
        try:
            self.s3_client.download_file(self.bucket, object_name, file_path)
            return True
        except ClientError as e:
            logger.error(f"Failed to download from storage: {e}")
            return False

    def delete_file(self, object_name: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=object_name)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete from storage: {e}")
            return False

    def exists(self, object_name: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=object_name)
            return True
        except ClientError:
            return False
