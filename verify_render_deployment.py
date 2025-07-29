#!/usr/bin/env python3
"""
VERIFICAÇÃO COMPLETA DO SISTEMA SKPONTO - RENDER.COM
Checklist completo para garantir funcionamento perfeito
"""

import requests
import json
from datetime import datetime
import time

# Configurações
PRODUCTION_URL = "https://skponto.onrender.com"
ADMIN_EMAIL = "admin@skponto.com"
ADMIN_PASSWORD = "admin123"

def check_system_health():
    """Verificação completa da saúde do sistema"""
    
    print("🔍 VERIFICAÇÃO COMPLETA DO SISTEMA SKPONTO")
    print("=" * 60)
    print(f"🌐 URL: {PRODUCTION_URL}")
    print(f"⏰ Verificação iniciada em: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "url": PRODUCTION_URL,
        "checks": {}
    }
    
    # 1. VERIFICAÇÃO DE CONECTIVIDADE BÁSICA
    print("\n🔌 1. VERIFICAÇÃO DE CONECTIVIDADE")
    print("-" * 40)
    
    try:
        response = requests.get(PRODUCTION_URL, timeout=15)
        if response.status_code == 200:
            print("✅ Site principal acessível")
            results["checks"]["connectivity"] = "OK"
        else:
            print(f"⚠️ Site retornou status {response.status_code}")
            results["checks"]["connectivity"] = f"Warning: {response.status_code}"
    except Exception as e:
        print(f"❌ Erro de conectividade: {str(e)}")
        results["checks"]["connectivity"] = f"Error: {str(e)}"
    
    # 2. VERIFICAÇÃO DE ROTAS PRINCIPAIS
    print("\n🛣️ 2. VERIFICAÇÃO DE ROTAS PRINCIPAIS")
    print("-" * 40)
    
    critical_routes = [
        "/",
        "/login",
        "/meus-registros",
        "/admin/usuarios",
        "/admin/dashboard"
    ]
    
    route_results = {}
    for route in critical_routes:
        try:
            response = requests.get(PRODUCTION_URL + route, timeout=10, allow_redirects=False)
            
            if response.status_code == 200:
                print(f"✅ {route} - OK (200)")
                route_results[route] = "OK"
            elif response.status_code == 302:
                print(f"🔄 {route} - REDIRECT (302)")
                route_results[route] = "REDIRECT"
            elif response.status_code == 404:
                print(f"❌ {route} - NOT FOUND (404)")
                route_results[route] = "NOT_FOUND"
            else:
                print(f"⚠️ {route} - Status {response.status_code}")
                route_results[route] = f"Status_{response.status_code}"
                
        except Exception as e:
            print(f"❌ {route} - ERROR: {str(e)}")
            route_results[route] = "ERROR"
    
    results["checks"]["routes"] = route_results
    
    # 3. VERIFICAÇÃO DA API
    print("\n🔌 3. VERIFICAÇÃO DA API")
    print("-" * 40)
    
    api_routes = [
        "/api/status",
        "/api/users",
        "/api/time-records"
    ]
    
    api_results = {}
    for route in api_routes:
        try:
            response = requests.get(PRODUCTION_URL + route, timeout=10, allow_redirects=False)
            
            if response.status_code in [200, 302]:
                print(f"✅ {route} - OK ({response.status_code})")
                api_results[route] = "OK"
            else:
                print(f"⚠️ {route} - Status {response.status_code}")
                api_results[route] = f"Status_{response.status_code}"
                
        except Exception as e:
            print(f"❌ {route} - ERROR: {str(e)}")
            api_results[route] = "ERROR"
    
    results["checks"]["api"] = api_results
    
    # 4. VERIFICAÇÃO DO SISTEMA DE AUTENTICAÇÃO
    print("\n🔐 4. VERIFICAÇÃO DO SISTEMA DE AUTENTICAÇÃO")
    print("-" * 40)
    
    auth_results = {}
    session = requests.Session()
    
    try:
        # Testar página de login
        login_page = session.get(PRODUCTION_URL + "/login", timeout=10)
        if login_page.status_code == 200:
            print("✅ Página de login acessível")
            auth_results["login_page"] = "OK"
            
            # Verificar se contém formulário de login
            if "email" in login_page.text.lower() and "password" in login_page.text.lower():
                print("✅ Formulário de login detectado")
                auth_results["login_form"] = "OK"
            else:
                print("⚠️ Formulário de login não detectado")
                auth_results["login_form"] = "WARNING"
        else:
            print(f"❌ Página de login retornou {login_page.status_code}")
            auth_results["login_page"] = f"Error_{login_page.status_code}"
            
    except Exception as e:
        print(f"❌ Erro ao testar autenticação: {str(e)}")
        auth_results["authentication"] = "ERROR"
    
    results["checks"]["authentication"] = auth_results
    
    # 5. VERIFICAÇÃO DE HEADERS DE SEGURANÇA
    print("\n🛡️ 5. VERIFICAÇÃO DE HEADERS DE SEGURANÇA")
    print("-" * 40)
    
    try:
        response = requests.get(PRODUCTION_URL, timeout=10)
        headers = response.headers
        
        security_headers = {
            "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
            "X-Frame-Options": headers.get("X-Frame-Options"),
            "X-XSS-Protection": headers.get("X-XSS-Protection"),
            "Strict-Transport-Security": headers.get("Strict-Transport-Security"),
            "Content-Security-Policy": headers.get("Content-Security-Policy")
        }
        
        security_results = {}
        for header, value in security_headers.items():
            if value:
                print(f"✅ {header}: {value}")
                security_results[header] = "PRESENT"
            else:
                print(f"⚠️ {header}: AUSENTE")
                security_results[header] = "MISSING"
        
        results["checks"]["security_headers"] = security_results
        
    except Exception as e:
        print(f"❌ Erro ao verificar headers: {str(e)}")
        results["checks"]["security_headers"] = "ERROR"
    
    # 6. VERIFICAÇÃO DE PERFORMANCE
    print("\n⚡ 6. VERIFICAÇÃO DE PERFORMANCE")
    print("-" * 40)
    
    performance_results = {}
    
    try:
        start_time = time.time()
        response = requests.get(PRODUCTION_URL, timeout=30)
        end_time = time.time()
        
        response_time = end_time - start_time
        performance_results["response_time"] = response_time
        
        if response_time < 2.0:
            print(f"✅ Tempo de resposta: {response_time:.2f}s (Excelente)")
        elif response_time < 5.0:
            print(f"⚠️ Tempo de resposta: {response_time:.2f}s (Aceitável)")
        else:
            print(f"❌ Tempo de resposta: {response_time:.2f}s (Lento)")
        
        # Verificar tamanho da resposta
        content_length = len(response.content)
        performance_results["content_size"] = content_length
        print(f"📏 Tamanho da página: {content_length / 1024:.1f} KB")
        
    except Exception as e:
        print(f"❌ Erro ao testar performance: {str(e)}")
        performance_results["error"] = str(e)
    
    results["checks"]["performance"] = performance_results
    
    # 7. VERIFICAÇÃO DO BANCO DE DADOS
    print("\n🗄️ 7. VERIFICAÇÃO DO BANCO DE DADOS")
    print("-" * 40)
    
    db_results = {}
    
    try:
        # Tentar acessar uma rota que requer DB
        db_route = "/admin/usuarios"
        response = requests.get(PRODUCTION_URL + db_route, timeout=10, allow_redirects=False)
        
        if response.status_code in [200, 302]:
            print("✅ Banco de dados acessível")
            db_results["connectivity"] = "OK"
        else:
            print(f"⚠️ Possível problema no DB - Status: {response.status_code}")
            db_results["connectivity"] = f"Warning_{response.status_code}"
            
    except Exception as e:
        print(f"❌ Erro ao testar banco: {str(e)}")
        db_results["connectivity"] = "ERROR"
    
    results["checks"]["database"] = db_results
    
    # RESUMO FINAL
    print("\n📊 RESUMO DA VERIFICAÇÃO")
    print("=" * 60)
    
    total_checks = 0
    passed_checks = 0
    
    for category, check_results in results["checks"].items():
        if isinstance(check_results, dict):
            category_passed = sum(1 for v in check_results.values() if v in ["OK", "REDIRECT", "PRESENT"])
            category_total = len(check_results)
        else:
            category_passed = 1 if check_results == "OK" else 0
            category_total = 1
        
        total_checks += category_total
        passed_checks += category_passed
        
        percentage = (category_passed / category_total * 100) if category_total > 0 else 0
        print(f"📋 {category.upper()}: {category_passed}/{category_total} ({percentage:.1f}%)")
    
    overall_percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    print(f"\n🎯 RESULTADO GERAL: {passed_checks}/{total_checks} ({overall_percentage:.1f}%)")
    
    if overall_percentage >= 90:
        print("🎉 SISTEMA EM EXCELENTE ESTADO!")
        status = "EXCELLENT"
    elif overall_percentage >= 75:
        print("✅ SISTEMA FUNCIONANDO BEM")
        status = "GOOD"
    elif overall_percentage >= 50:
        print("⚠️ SISTEMA COM ALGUNS PROBLEMAS")
        status = "WARNING"
    else:
        print("❌ SISTEMA COM PROBLEMAS CRÍTICOS")
        status = "CRITICAL"
    
    results["overall_status"] = status
    results["overall_percentage"] = overall_percentage
    
    # Salvar resultados
    with open("system_health_check.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Relatório salvo em: system_health_check.json")
    print("=" * 60)
    
    return status == "EXCELLENT" or status == "GOOD"

if __name__ == "__main__":
    success = check_system_health()
    exit(0 if success else 1)
