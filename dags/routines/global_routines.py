from pathlib import Path
import boto3
from botocore.config import Config
from dotenv import load_dotenv
import os
from datetime import datetime, UTC
from pathlib import Path
import base64

def get_s3_client():
    """
    Create and return an S3 client using boto3.

    Returns:
        boto3.client: An S3 client instance.

    """
    s3_client = boto3.client("s3")

    bucket_name = os.getenv("AWS_S3_BUCKET")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_s3_url = os.getenv("AWS_S3_URL")

    if not bucket_name or not aws_access_key_id or not aws_secret_access_key or not aws_s3_url:
        raise ValueError("AWS_S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and AWS_S3_URL environment variables must be set")

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=f"{aws_s3_url}",
        config=Config(s3={'addressing_style': 'path'})
    )
    return s3_client

def get_base64_credentials(username: str, password: str) -> str:
    """
    Generate a base64-encoded string for HTTP Basic Authentication.

    Args:
        username (str): The username for authentication.
        password (str): The password for authentication.

    Returns:
        str: A base64-encoded string in the format "username:password".
    """

    credentials = f"{username}:{password}"
    credentials_bytes = credentials.encode("utf-8")
    base64_bytes = base64.b64encode(credentials_bytes)
    base64_credentials = base64_bytes.decode("utf-8")

    return base64_credentials

def generate_work_dir(datasource_name: str, object_name: str) -> Path:
    """
    Generate a work directory path based on the datasource name and object name.
    The directory will be created if it doesn't exist.

    Args:
        datasource_name (str): The name of the datasource.
        object_name (str): The name of the object.

    Returns:
        Path: The path to the generated work directory.
    """

    param_datasource_name = datasource_name
    param_object_name = object_name
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")

    work_dir = Path('.') / "work" / param_datasource_name / param_object_name / ts
    work_dir.mkdir(parents=True, exist_ok=True)

    return work_dir

def upload_file_to_object_storage(file_path: Path, object_storage_url: str, username: str, password: str) -> None:
    """
    Upload a file to an object storage service.

    Args:
        file_path (Path): The path to the file to be uploaded.
        object_storage_url (str): The URL of the object storage service.
        username (str): The username for authentication.
        password (str): The password for authentication.
    """
    import requests

    with open(file_path, 'rb') as f:
        response = requests.put(object_storage_url, data=f, auth=(username, password))
        response.raise_for_status()  # Raise an error for bad responses

def delete_work_dir(work_dir: Path) -> None:
    """
    Delete the specified work directory and its contents.

    Args:
        work_dir (Path): The path to the work directory to be deleted.
    """
    if work_dir.exists() and work_dir.is_dir():
        for item in work_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                delete_work_dir(item)  # Recursively delete subdirectories
        work_dir.rmdir()

env_path = Path('.') / '.env'
load_dotenv(env_path)

datasource_datagrandlyon_api_username = os.getenv("DATASOURCE_DATA_GRAND_LYON_USERNAME")
datasource_datagrandlyon_api_pwd = os.getenv("DATASOURCE_DATA_GRAND_LYON_PASSWORD")

if not datasource_datagrandlyon_api_username or not datasource_datagrandlyon_api_pwd:
    raise ValueError(
        "DATASOURCE_DATA_GRAND_LYON_USERNAME and "
        "DATASOURCE_DATA_GRAND_LYON_PASSWORD environment variables must be set"
    )

datasource_datagrandlyon_api_credentials_base64 = get_base64_credentials(datasource_datagrandlyon_api_username, datasource_datagrandlyon_api_pwd)