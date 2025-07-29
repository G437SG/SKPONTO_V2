#!/usr/bin/env python3
"""
VERIFICAÇÃO COMPLETA - SKPONTO NO RENDER.COM
Checklist completo para garantir funcionamento perfeito
"""

import requests
import json
from datetime import datetime

def verificar_sistema():
    print("🔍 VERIFICAÇÃO COMPLETA - SKPONTO NO RENDER.COM")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    base_url = "https://skponto.onrender.com"
    resultados = {"total": 0, "sucesso": 0, "problemas": []}
    
    # 1. CONECTIVIDADE BÁSICA
    print("\n📡 1. TESTE DE CONECTIVIDADE BÁSICA")
    print("-" * 40)
    
    try:
        response = requests.get(base_url, timeout=15)
        tempo = response.elapsed.total_seconds()
        resultados["total"] += 1
        
        if response.status_code == 200:
            print(f"✅ Site principal: OK ({tempo:.2f}s)")
            resultados["sucesso"] += 1
        else:
            print(f"⚠️ Site principal: Status {response.status_code}")
            resultados["problemas"].append(f"Site principal: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro de conectividade: {e}")
        resultados["problemas"].append(f"Conectividade: {e}")
        resultados["total"] += 1
    
    # 2. ROTAS PRINCIPAIS
    print("\n🛣️ 2. TESTE DAS ROTAS PRINCIPAIS")
    print("-" * 40)
    
    rotas_principais = [
        ("/", "Página inicial", [200]),
        ("/login", "Login", [200]),
        ("/admin/usuarios", "Dashboard usuários", [200, 302]),
        ("/admin/dashboard", "Dashboard admin", [200, 302]),
        ("/meus-registros", "Meus registros", [200, 302]),
        ("/meus_registros", "Meus registros (alt)", [200, 302])
    ]
    
    for rota, desc, status_ok in rotas_principais:
        try:
            resp = requests.get(base_url + rota, timeout=10, allow_redirects=False)
            resultados["total"] += 1
            
            if resp.status_code in status_ok:
                icon = "✅" if resp.status_code == 200 else "🔄"
                print(f"{icon} {rota} ({desc}): {resp.status_code}")
                resultados["sucesso"] += 1
            else:
                print(f"❌ {rota} ({desc}): {resp.status_code}")
                resultados["problemas"].append(f"{rota}: {resp.status_code}")
                
        except Exception as e:
            print(f"❌ {rota}: Erro de conexão")
            resultados["problemas"].append(f"{rota}: Erro de conexão")
            resultados["total"] += 1
    
    # 3. APIs
    print("\n🔌 3. TESTE DAS APIs")
    print("-" * 40)
    
    apis = [
        ("/api/status", "API Status", [200]),
        ("/api/users", "API Users", [200, 302]),
        ("/api/time-records", "API Time Records", [200, 302])
    ]
    
    for api, desc, status_ok in apis:
        try:
            resp = requests.get(base_url + api, timeout=10, allow_redirects=False)
            resultados["total"] += 1
            
            if resp.status_code in status_ok:
                icon = "✅" if resp.status_code == 200 else "🔄"
                print(f"{icon} {api} ({desc}): {resp.status_code}")
                resultados["sucesso"] += 1
            else:
                print(f"❌ {api} ({desc}): {resp.status_code}")
                resultados["problemas"].append(f"{api}: {resp.status_code}")
                
        except Exception as e:
            print(f"❌ {api}: Erro de conexão")
            resultados["problemas"].append(f"{api}: Erro de conexão")
            resultados["total"] += 1
    
    # 4. TESTE DE AUTENTICAÇÃO
    print("\n🔐 4. TESTE DE AUTENTICAÇÃO")
    print("-" * 40)
    
    session = requests.Session()
    try:
        login_page = session.get(base_url + "/login", timeout=10)
        resultados["total"] += 1
        
        if login_page.status_code == 200:
            print("✅ Página de login: Acessível")
            resultados["sucesso"] += 1
            
            # Verificar se tem formulário
            if "login" in login_page.text.lower() and "password" in login_page.text.lower():
                print("✅ Formulário de login: Detectado")
            else:
                print("⚠️ Formulário de login: Pode estar incorreto")
        else:
            print(f"❌ Página de login: {login_page.status_code}")
            resultados["problemas"].append(f"Login page: {login_page.status_code}")
            
    except Exception as e:
        print(f"❌ Erro no teste de login: {e}")
        resultados["problemas"].append(f"Login test: {e}")
        resultados["total"] += 1
    
    # 5. VERIFICAÇÃO DE ARQUIVOS ESSENCIAIS
    print("\n📁 5. VERIFICAÇÃO DE CONFIGURAÇÃO")
    print("-" * 40)
    
    # Verificar se arquivos importantes existem
    import os
    arquivos_essenciais = [
        "requirements.txt",
        "Procfile",
        "runtime.txt",
        "wsgi_simple.py",
        "app.py",
        "config.py"
    ]
    
    for arquivo in arquivos_essenciais:
        if os.path.exists(arquivo):
            print(f"✅ {arquivo}: Existe")
        else:
            print(f"❌ {arquivo}: Não encontrado")
            resultados["problemas"].append(f"Arquivo {arquivo}: Não encontrado")
    
    # RESUMO FINAL
    print("\n" + "=" * 60)
    print("📊 RESUMO DA VERIFICAÇÃO")
    print("=" * 60)
    
    taxa_sucesso = (resultados["sucesso"] / resultados["total"] * 100) if resultados["total"] > 0 else 0
    
    print(f"✅ Testes bem-sucedidos: {resultados['sucesso']}/{resultados['total']} ({taxa_sucesso:.1f}%)")
    
    if resultados["problemas"]:
        print(f"\n⚠️ PROBLEMAS ENCONTRADOS ({len(resultados['problemas'])}):")
        for problema in resultados["problemas"]:
            print(f"  • {problema}")
    else:
        print("\n🎉 NENHUM PROBLEMA ENCONTRADO!")
    
    # Status geral
    if taxa_sucesso >= 90:
        print(f"\n🎯 STATUS GERAL: ✅ EXCELENTE - Sistema funcionando perfeitamente!")
    elif taxa_sucesso >= 80:
        print(f"\n🎯 STATUS GERAL: ✅ BOM - Sistema funcionando com pequenos detalhes")
    elif taxa_sucesso >= 70:
        print(f"\n🎯 STATUS GERAL: ⚠️ ACEITÁVEL - Sistema funcionando com alguns problemas")
    else:
        print(f"\n🎯 STATUS GERAL: ❌ CRÍTICO - Sistema com problemas sérios")
    
    print("\n🔗 URL do sistema: https://skponto.onrender.com")
    print("🔑 Login admin: admin@skponto.com / admin123")
    print("=" * 60)
    
    return taxa_sucesso >= 80

if __name__ == "__main__":
    sucesso = verificar_sistema()
    exit(0 if sucesso else 1)
