#!/bin/bash

# Build script para Render.com
echo "🚀 Iniciando build para produção..."

# Definir configurações de produção
export FLASK_ENV=production
export FLASK_CONFIG=production

# Instalar dependências
echo "📦 Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# Verificar instalação
echo "🔍 Verificando instalação..."
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import psycopg; print('psycopg3 instalado')"

# Executar scripts de inicialização em ordem de prioridade
echo "🗄️ Inicializando banco de dados..."

# Tentar Flask-Migrate primeiro
if flask db upgrade 2>/dev/null; then
    echo "✅ Migração Flask-Migrate concluída"
elif python init_db.py 2>/dev/null; then
    echo "✅ Inicialização via init_db.py concluída"
elif python force_init_db.py 2>/dev/null; then
    echo "✅ Inicialização via force_init_db.py concluída"
elif python force_production_init.py 2>/dev/null; then
    echo "✅ Inicialização via force_production_init.py concluída"
else
    echo "⚠️ Tentando inicialização manual..."
    python -c "
import os
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_CONFIG'] = 'production'
from app import create_app, db
app = create_app('production')
with app.app_context():
    db.create_all()
    print('✅ Tabelas criadas manualmente')
"
fi

# Executar diagnóstico final
echo "🔍 Executando diagnóstico final..."
python troubleshoot_production.py || echo "⚠️ Diagnóstico com problemas - verificar logs"

echo "✅ Build concluído!"
