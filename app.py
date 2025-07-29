# -*- coding: utf-8 -*-
"""
SKPONTO - Sistema de Controle de Ponto
Aplicação principal Flask
"""

import os
import sys
from pathlib import Path
from flask_migrate import Migrate
from app import create_app, db

# Importar modelos (movido para o topo)
from app.models import (
    User, TimeRecord, MedicalAttestation, Notification,
    SecurityLog, SystemConfig, UserType, AttestationType,
    AttestationStatus, NotificationType, WorkClass,
    BackupHistory, UserApprovalRequest,
    SystemStatus, BackupType, BackupStatus, ApprovalStatus
)

def ensure_directories():
    """Garante que todos os diretórios necessários existam"""
    directories = [
        'storage',
        'storage/database', 
        'storage/backups',
        'storage/logs',
        'storage/uploads',
        'storage/attestations',
        'logs'
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f" ✅ Diretório verificado: {directory}")
        except Exception as e:
            print(f" ⚠️  Erro ao criar diretório {directory}: {e}")

def check_database_connection():
    """Verifica a conexão com o banco de dados - modo não crítico"""
    try:
        # Testar conexão com o banco
        with db.engine.connect() as connection:
            result = connection.execute(db.text("SELECT 1"))
            result.fetchone()
        print(" ✅ Conexão com PostgreSQL estabelecida")
        return True
    except Exception as e:
        print(f" ⚠️  Aviso de conexão com o banco: {e}")
        print(" 🔄 A aplicação continuará executando...")
        return False

# Criar a aplicação Flask
app = create_app(os.getenv('FLASK_CONFIG') or 'production')
migrate = Migrate(app, db)

# Garantir que os diretórios existam
ensure_directories()


@app.shell_context_processor
def make_shell_context():
    """Contexto do shell Flask"""
    return {
        'db': db,
        'User': User,
        'TimeRecord': TimeRecord,
        'MedicalAttestation': MedicalAttestation,
        'Notification': Notification,
        'SecurityLog': SecurityLog,
        'SystemConfig': SystemConfig,
        'UserType': UserType,
        'AttestationType': AttestationType,
        'AttestationStatus': AttestationStatus,
        'NotificationType': NotificationType,
        'WorkClass': WorkClass,
        'BackupHistory': BackupHistory,
        'UserApprovalRequest': UserApprovalRequest,
        'SystemStatus': SystemStatus,
        'BackupType': BackupType,
        'BackupStatus': BackupStatus,
        'ApprovalStatus': ApprovalStatus
    }


if __name__ == '__main__':
    # Configurar DATABASE_URL se não existir
    if not os.getenv('DATABASE_URL'):
        print(" 🔧 CONFIGURADO DATABASE_URL padrão para PostgreSQL")
        os.environ['DATABASE_URL'] = 'postgresql://skponto_user:ho8BpKkpG7dBMP7qGygnSP9G5vQd3FzF@dpg-d1rq11vgi27c73cm8oj0-a.oregon-postgres.render.com/skponto_production'
    
    print(f" 🗄️  POSTGRESQL MODE - URI: {os.environ['DATABASE_URL'][:50]}...")
    print(f" 🚀 USANDO POSTGRESQL PARA PRODUÇÃO")
    print(f" 🌍 Ambiente: {os.getenv('FLASK_ENV', 'production')}")
    
    # Garantir diretórios
    ensure_directories()
    
    # Configuração para desenvolvimento e produção
    debug = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('PORT', 5000))
    host = '0.0.0.0'  # Necessário para Render.com
    
    print(f" 🚀 Iniciando SKPONTO na porta {port}")
    print(f" � Acesse: http://localhost:{port}")
    
    # Verificações não críticas em background
    try:
        with app.app_context():
            # Verificar conexão (não crítico)
            check_database_connection()
            
            # Tentar configurar banco (não crítico)
            try:
                db.create_all()
                print(" ✅ Tabelas do banco verificadas")
            except Exception as e:
                print(f" ⚠️  Aviso ao verificar tabelas: {e}")
            
            # Verificar admin (não crítico)
            try:
                admin_exists = User.query.filter_by(
                    user_type=UserType.ADMIN
                ).first()
                if not admin_exists:
                    print("  ⚠️  AVISO: Execute 'flask create-admin' para criar administrador")
                else:
                    print(" ✅ Administrador encontrado no sistema")
            except Exception as e:
                print(f" ⚠️  Aviso: {e}")
    except Exception as e:
        print(f" ⚠️  Aviso na inicialização: {e}")
        print(" 🔄 A aplicação continuará executando...")
    
    # INICIAR A APLICAÇÃO (SEMPRE)
    try:
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        print(f" ❌ Erro ao iniciar aplicação: {e}")
        print(" � Verifique se a porta não está em uso")
        input(" 📋 Pressione Enter para sair...")
