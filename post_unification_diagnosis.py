#!/usr/bin/env python3
"""
🔍 DIAGNÓSTICO PÓS-UNIFICAÇÃO SKPONTO
====================================

Analisa o estado do sistema após a unificação e identifica
problemas específicos com as rotas que retornam erro 500.
"""

import requests
import json
from datetime import datetime
from pathlib import Path

class PostUnificationDiagnostics:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.logged_in = False
        self.error_routes = []
        self.missing_templates = []
        self.missing_routes = []
        
    def login(self):
        """Realiza login no sistema"""
        try:
            # Primeiro, acessar página de login para obter cookies
            login_page = self.session.get(f"{self.base_url}/login")
            
            # Dados de login
            login_data = {
                'email': 'admin@skponto.com',
                'password': 'admin123'
            }
            
            # Fazer login
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            
            if response.status_code == 200 and 'dashboard' in response.text.lower():
                self.logged_in = True
                print("✅ Login realizado com sucesso")
                return True
            else:
                print(f"❌ Erro no login: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao fazer login: {e}")
            return False
            
    def test_route_detailed(self, route, description):
        """Testa uma rota específica e analisa o erro"""
        try:
            response = self.session.get(f"{self.base_url}{route}", timeout=10)
            
            if response.status_code == 200:
                return {"status": "OK", "time": response.elapsed.total_seconds()}
            elif response.status_code == 500:
                # Analisar erro 500
                error_info = self.analyze_500_error(route, response)
                self.error_routes.append({
                    "route": route,
                    "description": description,
                    "error_info": error_info
                })
                return {"status": "ERROR_500", "error": error_info}
            else:
                return {"status": f"ERROR_{response.status_code}"}
                
        except Exception as e:
            return {"status": "EXCEPTION", "error": str(e)}
            
    def analyze_500_error(self, route, response):
        """Analisa detalhes do erro 500"""
        error_info = {
            "type": "unknown",
            "likely_cause": "unknown",
            "suggested_fix": "unknown"
        }
        
        # Analisar conteúdo da resposta para identificar tipo de erro
        try:
            content = response.text.lower()
            
            if 'templatenotfound' in content or 'template' in content:
                error_info["type"] = "template_missing"
                error_info["likely_cause"] = "Template removido durante unificação"
                error_info["suggested_fix"] = "Verificar se template foi movido ou removido"
                
            elif 'attributeerror' in content or 'module' in content:
                error_info["type"] = "import_error"
                error_info["likely_cause"] = "Arquivo/função removido durante unificação"
                error_info["suggested_fix"] = "Verificar imports e dependências"
                
            elif 'blueprint' in content:
                error_info["type"] = "blueprint_error"
                error_info["likely_cause"] = "Blueprint removido ou não registrado"
                error_info["suggested_fix"] = "Verificar registro de blueprints"
                
            elif 'database' in content or 'sqlalchemy' in content:
                error_info["type"] = "database_error"
                error_info["likely_cause"] = "Problema com modelo ou query"
                error_info["suggested_fix"] = "Verificar modelos de dados"
                
        except Exception:
            pass
            
        return error_info
        
    def check_critical_files(self):
        """Verifica se arquivos críticos ainda existem"""
        critical_files = {
            "app.py": "Arquivo principal da aplicação",
            "config.py": "Configurações principais",
            "app/main/routes.py": "Rotas principais",
            "app/admin/routes.py": "Rotas administrativas",
            "app/api/routes.py": "Rotas da API",
            "app/templates/main/dashboard.html": "Template dashboard principal",
            "app/templates/admin/dashboard.html": "Template dashboard admin",
            "app/templates/base.html": "Template base"
        }
        
        workspace = Path(r"c:\Users\Arq\OneDrive\Python Projetos\SKPONTO_V2")
        missing_files = []
        
        for file_path, description in critical_files.items():
            full_path = workspace / file_path
            if not full_path.exists():
                missing_files.append({
                    "file": file_path,
                    "description": description,
                    "status": "MISSING"
                })
            else:
                print(f"✅ {file_path} - OK")
                
        return missing_files
        
    def run_diagnosis(self):
        """Executa diagnóstico completo"""
        print("🔍 DIAGNÓSTICO PÓS-UNIFICAÇÃO SKPONTO")
        print("=" * 50)
        
        # 1. Verificar arquivos críticos
        print("\n📁 VERIFICANDO ARQUIVOS CRÍTICOS...")
        missing_files = self.check_critical_files()
        
        if missing_files:
            print(f"\n⚠️ {len(missing_files)} arquivos críticos faltando:")
            for file_info in missing_files:
                print(f"  ❌ {file_info['file']} - {file_info['description']}")
        else:
            print("✅ Todos os arquivos críticos estão presentes")
            
        # 2. Fazer login
        print("\n🔐 FAZENDO LOGIN...")
        if not self.login():
            print("❌ Não foi possível fazer login - diagnóstico limitado")
            return
            
        # 3. Testar rotas com erro identificadas
        print("\n🔍 TESTANDO ROTAS COM ERRO...")
        error_routes_to_test = [
            ("/", "Página inicial"),
            ("/dashboard", "Dashboard principal"),
            ("/admin/dashboard", "Dashboard administrativo"),
            ("/admin/usuarios", "Gestão de usuários"),
            ("/admin/atestados", "Atestados administrativos"),
            ("/admin/logs", "Logs do sistema"),
            ("/admin/notificacoes", "Notificações administrativas")
        ]
        
        for route, description in error_routes_to_test:
            print(f"  🔍 Testando {route}...")
            result = self.test_route_detailed(route, description)
            
            if result["status"] == "ERROR_500":
                print(f"    ❌ {description}: {result['error']['type']}")
            elif result["status"] == "OK":
                print(f"    ✅ {description}: OK")
            else:
                print(f"    ⚠️ {description}: {result['status']}")
                
        # 4. Gerar relatório
        print("\n📊 GERANDO RELATÓRIO...")
        report = {
            "timestamp": datetime.now().isoformat(),
            "missing_files": missing_files,
            "error_routes": self.error_routes,
            "summary": {
                "critical_files_missing": len(missing_files),
                "routes_with_errors": len(self.error_routes),
                "login_status": "OK" if self.logged_in else "FAILED"
            }
        }
        
        # Salvar relatório
        with open("post_unification_diagnosis.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # 5. Análise de padrões de erro
        print("\n🎯 ANÁLISE DE PADRÕES DE ERRO:")
        if self.error_routes:
            error_types = {}
            for error in self.error_routes:
                error_type = error["error_info"]["type"]
                if error_type not in error_types:
                    error_types[error_type] = []
                error_types[error_type].append(error["route"])
                
            for error_type, routes in error_types.items():
                print(f"  🔴 {error_type}: {len(routes)} rotas")
                for route in routes:
                    print(f"    • {route}")
                    
        # 6. Recomendações
        print("\n💡 RECOMENDAÇÕES:")
        if missing_files:
            print("  🔧 Verificar arquivos removidos durante unificação")
            print("  📋 Restaurar templates críticos do backup")
            
        if self.error_routes:
            template_errors = [e for e in self.error_routes if e["error_info"]["type"] == "template_missing"]
            if template_errors:
                print("  🎨 Verificar templates removidos:")
                for error in template_errors:
                    print(f"    • {error['route']}")
                    
        print(f"\n📄 Relatório salvo em: post_unification_diagnosis.json")
        return report

if __name__ == "__main__":
    diagnostics = PostUnificationDiagnostics()
    report = diagnostics.run_diagnosis()
    
    print("\n✅ Diagnóstico concluído!")
    if report["summary"]["routes_with_errors"] > 0:
        print("⚠️ Problemas identificados - verificar relatório para correções")
