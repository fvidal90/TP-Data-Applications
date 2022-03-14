"""Stocks dag."""
from datetime import datetime
import os

from airflow.models import DAG
from airflow.operators.python import PythonOperator
import boto3
import pandas as pd
import sqlalchemy

from packages.postgres_cli import PostgresClient
from packages.utils import extract_year, get_anomalous_days_airport, plot_chart_airport


PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_HOST = os.getenv("PG_HOST")
PG_PORT = int(os.getenv("PG_PORT"))
PG_DB = os.getenv("PG_DB")


def _get_delay_average_and_count(ds, bucket='flights-fer'):
    pg = PostgresClient(PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DB)
    year = extract_year(ds)
    s3_client = boto3.client("s3")
    response = s3_client.get_object(Bucket=bucket, Key=f"raw/{year}.csv")
    df = pd.read_csv(response.get("Body"), usecols=['FL_DATE', 'ORIGIN', 'DEP_DELAY'])
    df = df[~df.DEP_DELAY.isna()]
    df_metrics = df.groupby(['FL_DATE', 'ORIGIN']).agg({'DEP_DELAY': ['mean', 'count']}).reset_index()
    df_metrics.columns = ['fl_date', 'origin', 'dep_delay_mean', 'dep_delay_count']
    try:
        pg.insert_from_frame(df_metrics, 'delay_metrics')
    except sqlalchemy.exc.IntegrityError:
        print("Data already exists! Nothing to do...")


def _get_anomalous_days(ds):
    pg = PostgresClient(PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DB)
    year = extract_year(ds)
    df_delay = pg.to_frame(f"select * from delay_metrics where date_part('year', fl_date) = {year}")
    df_delay["fl_date"] = pd.to_datetime(df_delay.fl_date)
    df_anomalies = pd.DataFrame()
    for airport in sorted(set(df_delay.origin.values)):
        df_airport = get_anomalous_days_airport(df_delay, airport)
        df_anomalies = pd.concat([df_anomalies, df_airport])
    try:
        pg = PostgresClient(PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DB)
        pg.insert_from_frame(df_anomalies[['fl_date', 'origin', 'anomaly']], 'delay_anomalies')
    except sqlalchemy.exc.IntegrityError:
        print("Data already exists! Nothing to do...")


def _plot_anomalous_days(ds):
    year = extract_year(ds)
    pg = PostgresClient(PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DB)
    df_complete = pg.to_frame(f"""
    select dm.*, da.anomaly
    from 
        (select * from delay_metrics where date_part('year', fl_date) = {year}) dm
        join (select * from delay_anomalies where date_part('year', fl_date) = {year}) da
        on dm.fl_date=da.fl_date and dm.origin=da.origin
    """)
    df_complete["fl_date"] = pd.to_datetime(df_complete.fl_date)
    for airport in sorted(set(df_complete.origin.values)):
        plot_chart_airport(df_complete, airport, year)


default_args = {
    "owner": "Fernando",
    "retries": 0,
    "start_date": datetime(2009, 1, 1),
    "end_date": datetime(2010, 1, 1),
}
with DAG(
    "tp_rds_solution",
    default_args=default_args,
    schedule_interval="0 0 1 1 *",
) as dag:

    get_delay_task = PythonOperator(
        task_id=f"get_delay_task",
        python_callable=_get_delay_average_and_count,
        op_kwargs={
            "ds": "{{ ds }}",
        },
    )

    get_anomalies_task = PythonOperator(
        task_id=f"get_anomalies_task",
        python_callable=_get_anomalous_days,
        op_kwargs={
            "ds": "{{ ds }}",
        },
    )

    plot_anomalies_task = PythonOperator(
        task_id=f"plot_anomalies_task",
        python_callable=_plot_anomalous_days,
        op_kwargs={
            "ds": "{{ ds }}",
        },
    )

    get_delay_task.set_downstream(get_anomalies_task)
    get_anomalies_task.set_downstream(plot_anomalies_task)
