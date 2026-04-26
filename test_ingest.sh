#!/bin/bash
# Smoke test for ingest_known_bugs.py
# Set DATABASE_URL and GH_TOKEN env vars before running

if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not set"
    exit 1
fi

/home/deploy/depscope/.venv/bin/python3 scripts/ingest_known_bugs.py
