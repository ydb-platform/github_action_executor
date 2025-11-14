"""
Configuration file for GitHub Action Executor
"""
import os
from typing import List

# Автоматическое открытие ссылки на запуск workflow
# По умолчанию: True (включено)
AUTO_OPEN_RUN = os.getenv("AUTO_OPEN_RUN", "true").lower() == "true"

# Regex паттерны для фильтрации веток
# Используются для автоматической фильтрации веток при загрузке
# Если пусто, показываются все ветки
# 
# Примеры паттернов:
#   "^main$" - точное совпадение с "main"
#   "^stable-.*" - все ветки начинающиеся с "stable-"
#   "^stream-.*" - все ветки начинающиеся с "stream-"
#   ["production", "staging"] - только ветки содержащие "production" или "staging"
#   [".*-prod$"] - ветки заканчивающиеся на "-prod"
#
# Текущая настройка: main, stable-*, stream-*
BRANCH_FILTER_PATTERNS: List[str] = [
    "^main$",      # Точное совпадение с main
    "^stable-.*",  # Все ветки начинающиеся с stable-
    "^stream-.*"   # Все ветки начинающиеся с stream-
]

# Можно переопределить через переменную окружения (через запятую)
# Пример: BRANCH_FILTER_PATTERNS=^main$,^stable-.*,^stream-.*
env_patterns = os.getenv("BRANCH_FILTER_PATTERNS", "")
if env_patterns:
    BRANCH_FILTER_PATTERNS = [p.strip() for p in env_patterns.split(",") if p.strip()]

# Проверка прав пользователя перед запуском workflow
# Если True, проверяется является ли пользователь коллаборатором (имеет доступ к репозиторию)
# Если False, любой авторизованный пользователь может запускать workflows
# По умолчанию: True (проверка включена)
CHECK_PERMISSIONS = os.getenv("CHECK_PERMISSIONS", "true").lower() == "true"

# Выполнение workflow от имени авторизованного пользователя
# По умолчанию: True (workflow выполняются от имени пользователя)
# Если False, workflow выполняются от имени GitHub App
USE_USER_TOKEN_FOR_WORKFLOWS = os.getenv("USE_USER_TOKEN_FOR_WORKFLOWS", "true").lower() == "true"

