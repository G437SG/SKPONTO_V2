#!/usr/bin/env python3
"""
Debug detalhado da configuração CSRF
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def debug_csrf_detailed():
    """Debug detalhado da configuração CSRF"""
    print("🔍 DEBUG DETALHADO DO CSRF")
    
    app = create_app()
    
    with app.app_context():
        # 1. Verificar configurações
        print("\n📋 CONFIGURAÇÕES CSRF:")
        print(f"SECRET_KEY: {app.config.get('SECRET_KEY', 'None')[:20]}...")
        print(f"WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED')}")
        print(f"WTF_CSRF_TIME_LIMIT: {app.config.get('WTF_CSRF_TIME_LIMIT')}")
        print(f"WTF_CSRF_SSL_STRICT: {app.config.get('WTF_CSRF_SSL_STRICT')}")
        
        # 2. Testar form
        print("\n📝 TESTANDO FORM:")
        with app.test_request_context('/', method='GET'):
            from app.forms import LoginForm
            form = LoginForm()
            print(f"Form criado: {form}")
            print(f"Form CSRF token field: {hasattr(form, 'csrf_token')}")
            if hasattr(form, 'csrf_token'):
                print(f"CSRF token do form: {form.csrf_token.current_token[:30]}...")
        
        # 3. Testar com request context
        print("\n🌐 TESTANDO COM REQUEST CONTEXT:")
        with app.test_request_context('/', method='GET'):
            from flask_wtf.csrf import generate_csrf, validate_csrf
            from flask import session
            
            # Gerar token
            try:
                csrf_token = generate_csrf()
                print(f"✅ CSRF token gerado: {csrf_token[:30]}...")
                
                # Verificar se foi salvo na sessão
                print(f"Session keys: {list(session.keys())}")
                csrf_key = session.get('csrf_token', 'Not found')
                print(f"CSRF na sessão: {csrf_key}")
                
                # Testar validação
                try:
                    validate_csrf(csrf_token)
                    print("✅ CSRF token válido!")
                except Exception as e:
                    print(f"❌ CSRF token inválido: {e}")
                    
            except Exception as e:
                print(f"❌ Erro ao gerar CSRF: {e}")
        
        # 4. Simular request POST
        print("\n📮 SIMULANDO REQUEST POST:")
        with app.test_client() as client:
            # GET para obter token
            response = client.get('/login')
            print(f"GET /login status: {response.status_code}")
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.data, 'html.parser')
                csrf_input = soup.find('input', {'name': 'csrf_token'})
                
                if csrf_input:
                    csrf_token = csrf_input.get('value')
                    print(f"CSRF do HTML: {csrf_token[:30]}...")
                    
                    # POST com token
                    login_data = {
                        'email': 'admin@skponto.com',
                        'password': 'admin123', 
                        'csrf_token': csrf_token
                    }
                    
                    response = client.post('/login', data=login_data, follow_redirects=False)
                    print(f"POST /login status: {response.status_code}")
                    
                    if response.status_code == 302:
                        print("✅ Login bem-sucedido!")
                        redirect = response.headers.get('Location', '')
                        print(f"Redirecionamento: {redirect}")
                    else:
                        print(f"❌ Login falhou: {response.status_code}")
                        print(f"Response: {response.data[:200]}")
                else:
                    print("❌ CSRF token não encontrado no HTML")
            else:
                print(f"❌ Erro ao acessar /login: {response.status_code}")

if __name__ == "__main__":
    debug_csrf_detailed()
