#!/bin/bash
# Start API server script

echo "Starting Demand Forecasting API Server..."
echo "API will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")/.."
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

