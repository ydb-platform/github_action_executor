# GitHub Action Executor

Веб-интерфейс для запуска GitHub Actions workflows с проверкой прав контрибьютора и возможностью выбора тестов.

## Возможности

- ✅ Авторизация через GitHub OAuth
- ✅ Проверка прав контрибьютора перед запуском workflow
- ✅ Веб-форма для выбора тестов
- ✅ Запуск workflow через GitHub App (без использования PAT)
- ✅ Готово для развертывания в Yandex Cloud

## Требования

- Python 3.11+
- GitHub OAuth App
- GitHub App с установкой в репозиторий

## Установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone <repository-url>
   cd github_action_executor
   ```

2. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Настройте переменные окружения:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env файл
   ```

## Настройка GitHub

### 1. Создание OAuth App

1. Перейдите в [GitHub Settings > Developer settings > OAuth Apps](https://github.com/settings/developers)
2. Нажмите "New OAuth App"
3. Заполните:
   - **Application name**: GitHub Action Executor
   - **Homepage URL**: `http://localhost:8000` (для разработки)
   - **Authorization callback URL**: `http://localhost:8000/auth/github/callback`
4. Сохраните **Client ID** и **Client Secret**

### 2. Создание GitHub App

1. Перейдите в [GitHub Settings > Developer settings > GitHub Apps](https://github.com/settings/apps)
2. Нажмите "New GitHub App"
3. Заполните:
   - **GitHub App name**: GitHub Action Executor
   - **Homepage URL**: `http://localhost:8000`
   - **Webhook URL**: (можно оставить пустым)
   - **Permissions**:
     - **Actions**: Read and write
     - **Contents**: Read-only (или Read and write если нужно)
     - **Metadata**: Read-only
4. Сохраните **App ID**
5. Сгенерируйте **Private key** и скачайте файл `.pem`
6. Установите приложение в репозиторий или организацию
7. Найдите **Installation ID** в URL установки (8-значное число)

### 3. Настройка Workflow

Ваш workflow должен поддерживать `workflow_dispatch` с inputs:

```yaml
name: CI Tests

on:
  workflow_dispatch:
    inputs:
      tests:
        description: 'Tests to run'
        required: false
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          echo "Running tests: ${{ inputs.tests }}"
          # Ваши команды для запуска тестов
```

## Запуск локально

```bash
# Простой запуск
python app.py

# Или с uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Приложение будет доступно по адресу: http://localhost:8000

## Использование Docker

```bash
# Соберите образ
docker build -t github-action-executor .

# Запустите контейнер
docker run -p 8000:8000 --env-file .env \
  -v $(pwd)/github-app-private-key.pem:/app/github-app-private-key.pem:ro \
  github-action-executor
```

Или используйте docker-compose:

```bash
docker-compose up -d
```

## Развертывание в Yandex Cloud

Подробные инструкции по развертыванию в Yandex Cloud см. в файле [yandex-cloud-deploy.md](yandex-cloud-deploy.md)

### Быстрый старт с Cloud Run:

1. Соберите Docker образ
2. Загрузите в Yandex Container Registry
3. Создайте Cloud Run сервис
4. Настройте переменные окружения
5. Создайте API Gateway для публичного доступа

## Использование

### Через веб-интерфейс

1. Откройте веб-интерфейс
2. Авторизуйтесь через GitHub (один раз)
3. Укажите репозиторий и workflow
4. Выберите тесты для запуска
5. Нажмите "Запустить Workflow"
6. Откроется страница с результатом запуска

### Прямая ссылка (без UI)

Вы можете создать прямую ссылку для запуска workflow:

```
http://your-server/workflow/trigger?owner=owner_name&repo=my-repo&workflow_id=ci.yml&ref=main&tests=unit,integration
```

При клике по ссылке:
1. Если не авторизован → редирект на GitHub OAuth
2. После авторизации → сразу запускается workflow
3. Показывается страница с результатом

### Через curl (с OAuth сессией)

1. Авторизуйтесь один раз в браузере
2. Скопируйте cookie сессии из браузера
3. Используйте в curl:

```bash
# HTML результат
curl "http://your-server/workflow/trigger?owner=owner_name&repo=my-repo&workflow_id=ci.yml&ref=main&tests=unit,integration" \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# JSON результат
curl "http://your-server/workflow/trigger?owner=owner_name&repo=my-repo&workflow_id=ci.yml" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -H "Accept: application/json"
```

## API Endpoints

### Web Interface
- `GET /` - Главная страница
- `GET /workflow/form` - Форма выбора тестов
- `GET /workflow/trigger` - Универсальный endpoint для запуска workflow (через URL)
- `POST /workflow/trigger` - Запуск workflow из формы

### Authentication
- `GET /auth/github` - Начать OAuth авторизацию
- `GET /auth/github/callback` - OAuth callback
- `GET /auth/logout` - Выход
- `GET /auth/user` - Информация о текущем пользователе

### API
- `POST /api/trigger` - Программный запуск workflow (JSON)

### Health Check
- `GET /health` - Проверка работоспособности

## Пример использования API

```bash
# Сначала авторизуйтесь через веб-интерфейс, затем используйте сессию

curl -X POST http://localhost:8000/api/trigger \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your-session-cookie>" \
  -d '{
    "owner": "username",
    "repo": "repo-name",
    "workflow_id": "ci.yml",
    "ref": "main",
    "tests": ["unit", "integration"]
  }'
```

## Безопасность

- ✅ Используется GitHub App вместо PAT
- ✅ Проверка прав контрибьютора перед запуском
- ✅ OAuth для аутентификации пользователей
- ✅ Session-based аутентификация
- ⚠️ **Важно**: Храните приватный ключ GitHub App в безопасном месте (Yandex Lockbox, Secrets Manager)

## Структура проекта

```
github_action_executor/
├── app.py                 # Главный файл приложения
├── backend/
│   ├── routes/           # API маршруты
│   │   ├── auth.py       # OAuth авторизация
│   │   ├── workflow.py   # Запуск workflow
│   │   └── api.py        # REST API
│   └── services/         # Бизнес-логика
│       ├── github_app.py      # GitHub App токены
│       ├── github_oauth.py    # OAuth
│       ├── permissions.py    # Проверка прав
│       └── workflow.py        # Запуск workflow
├── frontend/
│   ├── templates/        # HTML шаблоны
│   └── static/           # CSS, JS
├── requirements.txt      # Python зависимости
├── Dockerfile           # Docker образ
├── docker-compose.yml   # Docker Compose
└── README.md           # Документация
```

## Лицензия

MIT

## Поддержка

Если у вас возникли вопросы или проблемы, создайте issue в репозитории.

