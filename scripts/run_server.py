#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entry point específico para o Render
"""

import os
import sys
from pathlib import Path

# Configurar o path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Configurar variáveis de ambiente
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('FLASK_CONFIG', 'production')

# Importar e criar a aplicação
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
