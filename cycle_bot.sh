#!/bin/bash
PYTHON_FILE="bot.py"
PYTHON_BIN="./.venv/bin/python"

trap 'echo "Остановка..."; exit 0' INT TERM

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Запуск $PYTHON_FILE..."
    $PYTHON_BIN "$PYTHON_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Процесс завершён с кодом $EXIT_CODE. П>
    sleep 5
done