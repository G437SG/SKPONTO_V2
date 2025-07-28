#!/usr/bin/env python3
"""
Script para inicializar o banco de dados no Render
"""

import os
import sys
from app import create_app, db

def init_database():
    """Inicializa o banco de dados"""
    
    # Configurar variável de ambiente
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FLASK_CONFIG'] = 'production'
    
    # Criar aplicação
    app = create_app('production')
    
    with app.app_context():
        try:
            # Criar todas as tabelas
            db.create_all()
            print("✅ Banco de dados inicializado com sucesso!")
            
            # Verificar se há tabelas
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📊 Tabelas criadas: {len(tables)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao inicializar banco: {e}")
            return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
