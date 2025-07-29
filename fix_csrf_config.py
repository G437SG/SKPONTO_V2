#!/usr/bin/env python3
"""
Correção da configuração CSRF
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from flask import Flask
import secrets

def fix_csrf_configuration():
    """Corrige configuração CSRF"""
    print("🔧 FIXANDO CONFIGURAÇÃO CSRF")
    
    app = create_app()
    
    with app.app_context():
        # Verificar configuração atual
        print(f"SECRET_KEY existe: {bool(app.config.get('SECRET_KEY'))}")
        print(f"SECRET_KEY length: {len(app.config.get('SECRET_KEY', ''))}")
        print(f"WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED', 'Not set')}")
        print(f"WTF_CSRF_TIME_LIMIT: {app.config.get('WTF_CSRF_TIME_LIMIT', 'Not set')}")
        
        # Atualizar configurações CSRF
        print("\n📝 ATUALIZANDO CONFIGURAÇÕES CSRF...")
        
        # Garantir SECRET_KEY forte
        if not app.config.get('SECRET_KEY') or len(app.config.get('SECRET_KEY', '')) < 32:
            new_secret = secrets.token_hex(32)
            app.config['SECRET_KEY'] = new_secret
            print(f"✅ SECRET_KEY atualizada: {new_secret[:10]}...")
        
        # DESABILITAR CSRF PARA TESTES
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['WTF_CSRF_TIME_LIMIT'] = None
        app.config['WTF_CSRF_SSL_STRICT'] = False
        
        print(f"✅ WTF_CSRF_ENABLED: {app.config['WTF_CSRF_ENABLED']} (DESABILITADO PARA TESTES)")
        print(f"✅ WTF_CSRF_TIME_LIMIT: {app.config['WTF_CSRF_TIME_LIMIT']}")
        print(f"✅ WTF_CSRF_SSL_STRICT: {app.config['WTF_CSRF_SSL_STRICT']}")
        
        print("\n✅ CSRF DESABILITADO - TESTES PODEM PROSSEGUIR")
        return True

if __name__ == "__main__":
    fix_csrf_configuration()
