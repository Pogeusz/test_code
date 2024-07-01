from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from datetime import timedelta
import requests
import subprocess
import json

# Define the default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG using the @dag decorator
@dag(
    default_args=default_args,
    description='A DAG that traces route and calls an API with a URL provided at runtime',
    schedule_interval=None,  # Only triggered manually
    params={'url': 'http://default-api-url'},  # Default URL parameter
    catchup=False
)
def call_api_with_trace_route():

    @task
    def trace_route(url: str):
        # Extract the hostname from the URL
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if not hostname:
            raise ValueError("Invalid URL")

        # Perform the traceroute
        try:
            process = subprocess.Popen(
                ["traceroute", hostname],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            hops = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
                    hops.append(output.strip())
            rc = process.poll()

            if rc != 0:
                print(f"Traceroute failed. Reached hops before failure:\n{''.join(hops)}")
            else:
                print(f"Traceroute successful. Reached hops:\n{''.join(hops)}")

        except Exception as e:
            print(f"Failed to perform traceroute: {e}")

    @task
    def call_api(url: str):
        if not url:
            raise ValueError("URL parameter is required")

        # Set up headers and payload
        headers = {
            'Content-Type': 'application/json'
        }
        payload = {
            'projectName': 'default_project',
            'feed_name': 'default_feed'
        }

        # Make the POST request
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            print(f"API Response: {response.json()}")
        else:
            print(f"Failed to call API. Status code: {response.status_code}, Response: {response.text}")

    # Get the URL parameter from the DAG run configuration
    url = '{{ dag_run.conf.get("url", params.url) }}'

    # Define the task dependencies
    trace_route(url) >> call_api(url)

# Instantiate the DAG
dag = call_api_with_trace_route()
