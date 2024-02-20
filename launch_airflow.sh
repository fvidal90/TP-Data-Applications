export $(xargs <.env)
sudo service docker start
sudo docker-compose up airflow-init
sudo docker-compose up -d