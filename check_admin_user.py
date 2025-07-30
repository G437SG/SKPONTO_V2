#!/usr/bin/env python3
"""
Verificar e corrigir usuário admin no banco de dados
"""

import sys
import os
from datetime import datetime

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.abspath('.'))

from app import create_app, db
from app.models import User, UserType
from werkzeug.security import generate_password_hash

def check_admin_user():
    """Verificar se existe usuário admin"""
    app = create_app()
    
    with app.app_context():
        print("🔍 VERIFICANDO USUÁRIO ADMIN")
        print("="*40)
        
        # Verificar se existe admin
        admin = User.query.filter_by(email='admin@skponto.com').first()
        
        if admin:
            print("✅ Usuário admin encontrado!")
            print(f"   ID: {admin.id}")
            print(f"   Email: {admin.email}")
            print(f"   Nome: {admin.nome} {admin.sobrenome}")
            print(f"   Tipo: {admin.user_type}")
            print(f"   Ativo: {admin.is_active}")
            print(f"   Aprovado: {admin.is_approved}")
            print(f"   CPF: {admin.cpf}")
            
            # Testar senha
            print("\n🔐 TESTANDO SENHA...")
            if admin.check_password('admin123'):
                print("✅ Senha 'admin123' está correta!")
            else:
                print("❌ Senha 'admin123' está incorreta!")
                print("🔧 Corrigindo senha...")
                admin.set_password('admin123')
                db.session.commit()
                print("✅ Senha corrigida!")
            
            # Verificar se está ativo e aprovado
            if not admin.is_active:
                print("🔧 Ativando usuário admin...")
                admin.is_active = True
                db.session.commit()
                print("✅ Usuário ativado!")
            
            if not admin.is_approved:
                print("🔧 Aprovando usuário admin...")
                admin.is_approved = True
                db.session.commit()
                print("✅ Usuário aprovado!")
                
        else:
            print("❌ Usuário admin não encontrado!")
            print("🔧 Criando usuário admin...")
            
            admin = User(
                email='admin@skponto.com',
                cpf='00000000000',
                nome='Administrador',
                sobrenome='Sistema',
                telefone='(11) 99999-9999',
                cargo='Administrador',
                user_type=UserType.ADMIN,
                is_active=True,
                is_approved=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            admin.set_password('admin123')
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ Usuário admin criado com sucesso!")
            print(f"   Email: admin@skponto.com")
            print(f"   Senha: admin123")
        
        # Listar todos os usuários
        print("\n👥 TODOS OS USUÁRIOS NO SISTEMA:")
        users = User.query.all()
        for user in users:
            print(f"   • {user.email} - {user.nome} {user.sobrenome} - {user.user_type} - {'Ativo' if user.is_active else 'Inativo'}")

if __name__ == "__main__":
    check_admin_user()
