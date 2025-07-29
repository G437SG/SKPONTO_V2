#!/usr/bin/env python3
"""
Análise Completa do Sistema SKPONTO V2
Verificação de rotas, models, templates e dependências
"""

import sys
import os
from pathlib import Path

def analyze_system():
    """Análise completa do sistema"""
    print("🔍 ANÁLISE COMPLETA DO SISTEMA SKPONTO V2")
    print("=" * 50)
    
    try:
        # Teste 1: Verificar dependências críticas
        print("\n1. VERIFICAÇÃO DE DEPENDÊNCIAS:")
        missing_deps = []
        
        try:
            import flask
            print(f"   ✅ Flask: {flask.__version__}")
        except ImportError:
            missing_deps.append("flask")
            
        try:
            import psycopg2
            print(f"   ✅ psycopg2: {psycopg2.__version__}")
        except ImportError:
            missing_deps.append("psycopg2-binary")
            
        try:
            import sqlalchemy
            print(f"   ✅ SQLAlchemy: {sqlalchemy.__version__}")
        except ImportError:
            missing_deps.append("flask-sqlalchemy")
            
        if missing_deps:
            print(f"   ❌ Dependências faltando: {missing_deps}")
            return False
        
        # Teste 2: Verificar estrutura de diretórios
        print("\n2. VERIFICAÇÃO DE ESTRUTURA:")
        required_dirs = [
            'app',
            'app/templates',
            'app/static',
            'app/models',
            'app/admin',
            'app/auth',
            'app/main'
        ]
        
        for dir_path in required_dirs:
            if os.path.exists(dir_path):
                print(f"   ✅ {dir_path}")
            else:
                print(f"   ❌ {dir_path} - FALTANDO")
        
        # Teste 3: Verificar imports principais
        print("\n3. VERIFICAÇÃO DE IMPORTS:")
        try:
            from app import create_app, db
            print("   ✅ app imports")
        except Exception as e:
            print(f"   ❌ app imports: {e}")
            return False
        
        try:
            from app.models import User, UserType
            print("   ✅ models imports")
        except Exception as e:
            print(f"   ❌ models imports: {e}")
            return False
        
        # Teste 4: Criar app e verificar rotas
        print("\n4. VERIFICAÇÃO DE ROTAS:")
        try:
            app = create_app('development')
            
            with app.app_context():
                print(f"   ✅ App criada: {app.name}")
                
                # Listar todas as rotas
                routes = []
                error_routes = []
                
                for rule in app.url_map.iter_rules():
                    route_info = {
                        'endpoint': rule.endpoint,
                        'rule': rule.rule,
                        'methods': list(rule.methods)
                    }
                    routes.append(route_info)
                    
                    # Verificar se a rota tem função associada
                    try:
                        if rule.endpoint in app.view_functions:
                            print(f"   ✅ {rule.rule} -> {rule.endpoint}")
                        else:
                            print(f"   ⚠️  {rule.rule} -> {rule.endpoint} (sem função)")
                            error_routes.append(rule.endpoint)
                    except Exception as e:
                        print(f"   ❌ {rule.rule} -> ERRO: {e}")
                        error_routes.append(rule.endpoint)
                
                print(f"\n   📊 RESUMO DE ROTAS:")
                print(f"   - Total de rotas: {len(routes)}")
                print(f"   - Rotas com problemas: {len(error_routes)}")
                
                if error_routes:
                    print(f"   ❌ Rotas problemáticas: {error_routes}")
        
        except Exception as e:
            print(f"   ❌ Erro ao criar app: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Teste 5: Verificar blueprints
        print("\n5. VERIFICAÇÃO DE BLUEPRINTS:")
        try:
            blueprint_files = [
                'app/main/__init__.py',
                'app/auth/__init__.py', 
                'app/admin/__init__.py',
                'app/api/__init__.py'
            ]
            
            for bp_file in blueprint_files:
                if os.path.exists(bp_file):
                    print(f"   ✅ {bp_file}")
                else:
                    print(f"   ❌ {bp_file} - FALTANDO")
                    
        except Exception as e:
            print(f"   ❌ Erro verificando blueprints: {e}")
        
        # Teste 6: Verificar templates críticos
        print("\n6. VERIFICAÇÃO DE TEMPLATES:")
        critical_templates = [
            'app/templates/base.html',
            'app/templates/auth/login.html',
            'app/templates/main/index.html',
            'app/templates/admin/dashboard.html'
        ]
        
        for template in critical_templates:
            if os.path.exists(template):
                print(f"   ✅ {template}")
            else:
                print(f"   ❌ {template} - FALTANDO")
        
        # Teste 7: Verificar arquivo de configuração
        print("\n7. VERIFICAÇÃO DE CONFIGURAÇÃO:")
        if os.path.exists('config.py'):
            try:
                from config import Config
                print(f"   ✅ config.py carregado")
                print(f"   📋 SECRET_KEY: {'Configurado' if hasattr(Config, 'SECRET_KEY') else 'FALTANDO'}")
                print(f"   📋 SQLALCHEMY_DATABASE_URI: {'Configurado' if hasattr(Config, 'SQLALCHEMY_DATABASE_URI') else 'FALTANDO'}")
            except Exception as e:
                print(f"   ❌ Erro carregando config: {e}")
        else:
            print("   ❌ config.py - FALTANDO")
        
        print("\n" + "=" * 50)
        print("✅ ANÁLISE CONCLUÍDA")
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO NA ANÁLISE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Adicionar diretório atual ao path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    success = analyze_system()
    sys.exit(0 if success else 1)
