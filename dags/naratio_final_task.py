from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import random
import pandas as pd
import requests
from sqlalchemy import create_engine
from urllib.parse import quote_plus

# Define default_args dictionary to specify DAG configuration options
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2020, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create a DAG instance with the ID 'tutorial'
dag = DAG(
    'finalTask',
    default_args=default_args,
    schedule_interval=timedelta(hours=1),
    catchup=False,  # Don't backfill or "catch up" on execution
)

# Define three tasks: task1, task2, and task3
def extrac():
    print('process extract')
    # URL API
    url = "https://api.coindesk.com/v1/bpi/currentprice.json"

    # Request from APO\I
    response = requests.get(url)
    data = response.json()

    # Create dataframe from JSON response
    df = pd.DataFrame(data)

    # Create a flat dictionary for 'bpi' data
    flat_bpi = {}
    for currency, currency_data in data['bpi'].items():
        for key, value in currency_data.items():
            flat_bpi[f'bpi_{currency.lower()}_{key}'] = value


    # Add 'time' and 'disclaimer' data
    #flat_bpi.update(data['time'])
    flat_bpi['time_updated'] = data['time']['updated']
    flat_bpi['time_updated_iso'] = data['time']['updatedISO']
    flat_bpi['disclaimer'] = data['disclaimer']
    flat_bpi['chart_name'] = data['chartName']

    # Convert the flat dictionary to a DataFrame
    df = pd.DataFrame([flat_bpi])

    # Filter kolom yang diinginkan
    columns_to_keep = [
        'disclaimer', 'chart_name', 'time_updated', 'time_updated_iso',
        'bpi_usd_code', 'bpi_usd_rate_float', 'bpi_usd_description',
        'bpi_gbp_code', 'bpi_gbp_rate_float', 'bpi_gbp_description',
        'bpi_eur_code', 'bpi_eur_rate_float', 'bpi_eur_description'
    ]
    df = df[columns_to_keep]
    # Assuming the current exchange rate for USD to IDR is 15000 (for example)
    exchange_rate_usd_to_idr = 15000
    df['bpi_idr_rate_float'] = df['bpi_usd_rate_float'] * exchange_rate_usd_to_idr

    # Add last updated date
    from datetime import datetime
    df['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Define the username and password with special characters
    username = 'local_airflow'
    password = 'local_airflow'
    db_name = 'staging_area'
    db_port = '5433'

    # Encode the password to handle special characters
    encoded_password = quote_plus(password)

    # Define the database connection URL with encoded username and password
    # db_url = f'postgresql://{username}:{encoded_password}@localhost:{db_port}/{db_name}'
    db_url = f'postgresql+psycopg2://{username}:{password}@host.docker.internal:{db_port}/{db_name}'


    # Create a SQLAlchemy engine
    engine = create_engine(db_url)

    # Load the DataFrame into the database table
    df.to_sql('coinbase_data', engine, if_exists='append', index=False)

task1 = PythonOperator(
    task_id='task1',
    python_callable=extrac,
    dag=dag,
)

def read_and_load():
    print("Hello from Python!")
    

task2 = PythonOperator(
    task_id='task2',
    python_callable=read_and_load,
    dag=dag,
)


# Define the task dependencies
task1 >> task2
