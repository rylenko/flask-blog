#!/bin/sh

mkdir -p /usr/src/app/logs/
flask translate compile

while true; do
	flask db upgrade && break
	echo "Database upgrade failed, retrying in 5 seconds..."
	sleep 5
done

exec supervisord -n
