
import os
from airflow.sdk import task
from routines.staging_loading import read_json_from_s3_key, load_to_postgres
import pandas as pd

@task
def task_stg_data_grand_lyon_vehicle_monitoring(object_key: str):
    """
    Flow to load Data Grand Lyon vehicle monitoring data to PostgreSQL staging.
    """
    
    # Read from S3
    json_data = read_json_from_s3_key(object_key, os.getenv("AWS_S3_BUCKET"))

    df = pd.json_normalize(json_data)
    
    # Load to PostgreSQL
    load_to_postgres(schema_name="staging", table_name="stg_vehicle_monitoring", df_data=df)