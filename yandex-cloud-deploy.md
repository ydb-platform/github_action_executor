# Развертывание в Yandex Cloud

Этот проект можно развернуть в Yandex Cloud несколькими способами:

## Вариант 1: Yandex Cloud Run (Рекомендуется)

Cloud Run - это сервис для запуска контейнеризированных приложений.

### Шаги развертывания:

1. **Установите Yandex Cloud CLI:**
   ```bash
   curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
   yc init
   ```

2. **Создайте Container Registry:**
   ```bash
   yc container registry create --name github-action-executor
   ```

3. **Соберите Docker образ:**
   ```bash
   docker build -t cr.yandex/<registry-id>/github-action-executor:latest .
   ```

4. **Загрузите образ в registry:**
   ```bash
   docker push cr.yandex/<registry-id>/github-action-executor:latest
   ```

5. **Создайте сервис Cloud Run:**
   ```bash
   yc serverless container create --name github-action-executor
   ```

6. **Создайте ревизию с переменными окружения:**
   ```bash
   yc serverless container revision deploy \
     --container-name github-action-executor \
     --image cr.yandex/<registry-id>/github-action-executor:latest \
     --service-account-id <service-account-id> \
     --environment SECRET_KEY=<your-secret-key> \
     --environment GITHUB_CLIENT_ID=<your-client-id> \
     --environment GITHUB_CLIENT_SECRET=<your-client-secret> \
     --environment GITHUB_CALLBACK_URL=https://<your-domain>/auth/github/callback \
     --environment GITHUB_APP_ID=<your-app-id> \
     --environment GITHUB_APP_INSTALLATION_ID=<your-installation-id> \
     --environment GITHUB_APP_PRIVATE_KEY_PATH=/app/github-app-private-key.pem \
     --environment DEFAULT_REPO_OWNER=<owner> \
     --environment DEFAULT_REPO_NAME=<repo> \
     --environment DEFAULT_WORKFLOW_ID=<workflow-id> \
     --memory 512MB \
     --cores 1 \
     --execution-timeout 30s \
     --concurrency 10 \
     --min-instances 0 \
     --max-instances 5
   ```

7. **Создайте API Gateway для публичного доступа:**
   ```bash
   yc serverless api-gateway create \
     --name github-action-executor-gateway \
     --spec api-gateway-spec.yaml
   ```

## Вариант 2: Yandex Compute Cloud (VM)

Если нужен полный контроль, можно развернуть на виртуальной машине.

1. **Создайте VM:**
   ```bash
   yc compute instance create \
     --name github-action-executor \
     --zone ru-central1-a \
     --network-interface subnet-name=default,nat-ip-version=ipv4 \
     --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2204-lts,size=20 \
     --ssh-key ~/.ssh/id_rsa.pub
   ```

2. **Подключитесь к VM и установите зависимости:**
   ```bash
   ssh ubuntu@<vm-ip>
   sudo apt update
   sudo apt install -y python3-pip docker.io docker-compose
   ```

3. **Клонируйте проект и запустите:**
   ```bash
   git clone <your-repo>
   cd github_action_executor
   docker-compose up -d
   ```

## Переменные окружения

Все переменные окружения должны быть установлены в Yandex Cloud:

- `SECRET_KEY` - секретный ключ для сессий
- `GITHUB_CLIENT_ID` - OAuth Client ID
- `GITHUB_CLIENT_SECRET` - OAuth Client Secret
- `GITHUB_CALLBACK_URL` - URL для OAuth callback
- `GITHUB_APP_ID` - GitHub App ID
- `GITHUB_APP_INSTALLATION_ID` - Installation ID
- `GITHUB_APP_PRIVATE_KEY_PATH` - путь к приватному ключу (или используйте Secret Manager)
- `DEFAULT_REPO_OWNER` - владелец репозитория по умолчанию
- `DEFAULT_REPO_NAME` - название репозитория по умолчанию
- `DEFAULT_WORKFLOW_ID` - ID workflow по умолчанию

## Использование Yandex Lockbox (Secret Manager)

Для безопасного хранения секретов используйте Yandex Lockbox:

```bash
# Создайте секрет
yc lockbox secret create --name github-app-private-key --payload file=github-app-private-key.pem

# Получите секрет в приложении через API Lockbox
```

## Мониторинг

Настройте мониторинг через Yandex Monitoring:
- Метрики запросов
- Логи приложения
- Алерты на ошибки

