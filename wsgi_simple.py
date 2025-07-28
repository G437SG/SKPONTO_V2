#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI Simples para Render.com - Mínimo Viável
"""

import os
import sys

print("🚀 WSGI SIMPLES INICIANDO...")
print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")

try:
    # Set config primeiro
    os.environ.setdefault('FLASK_CONFIG', 'production')
    print(f"✅ FLASK_CONFIG definido: {os.environ.get('FLASK_CONFIG')}")
    
    # Import básico
    from app import create_app
    print("✅ create_app importado")
    
    # Criar app
    application = create_app('production')
    print("✅ Application criada")
    
    # Para compatibilidade
    app = application
    
    print("🎉 WSGI configurado com sucesso!")
    
except Exception as e:
    print(f"❌ ERRO CRÍTICO: {str(e)}")
    import traceback
    traceback.print_exc()
    raise

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"🏃 Executando na porta: {port}")
    application.run(host='0.0.0.0', port=port, debug=False)
