from pendulum import datetime
import json
import os
import boto3
import pandas as pd
import sqlalchemy
from routines.global_routines import get_s3_client
from pandas import DataFrame

def read_json_from_s3(source_name: str, object_name: str, extraction_date: datetime, bucket_name: str):
    """
    Read JSON file from S3.

    Args:
        source_name (str): The name of the source
        object_name (str): The name of the S3 object prefix
        extraction_date (datetime): The extraction date
        bucket_name (str): The S3 bucket name

    Returns:
        dict: The parsed JSON data
    """
    # Format the timestamp and key for S3 read
    timestamp = extraction_date.format("YYYYMMDDHHmmss")
    object_key = f"{source_name}/{object_name}/{timestamp}_{source_name}_{object_name}.json"
    return read_json_from_s3_key(object_key, bucket_name)

def read_json_from_s3_key(object_key: str, bucket_name: str):
    """Read a JSON object from S3 using its exact key."""
    print(object_key)
    s3_client = get_s3_client()

    response = s3_client.get_object(
        Bucket=bucket_name,
        Key=object_key
    )

    json_data = json.loads(response['Body'].read().decode('utf-8'))
    
    return json_data

def get_pgsql_connection():
    """
    Establish a connection to the PostgreSQL database.

    Returns:
        psycopg2.extensions.connection: A connection object to the PostgreSQL database.
    """
    try:
    # Get database connection parameters from environment
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "data_lyon_staging")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        
        conn_string = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_password}"

        # Connect to PostgreSQL
        conn = sqlalchemy.create_engine(f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')

        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        raise

def load_to_postgres(schema_name: str, table_name: str, df_data: DataFrame):
    """
    Load data into PostgreSQL staging.

    Args:
        schema_name (str): The name of the schema
        table_name (str): The name of the staging table
        df_data (DataFrame): The DataFrame containing the data to load
    """

    conn = get_pgsql_connection()

    df_data = df_data.apply(
        lambda column: column.map(
            lambda value: json.dumps(value, ensure_ascii=False)
            if isinstance(value, (dict, list))
            else value
        )
    )

    # Overwrite the staging table with new data
    df_data.to_sql(
        table_name,
        conn,
        schema=schema_name,
        if_exists='replace',
        index=False,
    )

    print(f"Loaded {len(df_data)} rows to staging PostgreSQL")

def flow_load_grand_lyon_to_postgres(extraction_date: datetime):
    """
    Flow to load Data Grand Lyon vehicle monitoring data to PostgreSQL staging.
    """
    
    # Read from S3
    json_data = read_json_from_s3(
        object_name="VehicleMonitoring",
        extraction_date=extraction_date,
        bucket_name=os.getenv("AWS_S3_BUCKET")
    )

    df = pd.json_normalize(json_data)
    
    # Load to PostgreSQL
    load_to_postgres(schema_name="staging", table_name="stg_vehicle_monitoring", df_data=df)