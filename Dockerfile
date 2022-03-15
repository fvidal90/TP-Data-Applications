FROM apache/airflow:2.2.3
RUN pip install apache-airflow-providers-amazon==3.0.0
RUN pip install boto3==1.20.24
RUN pip install matplotlib==3.5.1
RUN pip install s3fs==2022.2.0
RUN pip install scikit-learn==1.0.2
