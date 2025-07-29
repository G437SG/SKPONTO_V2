#!/usr/bin/env python3
"""
Análise detalhada e plano de unificação dos arquivos duplicados
"""

import os
import json
from pathlib import Path
from datetime import datetime

class DetailedDuplicateAnalyzer:
    def __init__(self):
        self.project_root = Path('.')
        self.critical_duplicates = {}
        
    def analyze_critical_files(self):
        """Analisa arquivos críticos duplicados"""
        print("🔍 ANÁLISE DETALHADA DE DUPLICAÇÕES CRÍTICAS")
        print("=" * 60)
        
        # 1. Analisar arquivos app.py
        self.analyze_app_files()
        
        # 2. Analisar arquivos config.py
        self.analyze_config_files()
        
        # 3. Analisar templates duplicados
        self.analyze_template_duplicates()
        
        # 4. Analisar rotas duplicadas nos blueprints
        self.analyze_blueprint_duplicates()
        
        # 5. Analisar arquivos de teste críticos
        self.analyze_critical_test_files()
        
    def analyze_app_files(self):
        """Analisa arquivos app.py duplicados"""
        print("\n📱 ANALISANDO ARQUIVOS APP.PY...")
        
        app_files = list(self.project_root.glob('app*.py'))
        app_info = {}
        
        for app_file in app_files:
            try:
                with open(app_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                app_info[str(app_file)] = {
                    'size': len(content),
                    'lines': len(content.split('\n')),
                    'has_main': '__main__' in content,
                    'has_create_app': 'create_app' in content,
                    'has_flask_run': 'app.run' in content,
                    'modified': os.path.getmtime(app_file)
                }
                
            except Exception as e:
                print(f"  ❌ Erro ao analisar {app_file}: {e}")
        
        print(f"  📊 {len(app_files)} arquivos app encontrados:")
        for file_path, info in app_info.items():
            mod_time = datetime.fromtimestamp(info['modified']).strftime('%d/%m/%Y %H:%M')
            print(f"    • {file_path}")
            print(f"      📏 {info['lines']} linhas, {info['size']} bytes")
            print(f"      🕒 Modificado: {mod_time}")
            print(f"      🔧 Main: {info['has_main']}, CreateApp: {info['has_create_app']}, Run: {info['has_flask_run']}")
        
        # Identificar arquivo principal
        main_app = None
        for file_path, info in app_info.items():
            if info['has_main'] and info['has_flask_run'] and info['lines'] > 50:
                main_app = file_path
                break
        
        if main_app:
            print(f"  ✅ ARQUIVO PRINCIPAL IDENTIFICADO: {main_app}")
        
        self.critical_duplicates['app_files'] = {
            'files': app_info,
            'main_file': main_app,
            'recommendation': 'Manter apenas o arquivo principal app.py'
        }
    
    def analyze_config_files(self):
        """Analisa arquivos config.py duplicados"""
        print("\n⚙️ ANALISANDO ARQUIVOS CONFIG.PY...")
        
        config_files = list(self.project_root.rglob('config.py'))
        config_info = {}
        
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                config_info[str(config_file)] = {
                    'size': len(content),
                    'lines': len(content.split('\n')),
                    'has_database_config': 'DATABASE_URL' in content or 'SQLALCHEMY' in content,
                    'has_secret_key': 'SECRET_KEY' in content,
                    'has_classes': 'class' in content,
                    'modified': os.path.getmtime(config_file),
                    'in_app_dir': '/app/' in str(config_file) or str(config_file).startswith('app')
                }
                
            except Exception as e:
                print(f"  ❌ Erro ao analisar {config_file}: {e}")
        
        print(f"  📊 {len(config_files)} arquivos config encontrados:")
        for file_path, info in config_info.items():
            mod_time = datetime.fromtimestamp(info['modified']).strftime('%d/%m/%Y %H:%M')
            print(f"    • {file_path}")
            print(f"      📏 {info['lines']} linhas, {info['size']} bytes")
            print(f"      🕒 Modificado: {mod_time}")
            print(f"      🔧 DB: {info['has_database_config']}, Secret: {info['has_secret_key']}, Classes: {info['has_classes']}")
        
        # Identificar config principal (no root ou mais completo)
        main_config = None
        best_score = 0
        
        for file_path, info in config_info.items():
            score = 0
            if not info['in_app_dir']:  # Preferir root
                score += 10
            if info['has_database_config']:
                score += 5
            if info['has_secret_key']:
                score += 3
            if info['has_classes']:
                score += 2
            if info['lines'] > 50:
                score += 2
            
            if score > best_score:
                best_score = score
                main_config = file_path
        
        if main_config:
            print(f"  ✅ CONFIG PRINCIPAL IDENTIFICADO: {main_config}")
        
        self.critical_duplicates['config_files'] = {
            'files': config_info,
            'main_file': main_config,
            'recommendation': 'Manter apenas o config.py principal e consolidar configurações'
        }
    
    def analyze_template_duplicates(self):
        """Analisa templates duplicados"""
        print("\n🎨 ANALISANDO TEMPLATES DUPLICADOS...")
        
        template_duplicates = {
            'atestados.html': [],
            'dashboard.html': [],
            'logs.html': [],
            'notificacoes.html': []
        }
        
        # Buscar templates
        for template_name in template_duplicates.keys():
            templates_found = list(self.project_root.rglob(template_name))
            
            for template_path in templates_found:
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    template_duplicates[template_name].append({
                        'path': str(template_path),
                        'size': len(content),
                        'lines': len(content.split('\n')),
                        'modified': os.path.getmtime(template_path),
                        'has_bootstrap': 'bootstrap' in content.lower(),
                        'has_javascript': '<script' in content,
                        'has_ajax': 'ajax' in content.lower() or 'fetch(' in content
                    })
                except Exception as e:
                    continue
        
        for template_name, templates in template_duplicates.items():
            if len(templates) > 1:
                print(f"\n  📄 {template_name} ({len(templates)} versões):")
                for template in templates:
                    mod_time = datetime.fromtimestamp(template['modified']).strftime('%d/%m/%Y %H:%M')
                    print(f"    • {template['path']}")
                    print(f"      📏 {template['lines']} linhas, {template['size']} bytes")
                    print(f"      🕒 Modificado: {mod_time}")
                    print(f"      🔧 Bootstrap: {template['has_bootstrap']}, JS: {template['has_javascript']}, AJAX: {template['has_ajax']}")
                
                # Recomendar versão mais recente e completa
                best_template = max(templates, key=lambda x: (x['modified'], x['size'], x['has_javascript']))
                print(f"    ✅ RECOMENDADO: {best_template['path']}")
        
        self.critical_duplicates['templates'] = template_duplicates
    
    def analyze_blueprint_duplicates(self):
        """Analisa blueprints com rotas duplicadas"""
        print("\n🌐 ANALISANDO BLUEPRINTS COM ROTAS DUPLICADAS...")
        
        blueprint_files = []
        app_dir = self.project_root / 'app'
        
        if app_dir.exists():
            for py_file in app_dir.rglob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'Blueprint' in content and '@' in content and 'route' in content:
                        blueprint_files.append({
                            'path': str(py_file),
                            'size': len(content),
                            'lines': len(content.split('\n')),
                            'modified': os.path.getmtime(py_file),
                            'blueprint_name': self.extract_blueprint_name(content)
                        })
                except:
                    continue
        
        print(f"  📊 {len(blueprint_files)} arquivos de blueprint encontrados:")
        
        # Agrupar por funcionalidade
        blueprint_groups = {}
        for bp in blueprint_files:
            bp_name = bp['blueprint_name'] or 'unknown'
            if bp_name not in blueprint_groups:
                blueprint_groups[bp_name] = []
            blueprint_groups[bp_name].append(bp)
        
        for group_name, blueprints in blueprint_groups.items():
            if len(blueprints) > 1:
                print(f"\n  ⚠️  GRUPO {group_name} ({len(blueprints)} arquivos):")
                for bp in blueprints:
                    mod_time = datetime.fromtimestamp(bp['modified']).strftime('%d/%m/%Y %H:%M')
                    print(f"    • {bp['path']} ({bp['lines']} linhas, {mod_time})")
            else:
                print(f"  ✅ {group_name}: 1 arquivo")
        
        self.critical_duplicates['blueprints'] = blueprint_groups
    
    def extract_blueprint_name(self, content):
        """Extrai nome do blueprint do conteúdo"""
        import re
        
        # Buscar padrões como: bp = Blueprint('name', ...)
        match = re.search(r"Blueprint\s*\(\s*['\"]([^'\"]+)['\"]", content)
        if match:
            return match.group(1)
        
        # Buscar padrões como: admin_bp = Blueprint(...)
        match = re.search(r"(\w+)\s*=\s*Blueprint", content)
        if match:
            return match.group(1)
        
        return None
    
    def analyze_critical_test_files(self):
        """Analisa arquivos de teste críticos"""
        print("\n🧪 ANALISANDO ARQUIVOS DE TESTE CRÍTICOS...")
        
        test_groups = {
            'login_tests': list(self.project_root.glob('*login*.py')),
            'system_tests': list(self.project_root.glob('test_*system*.py')),
            'final_tests': list(self.project_root.glob('test_*final*.py')),
            'complete_tests': list(self.project_root.glob('test_*complete*.py'))
        }
        
        for group_name, test_files in test_groups.items():
            if test_files:
                print(f"\n  📊 {group_name} ({len(test_files)} arquivos):")
                
                test_info = []
                for test_file in test_files:
                    try:
                        with open(test_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        test_info.append({
                            'path': str(test_file),
                            'size': len(content),
                            'lines': len(content.split('\n')),
                            'modified': os.path.getmtime(test_file),
                            'has_main': '__main__' in content,
                            'has_session': 'session' in content.lower(),
                            'has_login': 'login' in content.lower()
                        })
                    except:
                        continue
                
                # Mostrar apenas os mais relevantes
                test_info.sort(key=lambda x: (x['modified'], x['size']), reverse=True)
                for test in test_info[:3]:  # Top 3 mais recentes
                    mod_time = datetime.fromtimestamp(test['modified']).strftime('%d/%m/%Y %H:%M')
                    print(f"    • {test['path']}")
                    print(f"      📏 {test['lines']} linhas, modificado: {mod_time}")
        
        self.critical_duplicates['test_files'] = test_groups
    
    def create_unification_plan(self):
        """Cria plano de unificação"""
        print("\n" + "=" * 60)
        print("📋 PLANO DE UNIFICAÇÃO DO SISTEMA")
        print("=" * 60)
        
        plan = {
            'priority_1_critical': [],
            'priority_2_important': [],
            'priority_3_cleanup': [],
            'files_to_keep': [],
            'files_to_remove': []
        }
        
        # PRIORIDADE 1: Arquivos críticos
        print("\n🔴 PRIORIDADE 1 - ARQUIVOS CRÍTICOS:")
        
        # App files
        if 'app_files' in self.critical_duplicates:
            main_app = self.critical_duplicates['app_files']['main_file']
            other_apps = [f for f in self.critical_duplicates['app_files']['files'].keys() if f != main_app]
            
            if main_app and other_apps:
                print(f"  📱 MANTER: {main_app}")
                print(f"  🗑️  REMOVER: {', '.join(other_apps)}")
                plan['files_to_keep'].append(main_app)
                plan['files_to_remove'].extend(other_apps)
                plan['priority_1_critical'].append({
                    'action': 'Consolidar arquivos app.py',
                    'keep': main_app,
                    'remove': other_apps
                })
        
        # Config files
        if 'config_files' in self.critical_duplicates:
            main_config = self.critical_duplicates['config_files']['main_file']
            other_configs = [f for f in self.critical_duplicates['config_files']['files'].keys() if f != main_config]
            
            if main_config and other_configs:
                print(f"  ⚙️  MANTER: {main_config}")
                print(f"  🗑️  REMOVER: {', '.join(other_configs)}")
                plan['files_to_keep'].append(main_config)
                plan['files_to_remove'].extend(other_configs)
                plan['priority_1_critical'].append({
                    'action': 'Consolidar arquivos config.py',
                    'keep': main_config,
                    'remove': other_configs
                })
        
        # PRIORIDADE 2: Templates
        print("\n🟡 PRIORIDADE 2 - TEMPLATES:")
        
        if 'templates' in self.critical_duplicates:
            for template_name, versions in self.critical_duplicates['templates'].items():
                if len(versions) > 1:
                    # Escolher versão mais recente e completa
                    best = max(versions, key=lambda x: (x['modified'], x['size'], x['has_javascript']))
                    others = [v['path'] for v in versions if v['path'] != best['path']]
                    
                    if others:
                        print(f"  🎨 {template_name}:")
                        print(f"    MANTER: {best['path']}")
                        print(f"    REMOVER: {', '.join(others)}")
                        plan['files_to_keep'].append(best['path'])
                        plan['files_to_remove'].extend(others)
                        plan['priority_2_important'].append({
                            'action': f'Consolidar template {template_name}',
                            'keep': best['path'],
                            'remove': others
                        })
        
        # PRIORIDADE 3: Limpeza de testes
        print("\n🟢 PRIORIDADE 3 - LIMPEZA DE TESTES:")
        test_files_to_clean = list(self.project_root.glob('test_*.py'))
        
        # Manter apenas os mais importantes
        important_tests = [
            'test_final_complete.py',
            'test_corrected_routes.py', 
            'test_login_intelligent.py',
            'test_complete_system.py'
        ]
        
        tests_to_keep = []
        tests_to_remove = []
        
        for test_file in test_files_to_clean:
            if test_file.name in important_tests:
                tests_to_keep.append(str(test_file))
            else:
                tests_to_remove.append(str(test_file))
        
        if tests_to_remove:
            print(f"  🧪 MANTER: {len(tests_to_keep)} testes importantes")
            print(f"  🗑️  LIMPAR: {len(tests_to_remove)} testes obsoletos")
            plan['files_to_keep'].extend(tests_to_keep)
            plan['files_to_remove'].extend(tests_to_remove[:50])  # Limitar para não sobrecarregar
            plan['priority_3_cleanup'].append({
                'action': 'Limpeza de arquivos de teste obsoletos',
                'keep_count': len(tests_to_keep),
                'remove_count': len(tests_to_remove)
            })
        
        return plan
    
    def run_detailed_analysis(self):
        """Executa análise detalhada completa"""
        self.analyze_critical_files()
        plan = self.create_unification_plan()
        
        # Salvar plano
        with open('unification_plan.json', 'w', encoding='utf-8') as f:
            json.dump({
                'critical_duplicates': self.critical_duplicates,
                'unification_plan': plan,
                'analysis_date': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 PLANO DETALHADO SALVO EM: unification_plan.json")
        
        # Estatísticas finais
        total_to_remove = len(plan['files_to_remove'])
        total_to_keep = len(plan['files_to_keep'])
        
        print(f"\n📊 RESUMO DO PLANO:")
        print(f"  📁 Arquivos para manter: {total_to_keep}")
        print(f"  🗑️  Arquivos para remover: {total_to_remove}")
        print(f"  🔴 Ações críticas: {len(plan['priority_1_critical'])}")
        print(f"  🟡 Ações importantes: {len(plan['priority_2_important'])}")
        print(f"  🟢 Ações de limpeza: {len(plan['priority_3_cleanup'])}")
        
        return plan

if __name__ == "__main__":
    analyzer = DetailedDuplicateAnalyzer()
    plan = analyzer.run_detailed_analysis()
