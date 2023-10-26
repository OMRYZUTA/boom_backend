#!/bin/bash
cd boom_frontend
npm run build
cp -R dist/* ../static/
cd ..
source $(poetry env info --path)/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port $PORT
