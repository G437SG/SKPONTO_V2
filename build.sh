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

# Verificar instalação Flask
echo "🔍 Verificando instalação..."
python -c "import flask; print('Flask:', flask.__version__)"

# Inicializar banco de dados
echo "🗄️ Inicializando banco de dados..."

# Tentar Flask-Migrate primeiro
if flask db upgrade 2>/dev/null; then
    echo "✅ Migração Flask-Migrate concluída"
elif python scripts/init_db.py 2>/dev/null; then
    echo "✅ Inicialização via scripts/init_db.py concluída"
else
    echo "⚠️ Criando tabelas manualmente..."
    python -c "
import os
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_CONFIG'] = 'production'
from app import create_app, db
app = create_app('production')
with app.app_context():
    try:
        db.create_all()
        print('✅ Tabelas criadas com sucesso')
    except Exception as e:
        print(f'❌ Erro ao criar tabelas: {e}')
        exit(1)
"
fi

echo "✅ Build concluído com sucesso!"
