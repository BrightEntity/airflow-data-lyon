from airflow.sdk import task
from sqlalchemy import text

from dags.routines.staging_loading import get_pgsql_connection

@task
def std_data_grand_lyon_vehicle_monitoring():
    """
    Standardizes the raw data from the Data Grand Lyon Vehicle Monitoring API.
    Call the procedure standardized.sp_load_std_datagrandlyon_vehicle_monitoring() in the PostgreSQL database to perform the standardization.
    """
    try:
        conn = get_pgsql_connection()
        with conn.begin() as connection:
            connection.execute(text("CALL standardized.sp_load_std_datagrandlyon_vehicle_monitoring();"))
            print("Standardization procedure executed successfully.")
    except Exception as e:
        print(f"Error executing standardization procedure: {e}")
        raise