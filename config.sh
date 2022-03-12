#!/bin/bash

sudo su

cd /home/ec2-user

yum update -y

yum install docker -y
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-Linux-x86_64" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

yum install jq -y
aws ssm get-parameter --name /aws/reference/secretsmanager/github_credentials --query 'Parameter.Value'  --with-decryption --output text --region us-east-1 | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' > .env_github
export $(xargs <.env_github)
rm .env_github

yum install git -y
git config --global user.name "$GITHUB_USER"
git config --global user.email "$GITHUB_EMAIL"
git clone "https://$GITHUB_TOKEN@github.com/$GITHUB_USER/TP-Data-Applications.git"

cd TP-Data-Applications
git checkout $GITHUB_BRANCH

aws ssm get-parameter --name /aws/reference/secretsmanager/pg_credentials --query 'Parameter.Value'  --with-decryption --output text --region us-east-1 | jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' | sed "s/username=/PG_USER=/;s/password=/PG_PASSWORD=/;s/engine=/PG_ENGINE=/;s/host=/PG_HOST=/;s/port=/PG_PORT=/;s/dbname=/PG_DB=/;s/dbInstanceIdentifier=/PG_dbInstanceIdentifier=/" > .env_pg
export $(xargs <.env_pg)
rm .env_pg

echo -e """AIRFLOW_UID=1000
AIRFLOW_GID=0
PG_PORT=$PG_PORT
PG_USER=$PG_USER
PG_PASSWORD=$PG_PASSWORD
PG_HOST=$PG_HOST
PG_DB=$PG_DB""" > .env
export $(xargs <.env)

pip3 install sqlalchemy==1.4.31
pip3 install psycopg2-binary==2.9.3
python3 create_tables.py

service docker start
docker-compose up airflow-init
docker-compose up -d