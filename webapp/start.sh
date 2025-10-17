#!/bin/bash

# Start the Review Evaluation Console server

echo "Starting Review Evaluation Console..."
echo ""

# Check if Python is available
if command -v python3 &> /dev/null; then
    echo "Using Python 3"
    python3 server.py
elif command -v python &> /dev/null; then
    echo "Using Python"
    python server.py
else
    echo "Error: Python not found!"
    echo "Please install Python 3 or use: php -S localhost:8000"
    exit 1
fi
