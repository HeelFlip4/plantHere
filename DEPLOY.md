# 🚀 Guia de Deploy - GreenPulse

Este guia explica como fazer o deploy da aplicação GreenPulse em diferentes plataformas.

## 📋 Pré-requisitos para Deploy

1. **Conta Google Cloud Platform** (para usar Earth Engine em produção)
2. **Service Account** do Earth Engine configurada
3. **Servidor com Python 3.8+**

## 🔐 Configuração de Produção

### 1. Criar Service Account no Google Cloud

Para usar o Earth Engine em produção (sem autenticação interativa), você precisa de uma Service Account:

1. Acesse: https://console.cloud.google.com/
2. Crie um novo projeto ou selecione um existente
3. Vá em "IAM & Admin" → "Service Accounts"
4. Clique em "Create Service Account"
5. Dê um nome (ex: "greenpulse-ee")
6. Clique em "Create and Continue"
7. Adicione a role "Earth Engine Resource Writer"
8. Clique em "Done"
9. Clique na service account criada
10. Vá em "Keys" → "Add Key" → "Create new key"
11. Escolha formato JSON e baixe o arquivo

### 2. Configurar Credenciais

Salve o arquivo JSON baixado e configure a variável de ambiente:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/caminho/para/service-account-key.json"
```

### 3. Modificar app.py para Produção

No arquivo `backend/app.py`, altere a inicialização do Earth Engine:

```python
# Substituir:
ee.Initialize()

# Por:
credentials = ee.ServiceAccountCredentials(
    email='seu-service-account@projeto.iam.gserviceaccount.com',
    key_file=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
)
ee.Initialize(credentials)
```

## 🌐 Opções de Deploy

### Opção 1: Deploy Local (Desenvolvimento)

Ideal para testes e desenvolvimento local.

```bash
cd greenpulse
./start.sh
```

Acesse: http://localhost:5000

### Opção 2: Deploy em Servidor Linux (VPS)

#### Passo 1: Preparar Servidor

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python e pip
sudo apt install python3 python3-pip -y

# Instalar nginx (opcional, para proxy reverso)
sudo apt install nginx -y
```

#### Passo 2: Transferir Arquivos

```bash
# No seu computador local
scp -r greenpulse/ usuario@seu-servidor.com:/home/usuario/
```

#### Passo 3: Instalar Dependências

```bash
# No servidor
cd greenpulse
pip3 install -r requirements.txt
```

#### Passo 4: Configurar Gunicorn

Instale o Gunicorn (servidor WSGI de produção):

```bash
pip3 install gunicorn
```

Crie arquivo `gunicorn_config.py`:

```python
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 5
```

#### Passo 5: Criar Serviço Systemd

Crie `/etc/systemd/system/greenpulse.service`:

```ini
[Unit]
Description=GreenPulse Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/greenpulse/backend
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/greenpulse/service-account-key.json"
ExecStart=/usr/local/bin/gunicorn -c ../gunicorn_config.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Ative o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable greenpulse
sudo systemctl start greenpulse
sudo systemctl status greenpulse
```

#### Passo 6: Configurar Nginx (Proxy Reverso)

Crie `/etc/nginx/sites-available/greenpulse`:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Ative a configuração:

```bash
sudo ln -s /etc/nginx/sites-available/greenpulse /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Opção 3: Deploy no Heroku

#### Passo 1: Preparar Arquivos

Crie `Procfile` na raiz do projeto:

```
web: cd backend && gunicorn app:app
```

Crie `runtime.txt`:

```
python-3.11.0
```

Adicione `gunicorn` ao `requirements.txt`:

```
gunicorn==21.2.0
```

#### Passo 2: Deploy

```bash
# Instalar Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login
heroku login

# Criar app
heroku create greenpulse-app

# Configurar variáveis de ambiente
heroku config:set GOOGLE_APPLICATION_CREDENTIALS="$(cat service-account-key.json)"

# Deploy
git init
git add .
git commit -m "Initial commit"
git push heroku main

# Abrir app
heroku open
```

### Opção 4: Deploy no Google Cloud Run

#### Passo 1: Criar Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json

CMD cd backend && python app.py
```

#### Passo 2: Deploy

```bash
# Instalar gcloud CLI
curl https://sdk.cloud.google.com | bash

# Autenticar
gcloud auth login

# Configurar projeto
gcloud config set project SEU_PROJETO_ID

# Build e deploy
gcloud builds submit --tag gcr.io/SEU_PROJETO_ID/greenpulse
gcloud run deploy greenpulse \
  --image gcr.io/SEU_PROJETO_ID/greenpulse \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 🔒 Segurança em Produção

### 1. HTTPS

Sempre use HTTPS em produção. Para Nginx + Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com
```

### 2. Variáveis de Ambiente

Nunca commite credenciais no Git. Use variáveis de ambiente:

```bash
export FLASK_SECRET_KEY="sua-chave-secreta-aleatoria"
export GOOGLE_APPLICATION_CREDENTIALS="/caminho/seguro/credentials.json"
```

### 3. Rate Limiting

Adicione rate limiting para proteger a API:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

## 📊 Monitoramento

### Logs

Para visualizar logs em produção:

```bash
# Systemd
sudo journalctl -u greenpulse -f

# Heroku
heroku logs --tail

# Google Cloud Run
gcloud run logs read greenpulse --limit=50
```

### Métricas

Configure monitoramento com:
- **Google Cloud Monitoring** (para Cloud Run)
- **Heroku Metrics** (para Heroku)
- **Prometheus + Grafana** (para VPS)

## 🐛 Troubleshooting

### Erro: "Earth Engine not initialized"

**Solução:** Verifique se a service account está configurada corretamente e tem permissões no Earth Engine.

### Erro: "Memory limit exceeded"

**Solução:** Aumente o número de workers do Gunicorn ou use instâncias com mais memória.

### Erro: "Timeout"

**Solução:** Aumente o timeout do Gunicorn (padrão: 30s, recomendado: 120s para Earth Engine).

## 📈 Otimizações

### Cache

Implemente cache para reduzir chamadas ao Earth Engine:

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/heatmap/<city_id>')
@cache.cached(timeout=3600)  # Cache por 1 hora
def get_heatmap(city_id):
    # ...
```

### CDN

Use CDN para servir assets estáticos (CSS, JS, imagens).

### Compressão

Ative compressão gzip no Nginx:

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

## 🎉 Pronto!

Sua aplicação GreenPulse está no ar! 🌳

Para suporte, consulte:
- Documentação do Earth Engine: https://developers.google.com/earth-engine
- Documentação do Flask: https://flask.palletsprojects.com/
