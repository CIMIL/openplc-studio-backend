#! /bin/bash

API_HOST=0.0.0.0 uv run --no-sync python3 -m debugpy \
  --listen 0.0.0.0:5678 plc_platform_backend/debug.py
