from config import get_aws_settings
import logging
import boto3
from uuid import uuid4
import os

logger = logging.getLogger(__name__)


class S3Saver:
    """S3Saver class to save and retrieve the file from S3"""

    def __init__(self):
        self.aws_settings = get_aws_settings()
        self.s3_client = self.__initialise_s3_client__()

    def __initialise_s3_client__(self):
        try:
            s3 = boto3.client(
                "s3",
                region_name=self.aws_settings.aws_region,
                aws_access_key_id=self.aws_settings.aws_access_key_id,
                aws_secret_access_key=self.aws_settings.aws_secret_access_key,
            )
            logger.info("S3 client initialise succcesfully")
            return s3
        except Exception as e:
            logger.error(f"Failed to initialise S3 client, error: {str(e)}")

    def upload_audio_to_s3(self, file_path: str) -> str:
        """Method to upload file in s3

        Args:
            file_path (str): File path

        Returns:
            str: url of the uploaded audio file
        """
        try:
            # Read file from file path
            with open(file_path, "rb") as file:
                file_data = file.read()

            # Extract file extension from file path
            file_extension = file_path.split(".")[-1].lower()

            # Generate a unique file name
            s3_key = f"audio/{uuid4()}.{file_extension}"

            # Determine content type based on file extension
            content_type_map = {
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
                "ogg": "audio/ogg",
                "flac": "audio/flac",
                "m4a": "audio/mp4",
                "aac": "audio/aac",
                "wma": "audio/x-ms-wma",
            }
            content_type = content_type_map.get(file_extension, "audio/mpeg")

            # Create a BytesIO object for upload
            from io import BytesIO

            file_obj = BytesIO(file_data)

            # Upload to S3
            self.s3_client.upload_fileobj(
                file_obj,
                self.aws_settings.aws_s3_bucket_name,
                s3_key,
                ExtraArgs={"ContentType": content_type},
            )

            # Get file URL
            file_url = f"https://{self.aws_settings.aws_s3_bucket_name}.s3.{self.aws_settings.aws_region}.amazonaws.com/{s3_key}"

            return file_url
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to upload audio file to S3 bucket, error: {str(e)}")
            return None
