#!/usr/bin/env python3
"""
Script para verificar se todas as páginas estão funcionando corretamente
Testa não apenas o status HTTP, mas também se os templates estão sendo renderizados
"""

import requests
import time
from urllib.parse import urljoin

# Configuração do servidor
BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 15

def test_page_detailed(url, method='GET', data=None, description=""):
    """Testa uma página detalhadamente"""
    try:
        if method == 'GET':
            response = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        elif method == 'POST':
            response = requests.post(url, data=data, timeout=TIMEOUT, allow_redirects=True)
        
        status = response.status_code
        content = response.text
        content_length = len(content)
        
        # Verificar se é uma resposta válida
        if status == 200:
            # Verificar se tem conteúdo HTML válido ou JSON válido
            if content_length < 50:
                return False, status, f"❌ Conteúdo muito pequeno ({content_length} chars)"
            elif content.strip().startswith('{') and content.strip().endswith('}'):
                # É JSON (como API status)
                return True, status, f"✅ OK - JSON válido ({content_length} chars)"
            elif "<!DOCTYPE html>" not in content and "<html" not in content:
                return False, status, f"❌ Não é HTML válido"
            elif "Internal Server Error" in content:
                return False, status, f"❌ Erro interno no conteúdo"
            elif "Template não encontrado" in content or "TemplateNotFound" in content:
                return False, status, f"❌ Template não encontrado"
            else:
                return True, status, f"✅ OK - HTML válido ({content_length} chars)"
        
        elif status in [302, 301]:
            location = response.history[0].headers.get('Location', 'N/A') if response.history else 'N/A'
            return True, status, f"✅ Redirecionamento para: {location}"
        
        elif status == 404:
            return False, status, "❌ Página não encontrada"
        elif status == 403:
            return False, status, "❌ Acesso negado"
        elif status == 500:
            return False, status, "❌ Erro interno do servidor"
        else:
            return False, status, f"❌ Status HTTP {status}"
            
    except requests.exceptions.ConnectionError:
        return False, 0, "❌ Servidor não conectado"
    except requests.exceptions.Timeout:
        return False, 0, "❌ Timeout"
    except Exception as e:
        return False, 0, f"❌ Erro: {str(e)[:50]}"

def main():
    print("🔍 VERIFICAÇÃO DETALHADA DE TODAS AS PÁGINAS")
    print("=" * 70)
    
    # Lista completa de páginas para testar
    pages = [
        # Páginas públicas
        ("/", "GET", "Página inicial"),
        ("/login", "GET", "Login"),
        ("/register", "GET", "Registro"),
        
        # Páginas que requerem autenticação (vão redirecionar para login)
        ("/dashboard", "GET", "Dashboard principal"),
        ("/profile", "GET", "Perfil do usuário"),
        ("/settings", "GET", "Configurações"),
        ("/notifications", "GET", "Notificações"),
        ("/overtime", "GET", "Horas extras"),
        ("/attestations", "GET", "Atestados"),
        ("/upload-attestation", "GET", "Upload de atestado"),
        
        # Relatórios
        ("/reports", "GET", "Relatórios"),
        ("/reports/monthly", "GET", "Relatório mensal"),
        ("/reports/attendance", "GET", "Relatório de presença"),
        
        # Admin (vão redirecionar para login)
        ("/admin", "GET", "Painel admin"),
        ("/admin/users", "GET", "Usuários admin"),
        ("/admin/system", "GET", "Sistema admin"),
        ("/admin/reports", "GET", "Relatórios admin"),
        
        # API endpoints
        ("/api/status", "GET", "Status da API"),
        
        # Páginas de erro e recovery
        ("/forgot-password", "GET", "Esqueci a senha"),
        
        # Exports (vão redirecionar)
        ("/export/pdf", "GET", "Export PDF"),
        ("/export/excel", "GET", "Export Excel"),
    ]
    
    success_count = 0
    total_count = len(pages)
    results = []
    
    print(f"🧪 Testando {total_count} páginas...\n")
    
    for route, method, description in pages:
        url = urljoin(BASE_URL, route)
        success, status, message = test_page_detailed(url, method, description=description)
        
        results.append({
            'route': route,
            'method': method,
            'description': description,
            'success': success,
            'status': status,
            'message': message
        })
        
        if success:
            success_count += 1
        
        print(f"{message} [{status}] {method} {route} - {description}")
        time.sleep(0.2)  # Pausa entre requests
    
    print("\n" + "=" * 70)
    print("📊 RESULTADO DA VERIFICAÇÃO:")
    print(f"✅ Páginas funcionando: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    print(f"❌ Páginas com problemas: {total_count - success_count}/{total_count}")
    
    # Páginas com problemas
    failed_pages = [r for r in results if not r['success']]
    if failed_pages:
        print(f"\n🚨 PÁGINAS COM PROBLEMAS ({len(failed_pages)}):")
        for page in failed_pages:
            print(f"   {page['message']} [{page['status']}] {page['route']}")
    
    # Páginas funcionando
    working_pages = [r for r in results if r['success']]
    if working_pages:
        print(f"\n✅ PÁGINAS FUNCIONANDO ({len(working_pages)}):")
        for page in working_pages:
            print(f"   ✅ [{page['status']}] {page['route']} - {page['description']}")
    
    print("\n🎯 AVALIAÇÃO GERAL:")
    if success_count == total_count:
        print("   🚀 PERFEITO! Todas as páginas estão funcionando!")
        print("   🎉 Sistema 100% operacional!")
    elif success_count >= total_count * 0.9:
        print("   👍 EXCELENTE! Quase todas as páginas funcionando!")
        print("   🔧 Apenas pequenos ajustes necessários")
    elif success_count >= total_count * 0.7:
        print("   ⚠️ BOM! Maioria das páginas funcionando")
        print("   🛠️ Algumas correções necessárias")
    else:
        print("   🚨 ATENÇÃO! Muitas páginas com problemas")
        print("   🔨 Revisão geral necessária")
    
    # Teste adicional - verificar se templates base existem
    print(f"\n🔍 VERIFICAÇÃO DE TEMPLATES BASE:")
    base_templates = [
        "app/templates/base.html",
        "app/templates/auth/login.html", 
        "app/templates/main/dashboard.html",
        "app/templates/admin/dashboard.html"
    ]
    
    import os
    for template in base_templates:
        if os.path.exists(template):
            print(f"   ✅ {template}")
        else:
            print(f"   ❌ {template} - NÃO ENCONTRADO")

if __name__ == "__main__":
    main()
