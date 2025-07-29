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
    """Verifica a conexão com o banco de dados"""
    try:
        # Testar conexão com o banco
        with db.engine.connect() as connection:
            result = connection.execute(db.text("SELECT 1"))
            result.fetchone()
        print(" ✅ Conexão com PostgreSQL estabelecida")
        return True
    except Exception as e:
        print(f" ❌ Erro de conexão com o banco: {e}")
        return False
from app.models import (
    User, TimeRecord, MedicalAttestation, Notification,
    SecurityLog, SystemConfig, UserType, AttestationType,
    AttestationStatus, NotificationType, WorkClass,
    BackupHistory, UserApprovalRequest,
    SystemStatus, BackupType, BackupStatus, ApprovalStatus
)

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
    # Garantir que estamos usando PostgreSQL em produção
    if not os.getenv('DATABASE_URL'):
        print(" ⚠️  CONFIGURANDO DATABASE_URL para PostgreSQL...")
        os.environ['DATABASE_URL'] = 'postgresql://skponto_user:ho8BpKkpG7dBMP7qGygnSP9G5vQd3FzF@dpg-d1rq11vgi27c73cm8oj0-a.oregon-postgres.render.com/skponto_production'
    
    print(f" 🗄️  Usando banco: PostgreSQL")
    print(f" 🌍 Ambiente: {os.getenv('FLASK_ENV', 'production')}")
    
    with app.app_context():
        # Verificar conexão com PostgreSQL
        if not check_database_connection():
            print(" ❌ Falha na conexão com PostgreSQL!")
            print(" 🔧 Verifique se o banco está acessível...")
            exit(1)
        
        # Criar tabelas se não existirem
        try:
            db.create_all()
            print(" ✅ Tabelas do banco de dados verificadas")
        except Exception as e:
            print(f" ❌ Erro ao verificar tabelas: {e}")
            print(" 🔧 Tentando recriar tabelas...")
            try:
                db.create_all()
                print(" ✅ Banco de dados configurado com sucesso")
            except Exception as e2:
                print(f" ❌ Erro ao configurar banco: {e2}")
                exit(1)
        
        # Verificar se existe pelo menos um admin
        try:
            admin_exists = User.query.filter_by(
                user_type=UserType.ADMIN
            ).first()
            if not admin_exists:
                print("  ⚠️  AVISO: Nenhum administrador encontrado!")
                print("  Execute: flask create-admin")
                print("  Para criar o primeiro administrador do sistema.")
            else:
                print(" ✅ Administrador encontrado no sistema")
        except Exception as e:
            print(
                " ⚠️  Aviso: Não foi possível verificar administradores: "
                f"{e}"
            )
    
    # Configuração para desenvolvimento e produção
    debug = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('PORT', 5000))
    host = '0.0.0.0'  # Necessário para Render.com
    
    print(f" 🚀 Iniciando SKPONTO na porta {port}")
    
    app.run(host=host, port=port, debug=debug)
