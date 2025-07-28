#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para inicializar banco PostgreSQL no Render.com
Cria tabelas e usuários de exemplo para testar o sistema
"""

import os
import sys
from datetime import datetime, date, timedelta

# Adicionar o diretório pai ao path para importar app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Definir ambiente de produção
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_CONFIG'] = 'production'

try:
    print("🚀 Inicializando banco PostgreSQL para produção...")
    print("📋 Configurando imports...")
    
    from app import create_app, db
    from app.models import (
        User, UserType, HourBank, OvertimeRequest, 
        OvertimeSettings, OvertimeStatus, WorkClass,
        HourBankHistory, HourBankTransactionType
    )
    from werkzeug.security import generate_password_hash
    
    print("✅ Imports realizados com sucesso")
    
    app = create_app('production')
    
    with app.app_context():
        print("📋 Verificando conexão com banco de dados...")
        
        # Verificar qual banco está sendo usado
        try:
            from sqlalchemy import text
            
            # Verificar se é PostgreSQL ou SQLite
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            print(f"📊 Database URL: {db_url[:50]}...")
            
            if 'postgres' in db_url.lower():
                print("🐘 PostgreSQL detectado")
                result = db.session.execute(text("SELECT version();"))
                version = result.fetchone()[0]
                print(f"✅ Conectado ao PostgreSQL: {version[:50]}...")
            else:
                print("📁 SQLite detectado")
                result = db.session.execute(text("SELECT sqlite_version();"))
                version = result.fetchone()[0]
                print(f"✅ Conectado ao SQLite: {version}")
                
        except Exception as e:
            print(f"❌ Erro na conexão: {e}")
            print("⚠️ Continuando mesmo assim...")
            # Não falhar aqui, continuar com a inicialização
        
        print("🗄️ Criando tabelas...")
        try:
            db.create_all()
            print("✅ Tabelas criadas com sucesso")
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            sys.exit(1)
        
        print("👥 Verificando usuários existentes...")
        existing_users = User.query.count()
        print(f"   Usuários encontrados: {existing_users}")
        
        if existing_users == 0:
            print("🔧 Criando usuários de exemplo...")
            
            # Primeiro, criar classes de trabalho
            print("⚙️ Criando classes de trabalho...")
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
            
            users_to_create = [
                {
                    'nome': 'Admin',
                    'sobrenome': 'Sistema',
                    'email': 'admin@skponto.com',
                    'cpf': '00000000000',
                    'password': 'admin123',
                    'user_type': UserType.ADMIN,
                    'work_class_id': clt_class.id
                },
                {
                    'nome': 'João',
                    'sobrenome': 'Silva',
                    'email': 'joao@empresa.com',
                    'cpf': '11111111111',
                    'password': 'senha123',
                    'user_type': UserType.TRABALHADOR,
                    'work_class_id': clt_class.id
                },
                {
                    'nome': 'Maria',
                    'sobrenome': 'Santos',
                    'email': 'maria@empresa.com',
                    'cpf': '22222222222',
                    'password': 'senha123',
                    'user_type': UserType.TRABALHADOR,
                    'work_class_id': clt_class.id
                },
                {
                    'nome': 'Pedro',
                    'sobrenome': 'Oliveira',
                    'email': 'pedro@empresa.com',
                    'cpf': '33333333333',
                    'password': 'senha123',
                    'user_type': UserType.ESTAGIARIO,
                    'work_class_id': estagiario_class.id
                },
                {
                    'nome': 'Ana',
                    'sobrenome': 'Costa',
                    'email': 'ana@empresa.com',
                    'cpf': '44444444444',
                    'password': 'senha123',
                    'user_type': UserType.TRABALHADOR,
                    'work_class_id': clt_class.id
                }
            ]
            
            created_users = []
            
            for user_data in users_to_create:
                try:
                    user = User(
                        nome=user_data['nome'],
                        sobrenome=user_data['sobrenome'],
                        email=user_data['email'],
                        cpf=user_data['cpf'],
                        password_hash=generate_password_hash(user_data['password']),
                        user_type=user_data['user_type'],
                        work_class_id=user_data['work_class_id'],
                        is_active=True,
                        is_approved=True,
                        created_at=datetime.utcnow()
                    )
                    
                    db.session.add(user)
                    db.session.flush()  # Para obter o ID
                    
                    # Criar banco de horas para cada usuário
                    hour_bank = HourBank(
                        user_id=user.id,
                        current_balance=0.0,
                        last_updated=datetime.utcnow()
                    )
                    db.session.add(hour_bank)
                    
                    created_users.append(user)
                    print(f"   ✅ Usuário criado: {user.email}")
                    
                except Exception as e:
                    print(f"   ❌ Erro ao criar usuário {user_data['email']}: {e}")
                    db.session.rollback()
                    continue
            
            try:
                db.session.commit()
                print(f"✅ {len(created_users)} usuários criados com sucesso!")
                
                # Criar alguns saldos de exemplo
                print("💰 Adicionando saldos de exemplo...")
                
                for i, user in enumerate(created_users[1:], 1):  # Pular admin
                    if user.user_type != UserType.ADMIN:
                        try:
                            hour_bank = HourBank.query.filter_by(user_id=user.id).first()
                            if hour_bank:
                                # Saldos variados para teste
                                saldo_exemplo = [8.5, -2.0, 16.25, 0.0, 4.75][i-1] if i <= 5 else 0.0
                                hour_bank.current_balance = saldo_exemplo
                                
                                # Histórico de exemplo
                                history = HourBankHistory(
                                    user_id=user.id,
                                    transaction_type=HourBankTransactionType.CREDIT if saldo_exemplo > 0 else HourBankTransactionType.DEBIT,
                                    hours_amount=abs(saldo_exemplo),
                                    balance_before=0.0,
                                    balance_after=saldo_exemplo,
                                    description=f"Saldo inicial de exemplo",
                                    created_at=datetime.utcnow()
                                )
                                db.session.add(history)
                                print(f"   💰 Saldo para {user.nome}: {saldo_exemplo}h")
                        except Exception as e:
                            print(f"   ⚠️ Erro ao criar saldo para {user.nome}: {e}")
                
                db.session.commit()
                print("✅ Saldos de exemplo criados!")
                
            except Exception as e:
                print(f"❌ Erro ao salvar no banco: {e}")
                db.session.rollback()
                sys.exit(1)
        else:
            print("✅ Usuários já existem no banco")
        
        # Verificar configurações de horas extras
        print("⚙️ Verificando configurações de horas extras...")
        try:
            settings = OvertimeSettings.query.first()
            if not settings:
                settings = OvertimeSettings(
                    auto_approval_enabled=False,
                    max_daily_overtime=4.0,
                    max_monthly_overtime=40.0,
                    require_justification=True,
                    notification_enabled=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(settings)
                db.session.commit()
                print("✅ Configurações de horas extras criadas")
            else:
                print("✅ Configurações já existem")
        except Exception as e:
            print(f"⚠️ Erro nas configurações de horas extras: {e}")
        
        # Verificação final
        print("🔍 Verificação final...")
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True, is_approved=True).count()
        hour_banks = HourBank.query.count()
        
        print(f"   📊 Total de usuários: {total_users}")
        print(f"   ✅ Usuários ativos: {active_users}")
        print(f"   💰 Bancos de horas: {hour_banks}")
        
        if active_users > 0:
            print("🎉 Banco inicializado com sucesso!")
            print("📋 Credenciais de teste:")
            print("   Admin: admin@skponto.com / admin123")
            print("   Usuário: joao@empresa.com / senha123")
            print("   Usuário: maria@empresa.com / senha123")
        else:
            print("❌ Nenhum usuário ativo encontrado")
            sys.exit(1)

except Exception as e:
    print(f"❌ Erro crítico: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
