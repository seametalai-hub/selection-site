#!/bin/bash
cd "$(dirname "$0")"
python3 -m http.server 8123 &
SERVER_PID=$!
sleep 2
open "http://127.0.0.1:8123/index.html"
wait $SERVER_PID
