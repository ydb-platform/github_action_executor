#!/bin/bash
# Скрипт для запуска приложения в фоне с nohup
# Использование: ./start.sh

# Получаем директорию скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "Ошибка: виртуальное окружение не найдено. Создайте его командой: python3 -m venv venv"
    exit 1
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Параметры запуска
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
LOG_FILE="${LOG_FILE:-nohup.out}"

echo "Запуск приложения на $HOST:$PORT..."
echo "Логи будут записываться в файл: $LOG_FILE"
echo "Для остановки используйте: ./stop.sh или pkill -f 'uvicorn app:app'"

# Запускаем с nohup в фоне
nohup uvicorn app:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &

# Сохраняем PID процесса
echo $! > app.pid

echo "Приложение запущено в фоне (PID: $(cat app.pid))"
echo "Проверить статус: tail -f $LOG_FILE"
echo "Остановить: ./stop.sh"
