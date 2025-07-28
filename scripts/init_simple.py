#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simples para inicializar qualquer banco de dados
Funciona tanto com PostgreSQL quanto SQLite
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Definir ambiente de produção
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_CONFIG'] = 'production'

try:
    print("🚀 Inicializando banco de dados...")
    
    from app import create_app, db
    from app.models import User, UserType, HourBank, WorkClass
    from werkzeug.security import generate_password_hash
    
    app = create_app('production')
    
    with app.app_context():
        # Verificar tipo de banco
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if 'postgres' in db_url.lower():
            print("🐘 PostgreSQL detectado")
        else:
            print("📁 SQLite detectado")
        
        print("🗄️ Criando tabelas...")
        db.create_all()
        print("✅ Tabelas criadas")
        
        # Verificar usuários existentes
        user_count = User.query.count()
        print(f"👥 Usuários existentes: {user_count}")
        
        if user_count == 0:
            print("🔧 Criando usuários básicos...")
            
            # Criar admin
            admin = User(
                nome='Admin',
                sobrenome='Sistema',
                email='admin@skponto.com',
                cpf='00000000000',
                password_hash=generate_password_hash('admin123'),
                user_type=UserType.ADMIN,
                work_class=WorkClass.CLT,
                is_active=True,
                is_approved=True,
                created_at=datetime.utcnow()
            )
            db.session.add(admin)
            db.session.flush()
            
            # Banco de horas para admin
            admin_bank = HourBank(
                user_id=admin.id,
                current_balance=0.0,
                last_updated=datetime.utcnow()
            )
            db.session.add(admin_bank)
            
            # Criar alguns usuários de teste
            users_data = [
                ('João', 'Silva', 'joao@empresa.com', '11111111111'),
                ('Maria', 'Santos', 'maria@empresa.com', '22222222222'),
                ('Pedro', 'Costa', 'pedro@empresa.com', '33333333333')
            ]
            
            for nome, sobrenome, email, cpf in users_data:
                user = User(
                    nome=nome,
                    sobrenome=sobrenome,
                    email=email,
                    cpf=cpf,
                    password_hash=generate_password_hash('senha123'),
                    user_type=UserType.TRABALHADOR,
                    work_class=WorkClass.CLT,
                    is_active=True,
                    is_approved=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(user)
                db.session.flush()
                
                # Banco de horas
                bank = HourBank(
                    user_id=user.id,
                    current_balance=0.0,
                    last_updated=datetime.utcnow()
                )
                db.session.add(bank)
                
                print(f"   ✅ Usuário: {email}")
            
            db.session.commit()
            print("✅ Usuários criados com sucesso!")
            
        else:
            print("✅ Usuários já existem")
        
        # Verificação final
        final_count = User.query.count()
        active_count = User.query.filter_by(is_active=True, is_approved=True).count()
        
        print(f"📊 Total: {final_count} usuários, {active_count} ativos")
        print("🎉 Inicialização concluída!")
        print("📋 Login: admin@skponto.com / admin123")

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
