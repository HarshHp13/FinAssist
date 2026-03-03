#!/bin/bash

# Start the cron service
printenv | grep -v "no_proxy" >> /etc/environment
service cron start

# Start the API
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
