#!/usr/bin/env python3
"""
Debug específico para as rotas que não estão funcionando
"""

import os
import sys
import requests
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurações
BASE_URL = "http://localhost:5000"
USERNAME = "admin@skponto.com"
PASSWORD = "admin123"

def test_single_route(route_name):
    """Testar uma rota específica e capturar o erro detalhado"""
    print(f"\n🔍 TESTANDO ROTA: {route_name}")
    
    session = requests.Session()
    
    # Fazer login primeiro
    login_data = {
        'email': USERNAME,
        'password': PASSWORD
    }
    
    try:
        # Login
        login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        print(f"  🔐 Login Status: {login_response.status_code}")
        
        # Testar a rota
        response = session.get(f"{BASE_URL}{route_name}", timeout=10)
        
        print(f"  📄 Response Status: {response.status_code}")
        print(f"  📄 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 500:
            print(f"  ❌ ERRO 500 - Conteúdo da resposta:")
            print(f"  {response.text[:500]}...")
        elif response.status_code == 200:
            print(f"  ✅ SUCESSO - Tamanho da resposta: {len(response.text)} chars")
        else:
            print(f"  ⚠️ Status inesperado: {response.status_code}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"  ❌ ERRO DE CONEXÃO: {str(e)}")
        return False

def main():
    print("🐛 DEBUG ESPECÍFICO DE ROTAS...")
    
    # Rotas problemáticas para debug
    routes_to_debug = [
        "/",
        "/dashboard",
        "/admin/usuarios",
        "/admin/system-config"
    ]
    
    for route in routes_to_debug:
        success = test_single_route(route)
        if success:
            print(f"  ✅ {route} está funcionando!")
        else:
            print(f"  ❌ {route} ainda tem problemas")

if __name__ == "__main__":
    main()
