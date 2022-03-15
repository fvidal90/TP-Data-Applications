FROM apache/airflow:2.2.3

COPY airflow_extra_requirements.txt /code/requirements.txt
WORKDIR /code
RUN pip install -r airflow_extra_requirements.txt
