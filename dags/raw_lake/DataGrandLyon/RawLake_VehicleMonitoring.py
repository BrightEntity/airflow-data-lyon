import os

import requests
from airflow.sdk import Asset, dag, task
from pendulum import datetime
from routines.global_routines import get_base64_credentials


from dags.routines.routines_raw_lake import upload_json_to_datalake

def get_rawfile_data_grand_lyon_vehicle_monitoring(p_credentials_base64: str):
    """
    Flow to retrieve vehicle monitoring data from the Data Grand Lyon API.
    """
    url = "https://data.grandlyon.com/siri-lite/2.0/vehicle-monitoring.json"

    with requests.get(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {p_credentials_base64}",
        },
    ) as response:
        if response.status_code == 200:
            data = response.json()
        else:
            raise ValueError(f"Error: {response.status_code} - {response.text}")
            data = None
    return data

@task(
    # Define an asset outlet for the task. This can be used to schedule downstream Dags when this task has run.
    outlets=[Asset("flow_data_grand_lyon_vehicle_monitoring")]
)  # Define that this task updates the `current_astronauts` Asset
def task_raw_lake_data_grand_lyon_vehicle_monitoring(extraction_date: datetime) -> str:
    """
    Main flow to retrieve and upload vehicle monitoring data from the Data Grand Lyon API.
    """
    datasource_datagrandlyon_api_credentials_base64 = get_base64_credentials(
        os.getenv("DATASOURCE_DATA_GRAND_LYON_USERNAME"),
        os.getenv("DATASOURCE_DATA_GRAND_LYON_PASSWORD")
    )

    # Retrieve data from API
    json_data = get_rawfile_data_grand_lyon_vehicle_monitoring(datasource_datagrandlyon_api_credentials_base64)

    # Upload data to datalake
    return upload_json_to_datalake("DataGrandLyon", "VehicleMonitoring", extraction_date, json_data)
