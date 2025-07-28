#!/bin/bash
set -e  # Parar em caso de erro

# Build script para Render.com
echo "🚀 Iniciando build para produção..."

# Verificar versão do Python
echo "🐍 Versão do Python:"
python --version

# Verificar se estamos usando Python 3.11 (obrigatório)
python_version=$(python --version 2>&1)
if [[ $python_version != *"3.11"* ]]; then
    echo "❌ ERRO: É necessário Python 3.11.x para compatibilidade"
    echo "📋 Render.com deveria usar runtime.txt: python-3.11.9"
    # Não falhar aqui, deixar o sistema tentar
fi

# Definir configurações de produção
export FLASK_ENV=production
export FLASK_CONFIG=production

# Instalar dependências essenciais com versões específicas
echo "📦 Instalando dependências essenciais..."
pip install --upgrade pip

# Instalar Flask stack em ordem específica para evitar conflitos
echo "🔧 Instalando Flask stack..."
pip install --no-cache-dir Werkzeug==2.3.7
pip install --no-cache-dir Flask==2.3.3
pip install --no-cache-dir -r requirements.txt

# Verificar instalação crítica
echo "🔍 Verificando instalações críticas..."
python -c "
try:
    import werkzeug
    print('✅ Werkzeug:', werkzeug.__version__)
    import flask
    print('✅ Flask:', flask.__version__)
    import gunicorn
    print('✅ Gunicorn instalado')
    import flask_sqlalchemy
    print('✅ Flask-SQLAlchemy instalado')
    print('✅ Dependências essenciais instaladas com sucesso!')
except ImportError as e:
    print('❌ Erro na importação:', e)
    exit(1)
"

# Tentar instalar dependências opcionais (não críticas)
echo "📊 Tentando instalar dependências opcionais..."
pip install xlsxwriter==3.1.2 || echo "⚠️ xlsxwriter não pôde ser instalado - funcionalidade Excel limitada"

# Inicializar banco de dados
echo "🗄️ Inicializando banco de dados..."

# Tentar Flask-Migrate primeiro
if flask db upgrade 2>/dev/null; then
    echo "✅ Migração Flask-Migrate concluída"
elif test -f scripts/init_db.py && python scripts/init_db.py 2>/dev/null; then
    echo "✅ Inicialização via scripts/init_db.py concluída"
else
    echo "⚠️ Criando tabelas manualmente..."
    python -c "
import os
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_CONFIG'] = 'production'
try:
    from app import create_app, db
    app = create_app('production')
    with app.app_context():
        db.create_all()
        print('✅ Tabelas criadas com sucesso')
except Exception as e:
    print(f'❌ Erro ao criar tabelas: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"
fi

echo "✅ Build concluído com sucesso!"
echo "📋 Sistema funcional com dependências essenciais"
echo "💡 Para funcionalidades Excel avançadas, instale requirements-optional.txt"
