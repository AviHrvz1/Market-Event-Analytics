#!/bin/bash
# Run Flask server and capture output to a log file

LOG_FILE="server_output_$(date +%Y%m%d_%H%M%S).log"

echo "Starting server with logging..."
echo "Log file: $LOG_FILE"
echo "Press Ctrl+C to stop the server"
echo ""

# Run the server and capture both stdout and stderr
python3 app.py 2>&1 | tee "$LOG_FILE"
