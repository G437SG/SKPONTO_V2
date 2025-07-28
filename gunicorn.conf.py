# Configuração do Gunicorn para produção no Render.com
import os

# Configurações básicas
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1  # Free plan limitation
worker_class = "sync"
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
worker_connections = 1000

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "skponto-app"

# Worker process settings
worker_tmp_dir = "/dev/shm"
tmp_upload_dir = None

# SSL (handled by Render)
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTO': 'https',
}

# Performance
max_worker_connections = 1000
worker_rlimit_nofile = 1000
