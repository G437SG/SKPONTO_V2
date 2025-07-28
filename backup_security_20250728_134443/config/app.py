# -*- coding: utf-8 -*-
"""
SKPONTO - Sistema de Controle de Ponto
Aplicação principal Flask
"""

import os
from flask_migrate import Migrate
from app import create_app, db
from app.models import (
    User, TimeRecord, MedicalAttestation, Notification,
    SecurityLog, SystemConfig, UserType, AttestationType,
    AttestationStatus, NotificationType, WorkClass,
    BackupHistory, UserApprovalRequest,
    SystemStatus, BackupType, BackupStatus, ApprovalStatus
)

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)


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
    with app.app_context():
        # Criar tabelas se não existirem
        try:
            db.create_all()
            print(" ✅ Tabelas do banco de dados verificadas")
        except Exception as e:
            print(f" ❌ Erro ao verificar tabelas: {e}")
            print(" 🔧 Recriando banco de dados...")
            try:
                db.drop_all()
                db.create_all()
                print(" ✅ Banco de dados recriado com sucesso")
            except Exception as e2:
                print(f" ❌ Erro ao recriar banco: {e2}")
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
    print(f" 🌍 Ambiente: {os.getenv('FLASK_ENV', 'development')}")
    
    app.run(host=host, port=port, debug=debug)
