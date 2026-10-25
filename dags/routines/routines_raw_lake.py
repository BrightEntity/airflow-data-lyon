from pendulum import datetime
import json
import os
import requests
from routines.global_routines import datasource_datagrandlyon_api_credentials_base64, generate_work_dir, upload_file_to_object_storage
import boto3
from botocore.config import Config


def upload_json_to_datalake(source_name: str, object_name: str, extraction_date: datetime, json_data: dict) -> str:
    """
    Upload JSON data to the datalake.

    Args:
        source_name (str): The name of the data source.
        object_name (str): The name of the object.
        extraction_date (datetime): The date of extraction.
        json_data (dict): The JSON data to be uploaded.
    """


    s3_client = boto3.client("s3")

    source_name = 'DataGrandLyon'
    object_name = 'VehicleMonitoring'

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

    timestamp = extraction_date.format("YYYYMMDDHHmmss")
    key = f"{source_name}/{object_name}/{timestamp}_{source_name}_{object_name}.json"
    body = json.dumps(json_data, ensure_ascii=False).encode("utf-8")

    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=body,
        ContentType="application/json"
    )

    print(f"Uploaded data to s3://{aws_s3_url}/{bucket_name}/{key}")
    return key


    