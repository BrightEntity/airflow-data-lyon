from airflow.sdk import Asset, dag, task
from dags.standardized_tables.DataGrandLyon.std_data_grand_lyon_vehicle_monitoring import std_data_grand_lyon_vehicle_monitoring
from pendulum import datetime, now
from dags.raw_lake.DataGrandLyon.RawLake_VehicleMonitoring import task_raw_lake_data_grand_lyon_vehicle_monitoring
from dags.staging.DataGrandLyon.stg_vehicle_monitoring import task_stg_data_grand_lyon_vehicle_monitoring
from pathlib import Path
from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig

@dag(
    start_date=datetime(2025, 4, 22, tz="UTC"),
    schedule="* * * * *",
    doc_md=__doc__,
    default_args={"owner": "Aymeric", "retries": 3},
    tags=["DataGrandLyon", "VehicleMonitoring"],
)  
def dag_datagrandlyon_vehicle_monitoring():
    """
    Dag to retrieve and upload vehicle monitoring data from the Data Grand Lyon API.
    """

    extraction_date = now()

    task_raw = task_raw_lake_data_grand_lyon_vehicle_monitoring(extraction_date=extraction_date)

    task_stg = task_stg_data_grand_lyon_vehicle_monitoring(object_key=task_raw)

    task_std = std_data_grand_lyon_vehicle_monitoring()


    task_raw >> task_stg >> task_std

@dag(
    start_date=datetime(2025, 4, 22, tz="UTC"),
    schedule="0,10,20,30,40,50 * * * *",
    doc_md=__doc__,
    default_args={"owner": "Aymeric", "retries": 3},
    tags=["CoreTables", "dbt"],
)
def dag_core_refresh():
    """ 
    Dag to refresh the core models in the Data Grand Lyon dbt project.
    """

    dbt_transform = DbtTaskGroup(
        group_id="dbt_transform",
        project_config=ProjectConfig(
            dbt_project_path=Path(__file__).resolve().parents[1] / "include" / "dbt"
        ),
        profile_config=ProfileConfig(
            profile_name="data_lyon",
            target_name="prd",
            profiles_yml_filepath=Path(__file__).resolve().parents[1] / "include" / "dbt" / "profiles.yml",
        ),
        operator_args={"install_deps": True},
    )


dag_datagrandlyon_vehicle_monitoring()
dag_core_refresh()