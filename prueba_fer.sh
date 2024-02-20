#!/bin/bash

seds="s/username=/PG_USER=/;"\
"s/password=/PG_PASSWORD=/;"\
"s/engine=/PG_ENGINE=/;"\
"s/host=/PG_HOST=/;"\
"s/port=/PG_PORT=/;"\
"s/dbname=/PG_DB=/;"\
"s/dbInstanceIdentifier=/PG_dbInstanceIdentifier=/"
echo "username=postgres\npassword=postgres"| sed $seds > .env_fer