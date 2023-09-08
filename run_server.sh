#!/bin/bash
source $(poetry env info --path)/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port $PORT
