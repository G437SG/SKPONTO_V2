#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point para produção
"""

import os

# Configurar psycopg3 para PostgreSQL no Render
def configure_psycopg3():
    """Configura psycopg3 para usar com PostgreSQL"""
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgresql://'):
        if '+psycopg' not in database_url:
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
            os.environ['DATABASE_URL'] = database_url
            print(f"🔧 WSGI: Configurado psycopg3 - {database_url}")

# Configurar antes de importar a aplicação
configure_psycopg3()

from app import create_app

# Criar a aplicação Flask
application = create_app(os.getenv('FLASK_CONFIG') or 'production')

# Para compatibilidade com diferentes servidores WSGI
app = application

if __name__ == "__main__":
    application.run()
