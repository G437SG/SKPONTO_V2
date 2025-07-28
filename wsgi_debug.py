#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuração específica para Render.com
"""

import os
import sys

# Print information for debugging
print("=== RENDER STARTUP DEBUG ===")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Working directory: {os.getcwd()}")
print(f"PORT env: {os.environ.get('PORT', 'NOT SET')}")
print(f"DATABASE_URL env: {os.environ.get('DATABASE_URL', 'NOT SET')[:60]}...")

# List all environment variables that start with specific prefixes
env_prefixes = ['FLASK_', 'DATABASE_', 'SECRET_', 'RENDER_']
for key, value in os.environ.items():
    for prefix in env_prefixes:
        if key.startswith(prefix):
            if 'SECRET' in key or 'PASSWORD' in key:
                print(f"{key}: [HIDDEN]")
            else:
                print(f"{key}: {value}")

# Import the application
try:
    print("Importing create_app...")
    from app import create_app
    print("✅ create_app imported successfully")
    
    print("Creating application...")
    application = create_app(os.getenv('FLASK_CONFIG') or 'production')
    print("✅ Application created successfully")
    
    print(f"App name: {application.name}")
    print(f"App config: {application.config['SQLALCHEMY_DATABASE_URI'][:60]}...")
    
    # For compatibility with different WSGI servers
    app = application
    
    print("=== RENDER STARTUP COMPLETE ===")
    
except Exception as e:
    print(f"❌ ERROR during startup: {str(e)}")
    import traceback
    traceback.print_exc()
    raise

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)
