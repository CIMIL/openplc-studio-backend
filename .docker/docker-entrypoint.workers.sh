#! /bin/bash

delay=1
while true; do
  uv run --no-sync dramatiq plc_platform_backend.actors
  if [ $? -eq 3 ]; then
    echo "Connection error encountered on startup. Retrying in $delay second(s)..."
    sleep $delay
    delay=$(delay)
  else
    exit $?
  fi
done