#!/usr/bin/env bash
# Wait for migrations to finish.
sleep 20

exec uwsgi --socket :9090 \
    --wsgi-file stroykerbox/wsgi.py \
    --master --processes 2 \
    --enable-threads --threads 1 \
    --buffer-size=65535 --stats /tmp/stats.socket \
    --attach-daemon 'python manage.py rqworker high default' \
    --attach-daemon 'python manage.py catalog_sync_scheduler'
