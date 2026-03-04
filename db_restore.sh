#! /bin/env bash


DOCKER_DB_NAME="$(docker compose ps -qa --status=running pg)"

DB_USER=stroykerbox
DB_NAME=stroykerbox

if [ -z ${DOCKER_DB_NAME} ]; then
    echo "No running postgres docker container was found. Run `docker-compose up` first."
    exit 1
fi

docker exec -i "${DOCKER_DB_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" < "$@"
