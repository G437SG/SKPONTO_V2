#!/usr/bin/env python3
"""
Análise completa do sistema SKPONTO para identificar duplicações
"""

import os
import re
import json
from pathlib import Path

class SystemAnalyzer:
    def __init__(self):
        self.project_root = Path('.')
        self.duplicates = {
            'files': [],
            'routes': [],
            'functions': [],
            'templates': [],
            'configs': []
        }
        self.analysis_results = {}
        
    def scan_files_by_pattern(self):
        """Escaneia arquivos por padrões similares"""
        print("🔍 ESCANEANDO ARQUIVOS POR PADRÕES...")
        
        patterns = {
            'test_files': r'test.*\.py$',
            'debug_files': r'debug.*\.py$',
            'check_files': r'check.*\.py$',
            'fix_files': r'fix.*\.py$',
            'backup_files': r'.*backup.*\.py$',
            'overtime_files': r'.*overtime.*\.py$',
            'user_files': r'.*user.*\.py$',
            'auth_files': r'.*auth.*\.py$',
            'config_files': r'config.*\.py$',
            'app_files': r'app.*\.py$'
        }
        
        file_groups = {}
        
        for pattern_name, pattern in patterns.items():
            matching_files = []
            for file_path in self.project_root.rglob('*.py'):
                if re.search(pattern, file_path.name, re.IGNORECASE):
                    matching_files.append(str(file_path))
            
            if matching_files:
                file_groups[pattern_name] = matching_files
                print(f"  📂 {pattern_name}: {len(matching_files)} arquivos")
        
        return file_groups
    
    def analyze_route_definitions(self):
        """Analisa definições de rotas no sistema"""
        print("\n🌐 ANALISANDO DEFINIÇÕES DE ROTAS...")
        
        route_files = []
        routes_found = {}
        
        # Buscar arquivos que podem conter rotas
        for file_path in self.project_root.rglob('*.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Buscar decoradores @app.route ou @blueprint.route
                route_patterns = [
                    r'@\w*\.route\([\'\"](.*?)[\'\"]',
                    r'@route\([\'\"](.*?)[\'\"]',
                    r'app\.route\([\'\"](.*?)[\'\"]'
                ]
                
                file_routes = []
                for pattern in route_patterns:
                    matches = re.findall(pattern, content)
                    file_routes.extend(matches)
                
                if file_routes:
                    route_files.append(str(file_path))
                    routes_found[str(file_path)] = file_routes
                    
            except Exception as e:
                continue
        
        print(f"  📄 {len(route_files)} arquivos com rotas encontrados")
        
        # Identificar rotas duplicadas
        all_routes = {}
        for file_path, routes in routes_found.items():
            for route in routes:
                if route not in all_routes:
                    all_routes[route] = []
                all_routes[route].append(file_path)
        
        duplicate_routes = {route: files for route, files in all_routes.items() if len(files) > 1}
        
        if duplicate_routes:
            print(f"  ⚠️  {len(duplicate_routes)} rotas duplicadas encontradas")
            for route, files in duplicate_routes.items():
                print(f"    • {route}: {len(files)} arquivos")
        
        return routes_found, duplicate_routes
    
    def analyze_function_definitions(self):
        """Analisa definições de funções similares"""
        print("\n⚙️ ANALISANDO FUNÇÕES SIMILARES...")
        
        function_patterns = {
            'login_functions': r'def.*login.*\(',
            'test_functions': r'def.*test.*\(',
            'check_functions': r'def.*check.*\(',
            'create_functions': r'def.*create.*\(',
            'update_functions': r'def.*update.*\(',
            'delete_functions': r'def.*delete.*\(',
            'backup_functions': r'def.*backup.*\(',
            'overtime_functions': r'def.*overtime.*\(',
        }
        
        function_groups = {}
        
        for pattern_name, pattern in function_patterns.items():
            functions_found = {}
            
            for file_path in self.project_root.rglob('*.py'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            functions_found[str(file_path)] = matches
                except:
                    continue
            
            if functions_found:
                function_groups[pattern_name] = functions_found
                total_functions = sum(len(funcs) for funcs in functions_found.values())
                print(f"  🔧 {pattern_name}: {total_functions} funções em {len(functions_found)} arquivos")
        
        return function_groups
    
    def analyze_template_files(self):
        """Analisa arquivos de template duplicados"""
        print("\n🎨 ANALISANDO TEMPLATES...")
        
        template_files = {}
        template_dirs = ['templates', 'app/templates']
        
        for template_dir in template_dirs:
            template_path = self.project_root / template_dir
            if template_path.exists():
                for file_path in template_path.rglob('*.html'):
                    template_name = file_path.name
                    if template_name not in template_files:
                        template_files[template_name] = []
                    template_files[template_name].append(str(file_path))
        
        duplicate_templates = {name: paths for name, paths in template_files.items() if len(paths) > 1}
        
        if duplicate_templates:
            print(f"  ⚠️  {len(duplicate_templates)} templates duplicados encontrados")
            for template, paths in duplicate_templates.items():
                print(f"    • {template}: {len(paths)} arquivos")
        
        return template_files, duplicate_templates
    
    def analyze_config_files(self):
        """Analisa arquivos de configuração"""
        print("\n⚙️ ANALISANDO CONFIGURAÇÕES...")
        
        config_patterns = [
            'config.py', 'settings.py', 'configuration.py',
            '.env', '.env.example', 'requirements.txt'
        ]
        
        config_files = {}
        
        for pattern in config_patterns:
            matching_files = list(self.project_root.rglob(pattern))
            if matching_files:
                config_files[pattern] = [str(f) for f in matching_files]
                if len(matching_files) > 1:
                    print(f"  ⚠️  {pattern}: {len(matching_files)} arquivos encontrados")
                else:
                    print(f"  ✅ {pattern}: 1 arquivo")
        
        return config_files
    
    def identify_test_file_duplicates(self):
        """Identifica arquivos de teste duplicados"""
        print("\n🧪 ANALISANDO ARQUIVOS DE TESTE...")
        
        test_files = list(self.project_root.glob('test*.py'))
        
        # Agrupar por funcionalidade
        test_groups = {
            'login_tests': [],
            'user_tests': [],
            'overtime_tests': [],
            'general_tests': [],
            'debug_tests': []
        }
        
        for test_file in test_files:
            file_name = test_file.name.lower()
            
            if 'login' in file_name:
                test_groups['login_tests'].append(str(test_file))
            elif 'user' in file_name:
                test_groups['user_tests'].append(str(test_file))
            elif 'overtime' in file_name:
                test_groups['overtime_tests'].append(str(test_file))
            elif 'debug' in file_name:
                test_groups['debug_tests'].append(str(test_file))
            else:
                test_groups['general_tests'].append(str(test_file))
        
        for group_name, files in test_groups.items():
            if files:
                print(f"  📊 {group_name}: {len(files)} arquivos")
                if len(files) > 3:  # Muitos arquivos similares
                    print(f"    ⚠️  Possível duplicação em {group_name}")
        
        return test_groups
    
    def check_file_sizes_and_dates(self, file_list):
        """Verifica tamanhos e datas dos arquivos"""
        file_info = {}
        
        for file_path in file_list:
            try:
                path = Path(file_path)
                if path.exists():
                    stat = path.stat()
                    file_info[file_path] = {
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'lines': self.count_lines(path)
                    }
            except:
                continue
        
        return file_info
    
    def count_lines(self, file_path):
        """Conta linhas de um arquivo"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except:
            return 0
    
    def run_complete_analysis(self):
        """Executa análise completa do sistema"""
        print("🚀 ANÁLISE COMPLETA DO SISTEMA SKPONTO")
        print("=" * 60)
        
        # 1. Escanear arquivos por padrões
        file_groups = self.scan_files_by_pattern()
        
        # 2. Analisar rotas
        routes_found, duplicate_routes = self.analyze_route_definitions()
        
        # 3. Analisar funções
        function_groups = self.analyze_function_definitions()
        
        # 4. Analisar templates
        template_files, duplicate_templates = self.analyze_template_files()
        
        # 5. Analisar configurações
        config_files = self.analyze_config_files()
        
        # 6. Analisar testes
        test_groups = self.identify_test_file_duplicates()
        
        # Compilar resultados
        self.analysis_results = {
            'file_groups': file_groups,
            'routes': routes_found,
            'duplicate_routes': duplicate_routes,
            'function_groups': function_groups,
            'template_files': template_files,
            'duplicate_templates': duplicate_templates,
            'config_files': config_files,
            'test_groups': test_groups
        }
        
        return self.analysis_results
    
    def generate_cleanup_recommendations(self):
        """Gera recomendações de limpeza"""
        print("\n" + "=" * 60)
        print("📋 RECOMENDAÇÕES DE UNIFICAÇÃO")
        print("=" * 60)
        
        recommendations = []
        
        # Analisar arquivos de teste
        test_files = self.analysis_results.get('file_groups', {}).get('test_files', [])
        if len(test_files) > 10:
            print(f"\n🧪 ARQUIVOS DE TESTE ({len(test_files)} arquivos)")
            print("  📝 RECOMENDAÇÃO: Consolidar em estrutura organizada")
            print("    • Manter apenas os testes mais recentes e completos")
            print("    • Criar diretório 'tests/' para organização")
            recommendations.append({
                'type': 'test_consolidation',
                'files': test_files,
                'action': 'consolidate'
            })
        
        # Analisar arquivos de debug
        debug_files = self.analysis_results.get('file_groups', {}).get('debug_files', [])
        if len(debug_files) > 5:
            print(f"\n🐛 ARQUIVOS DE DEBUG ({len(debug_files)} arquivos)")
            print("  📝 RECOMENDAÇÃO: Consolidar funcionalidades de debug")
            recommendations.append({
                'type': 'debug_consolidation', 
                'files': debug_files,
                'action': 'consolidate'
            })
        
        # Analisar rotas duplicadas
        duplicate_routes = self.analysis_results.get('duplicate_routes', {})
        if duplicate_routes:
            print(f"\n🌐 ROTAS DUPLICADAS ({len(duplicate_routes)} rotas)")
            for route, files in list(duplicate_routes.items())[:5]:
                print(f"  • {route}: {len(files)} definições")
            print("  📝 RECOMENDAÇÃO: Unificar definições de rotas")
            recommendations.append({
                'type': 'route_unification',
                'routes': duplicate_routes,
                'action': 'unify'
            })
        
        # Analisar templates duplicados
        duplicate_templates = self.analysis_results.get('duplicate_templates', {})
        if duplicate_templates:
            print(f"\n🎨 TEMPLATES DUPLICADOS ({len(duplicate_templates)} templates)")
            for template, paths in list(duplicate_templates.items())[:5]:
                print(f"  • {template}: {len(paths)} arquivos")
            print("  📝 RECOMENDAÇÃO: Manter apenas a versão mais atualizada")
            recommendations.append({
                'type': 'template_deduplication',
                'templates': duplicate_templates,
                'action': 'deduplicate'
            })
        
        return recommendations

if __name__ == "__main__":
    analyzer = SystemAnalyzer()
    results = analyzer.run_complete_analysis()
    recommendations = analyzer.generate_cleanup_recommendations()
    
    # Salvar resultados
    with open('system_analysis.json', 'w', encoding='utf-8') as f:
        json.dump({
            'analysis': results,
            'recommendations': recommendations
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 ANÁLISE SALVA EM: system_analysis.json")
    print(f"\n📊 RESUMO:")
    print(f"  📄 Grupos de arquivos identificados: {len(results.get('file_groups', {}))}")
    print(f"  🌐 Rotas duplicadas: {len(results.get('duplicate_routes', {}))}")
    print(f"  🎨 Templates duplicados: {len(results.get('duplicate_templates', {}))}")
    print(f"  📋 Recomendações geradas: {len(recommendations)}")
