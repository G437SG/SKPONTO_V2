#!/usr/bin/env python3
"""
Verificação detalhada das páginas com erro
"""

import requests
import time

class PageErrorAnalyzer:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.login()
        
    def login(self):
        """Faz login no sistema"""
        print("🔐 FAZENDO LOGIN...")
        login_data = {
            'email': 'admin@skponto.com',
            'password': 'admin123'
        }
        
        response = self.session.post(f"{self.base_url}/login", data=login_data)
        if 'admin/dashboard' in response.url:
            print("✅ LOGIN REALIZADO COM SUCESSO!")
            return True
        return False
    
    def analyze_page(self, url, expected_name):
        """Analisa uma página específica em detalhes"""
        print(f"\n🔍 ANALISANDO: {expected_name}")
        print(f"📍 URL: {url}")
        
        try:
            response = self.session.get(f"{self.base_url}{url}")
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 404:
                print("❌ PÁGINA NÃO ENCONTRADA (404)")
                print("🔍 Verificando se existe rota similar...")
                return self.suggest_alternative_route(url, expected_name)
            
            elif response.status_code == 500:
                print("❌ ERRO INTERNO DO SERVIDOR (500)")
                print("📄 Primeiros 300 caracteres da resposta:")
                print(response.text[:300])
                return False
                
            elif response.status_code == 200:
                print("✅ PÁGINA CARREGOU COM SUCESSO!")
                return True
                
            else:
                print(f"⚠️ STATUS INESPERADO: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ ERRO NA REQUISIÇÃO: {e}")
            return False
    
    def suggest_alternative_route(self, original_url, expected_name):
        """Sugere rotas alternativas baseadas no que existe"""
        print("🔄 BUSCANDO ROTAS ALTERNATIVAS...")
        
        # Mapeamento de URLs incorretas para corretas
        route_corrections = {
            '/': '/dashboard',  # Página inicial pode estar em /dashboard
            '/admin/users': '/admin/usuarios',
            '/admin/time_records': '/admin/registros-ponto',
            '/admin/reports': '/admin/relatorios',
            '/admin/attestations': '/admin/atestados',
            '/admin/hour_bank': '/admin/hour-bank',
            '/admin/overtime': '/admin/overtime-control',
            '/admin/settings': '/admin/system-config',
            '/time/register': '/ponto',
            '/time/history': '/meus_registros',
            '/profile': '/perfil',
            '/attestations': '/atestados',
            '/hour_bank': '/my-hour-bank',
            '/reports/personal': '/meus_registros'
        }
        
        if original_url in route_corrections:
            alternative_url = route_corrections[original_url]
            print(f"💡 TESTANDO ROTA ALTERNATIVA: {alternative_url}")
            
            try:
                response = self.session.get(f"{self.base_url}{alternative_url}")
                if response.status_code == 200:
                    print(f"✅ ROTA CORRETA ENCONTRADA: {alternative_url}")
                    return alternative_url
                else:
                    print(f"❌ Rota alternativa também falhou: {response.status_code}")
            except Exception as e:
                print(f"❌ Erro na rota alternativa: {e}")
        
        return False
    
    def comprehensive_check(self):
        """Verifica todas as páginas com erro"""
        print("🚀 VERIFICAÇÃO COMPLETA DAS PÁGINAS COM ERRO")
        print("=" * 70)
        
        # Páginas reportadas com erro
        error_pages = [
            ('/', 'Página inicial'),
            ('/admin/users', 'Gestão de Usuários'),
            ('/admin/time_records', 'Registros de Ponto'),
            ('/admin/reports', 'Relatórios'),
            ('/admin/attestations', 'Atestados Médicos'),
            ('/admin/hour_bank', 'Banco de Horas'),
            ('/admin/overtime', 'Horas Extras'),
            ('/admin/settings', 'Configurações'),
            ('/time/register', 'Registro de Ponto'),
            ('/time/history', 'Histórico de Pontos'),
            ('/profile', 'Perfil do Usuário'),
            ('/attestations', 'Meus Atestados'),
            ('/hour_bank', 'Meu Banco de Horas'),
            ('/reports/personal', 'Relatórios Pessoais')
        ]
        
        results = {
            'fixed': [],
            'still_broken': [],
            'alternative_found': []
        }
        
        for url, name in error_pages:
            result = self.analyze_page(url, name)
            
            if result is True:
                results['fixed'].append((url, name))
            elif isinstance(result, str):  # Rota alternativa encontrada
                results['alternative_found'].append((url, name, result))
            else:
                results['still_broken'].append((url, name))
            
            time.sleep(0.1)  # Pausa entre requisições
        
        self.print_summary(results)
        return results
    
    def print_summary(self, results):
        """Imprime resumo dos resultados"""
        print("\n" + "=" * 70)
        print("📊 RESUMO DA VERIFICAÇÃO")
        print("=" * 70)
        
        if results['fixed']:
            print(f"\n✅ PÁGINAS CORRIGIDAS ({len(results['fixed'])}):")
            for url, name in results['fixed']:
                print(f"  • {url} - {name}")
        
        if results['alternative_found']:
            print(f"\n🔄 ROTAS ALTERNATIVAS ENCONTRADAS ({len(results['alternative_found'])}):")
            for original, name, correct in results['alternative_found']:
                print(f"  • {original} ➜ {correct} - {name}")
        
        if results['still_broken']:
            print(f"\n❌ PÁGINAS AINDA COM PROBLEMA ({len(results['still_broken'])}):")
            for url, name in results['still_broken']:
                print(f"  • {url} - {name}")
        
        total_checked = len(results['fixed']) + len(results['alternative_found']) + len(results['still_broken'])
        working = len(results['fixed']) + len(results['alternative_found'])
        
        if total_checked > 0:
            success_rate = (working / total_checked) * 100
            print(f"\n📈 TAXA DE CORREÇÃO: {success_rate:.1f}% ({working}/{total_checked})")

if __name__ == "__main__":
    analyzer = PageErrorAnalyzer()
    results = analyzer.comprehensive_check()
    
    print(f"\n🎯 PRÓXIMOS PASSOS:")
    
    if results['alternative_found']:
        print("1. 📝 Atualizar links/menus para usar as rotas corretas")
        print("2. 🔄 Implementar redirects das URLs antigas para as novas")
    
    if results['still_broken']:
        print("3. 🔧 Investigar erros 500 nas páginas restantes")
        print("4. 📋 Verificar logs do servidor para detalhes dos erros")
    
    print("5. ✅ Testar novamente após correções")
