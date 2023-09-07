#!/bin/bash
# A shhell script that does the initial setup for you.

# Step 1: Check if a Python virtual environment named "env" exists
if [ ! -d "env" ]; then
    python3 -m venv --prompt vorta --upgrade-deps env
fi

# Step 2: Activate the environment
source ./env/bin/activate

# Step 3: Install dependencies and development packages
pip install -e .
pip install -r requirements.d/dev.txt
pre-commit install
