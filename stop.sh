#!/bin/bash
# Скрипт для остановки приложения
# Использование: ./stop.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/app.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Остановка приложения (PID: $PID)..."
        kill "$PID"
        rm "$PID_FILE"
        echo "Приложение остановлено"
    else
        echo "Процесс с PID $PID не найден"
        rm "$PID_FILE"
    fi
else
    echo "Файл PID не найден. Попытка найти процесс вручную..."
    pkill -f 'uvicorn app:app'
    if [ $? -eq 0 ]; then
        echo "Процесс остановлен"
    else
        echo "Процесс не найден"
    fi
fi
