#!/bin/sh
#
# Author: KIM BYOUNGGON(architect@data-dynamics.io)
# Description: Python 애플리케이션을 백그라운드에서 실행하고 PID를 저장하는 스크립트
# Usage: sh status.sh
#

PID_FILE="app.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Application is not running (no PID file found)."
    exit 1
fi

PID=$(cat "$PID_FILE")

if ps -p $PID > /dev/null; then
    echo "Application is running with PID $PID."
    exit 0
else
    echo "Application is not running (stale PID file found)."
    exit 1
fi
