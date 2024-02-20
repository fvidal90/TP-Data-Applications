import boto3
import pandas as pd


def read_from_s3(bucket="flights-fer", key="tp/2009.csv"):
    s3_client = boto3.client("s3")
    response = s3_client.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(response.get("Body"))
    return df


def read_from_csv(directory="raw_files", year=2018):
    df = pd.read_csv(f"{directory}/{year}.csv")
    return df
