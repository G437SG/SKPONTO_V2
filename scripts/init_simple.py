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
        
        # Criar classes de trabalho se não existirem
        print("⚙️ Verificando classes de trabalho...")
        clt_class = WorkClass.query.filter_by(name='CLT').first()
        if not clt_class:
            print("🔧 Criando classes de trabalho...")
            clt_class = WorkClass(
                name='CLT',
                description='Trabalhador CLT - 8 horas diárias',
                daily_work_hours=8.0,
                lunch_hours=1.0,
                is_active=True,
                is_approved=True,
                created_at=datetime.utcnow()
            )
            db.session.add(clt_class)
            
            estagiario_class = WorkClass(
                name='Estagiário',
                description='Estagiário - 6 horas diárias',
                daily_work_hours=6.0,
                lunch_hours=0.5,
                is_active=True,
                is_approved=True,
                created_at=datetime.utcnow()
            )
            db.session.add(estagiario_class)
            
            db.session.commit()
            print("✅ Classes de trabalho criadas")
        else:
            print("✅ Classes de trabalho já existem")
        
        # Recarregar as classes
        clt_class = WorkClass.query.filter_by(name='CLT').first()
        estagiario_class = WorkClass.query.filter_by(name='Estagiário').first()
        
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
                work_class_id=clt_class.id if clt_class else None,
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
                ('João', 'Silva', 'joao@empresa.com', '11111111111', UserType.TRABALHADOR, clt_class.id),
                ('Maria', 'Santos', 'maria@empresa.com', '22222222222', UserType.TRABALHADOR, clt_class.id),
                ('Pedro', 'Costa', 'pedro@empresa.com', '33333333333', UserType.ESTAGIARIO, estagiario_class.id if estagiario_class else clt_class.id)
            ]
            
            for nome, sobrenome, email, cpf, user_type, work_class_id in users_data:
                user = User(
                    nome=nome,
                    sobrenome=sobrenome,
                    email=email,
                    cpf=cpf,
                    password_hash=generate_password_hash('senha123'),
                    user_type=user_type,
                    work_class_id=work_class_id,
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
