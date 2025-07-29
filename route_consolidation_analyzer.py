#!/usr/bin/env python3
"""
🌐 ANÁLISE E CONSOLIDAÇÃO DE ROTAS DUPLICADAS
============================================

Identifica e consolida as 145 rotas duplicadas encontradas no sistema.
"""

import os
import ast
import re
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

class RouteAnalyzer:
    def __init__(self, workspace_path):
        self.workspace = Path(workspace_path)
        self.route_map = defaultdict(list)
        self.duplicate_routes = {}
        self.blueprint_routes = defaultdict(list)
        
    def extract_routes_from_file(self, file_path):
        """Extrai rotas de um arquivo Python"""
        routes = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Padrões para encontrar rotas Flask
            route_patterns = [
                r"@app\.route\(['\"]([^'\"]+)['\"]",  # @app.route('/path')
                r"@bp\.route\(['\"]([^'\"]+)['\"]",   # @bp.route('/path') 
                r"@.*\.route\(['\"]([^'\"]+)['\"]",   # @*.route('/path')
                r"add_url_rule\(['\"]([^'\"]+)['\"]", # add_url_rule('/path')
            ]
            
            for pattern in route_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    routes.append({
                        'route': match,
                        'file': str(file_path),
                        'type': 'flask_route'
                    })
                    
            # Buscar blueprints
            blueprint_patterns = [
                r"(\w+)\s*=\s*Blueprint\(['\"](\w+)['\"]",  # bp = Blueprint('name')
                r"Blueprint\(['\"](\w+)['\"]"               # Blueprint('name')
            ]
            
            for pattern in blueprint_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if isinstance(match, tuple):
                        bp_name = match[1] if len(match) > 1 else match[0]
                    else:
                        bp_name = match
                    
                    routes.append({
                        'route': f'blueprint:{bp_name}',
                        'file': str(file_path),
                        'type': 'blueprint'
                    })
                    
        except Exception as e:
            print(f"⚠️ Erro ao analisar {file_path}: {e}")
            
        return routes
    
    def scan_all_routes(self):
        """Escaneia todas as rotas no workspace"""
        print("🔍 Escaneando rotas em todos os arquivos Python...")
        
        python_files = list(self.workspace.rglob("*.py"))
        
        for py_file in python_files:
            # Pular arquivos em .venv e __pycache__
            if '.venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            routes = self.extract_routes_from_file(py_file)
            for route_info in routes:
                route = route_info['route']
                self.route_map[route].append(route_info)
                
        print(f"📊 Encontradas {len(self.route_map)} rotas únicas")
        
    def find_duplicate_routes(self):
        """Identifica rotas duplicadas"""
        print("🔍 Identificando rotas duplicadas...")
        
        for route, instances in self.route_map.items():
            if len(instances) > 1:
                self.duplicate_routes[route] = instances
                
        print(f"⚠️ Encontradas {len(self.duplicate_routes)} rotas duplicadas")
        
    def analyze_route_priority(self, route_instances):
        """Analisa qual instância de rota manter baseado em prioridade"""
        priority_rules = [
            # Arquivos principais têm prioridade
            lambda f: f['file'].endswith('app.py'),
            lambda f: 'main' in f['file'] and 'routes.py' in f['file'],
            lambda f: 'admin' in f['file'] and 'routes.py' in f['file'],
            
            # Evitar arquivos de backup
            lambda f: 'backup' not in f['file'],
            lambda f: 'debug' not in f['file'],
            lambda f: 'test' not in f['file'],
            
            # Preferir arquivos mais recentes
            lambda f: os.path.getmtime(f['file'])
        ]
        
        scored_instances = []
        for instance in route_instances:
            score = 0
            
            # Aplicar regras de prioridade
            for i, rule in enumerate(priority_rules[:-1]):  # Excluir última (timestamp)
                try:
                    if rule(instance):
                        score += (len(priority_rules) - i) * 10
                except:
                    pass
                    
            # Adicionar timestamp como critério de desempate
            try:
                score += os.path.getmtime(instance['file']) / 1000000  # Normalizar
            except:
                pass
                
            scored_instances.append((score, instance))
            
        # Ordenar por score (maior = melhor)
        scored_instances.sort(key=lambda x: x[0], reverse=True)
        
        return scored_instances[0][1], [x[1] for x in scored_instances[1:]]
    
    def generate_consolidation_plan(self):
        """Gera plano de consolidação das rotas"""
        print("📋 Gerando plano de consolidação...")
        
        consolidation_plan = {
            'total_duplicates': len(self.duplicate_routes),
            'routes_to_consolidate': {},
            'files_to_modify': set(),
            'files_to_remove': set()
        }
        
        for route, instances in self.duplicate_routes.items():
            keep_instance, remove_instances = self.analyze_route_priority(instances)
            
            consolidation_plan['routes_to_consolidate'][route] = {
                'keep': keep_instance,
                'remove': remove_instances,
                'duplicate_count': len(instances)
            }
            
            consolidation_plan['files_to_modify'].add(keep_instance['file'])
            for remove_instance in remove_instances:
                consolidation_plan['files_to_remove'].add(remove_instance['file'])
                
        return consolidation_plan
    
    def create_route_map_report(self):
        """Cria relatório detalhado do mapeamento de rotas"""
        print("📊 Criando relatório de mapeamento de rotas...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'workspace': str(self.workspace),
            'summary': {
                'total_unique_routes': len(self.route_map),
                'total_duplicate_routes': len(self.duplicate_routes),
                'total_route_instances': sum(len(instances) for instances in self.route_map.values())
            },
            'top_duplicated_routes': {},
            'route_distribution': {},
            'file_distribution': {}
        }
        
        # Top rotas mais duplicadas
        duplicate_counts = {route: len(instances) for route, instances in self.duplicate_routes.items()}
        top_duplicates = sorted(duplicate_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for route, count in top_duplicates:
            report['top_duplicated_routes'][route] = {
                'duplicate_count': count,
                'files': [inst['file'] for inst in self.duplicate_routes[route]]
            }
            
        # Distribuição por arquivo
        file_counts = Counter()
        for instances in self.route_map.values():
            for instance in instances:
                file_counts[instance['file']] += 1
                
        report['file_distribution'] = dict(file_counts.most_common(20))
        
        return report
    
    def run_route_analysis(self):
        """Executa análise completa das rotas"""
        print("🌐 INICIANDO ANÁLISE COMPLETA DE ROTAS")
        print("=" * 50)
        
        # Escanear todas as rotas
        self.scan_all_routes()
        
        # Encontrar duplicatas
        self.find_duplicate_routes()
        
        # Gerar plano de consolidação
        consolidation_plan = self.generate_consolidation_plan()
        
        # Criar relatório
        report = self.create_route_map_report()
        
        # Salvar resultados
        results_dir = self.workspace / "route_analysis_results"
        results_dir.mkdir(exist_ok=True)
        
        # Salvar plano de consolidação
        with open(results_dir / "consolidation_plan.json", 'w', encoding='utf-8') as f:
            # Converter sets para listas para JSON
            plan_serializable = consolidation_plan.copy()
            plan_serializable['files_to_modify'] = list(consolidation_plan['files_to_modify'])
            plan_serializable['files_to_remove'] = list(consolidation_plan['files_to_remove'])
            json.dump(plan_serializable, f, indent=2, ensure_ascii=False)
            
        # Salvar relatório
        with open(results_dir / "route_analysis_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # Exibir resumo
        print("\n📊 RESUMO DA ANÁLISE:")
        print(f"• Total de rotas únicas: {report['summary']['total_unique_routes']}")
        print(f"• Rotas duplicadas: {report['summary']['total_duplicate_routes']}")
        print(f"• Instâncias totais: {report['summary']['total_route_instances']}")
        print(f"• Arquivos a modificar: {len(consolidation_plan['files_to_modify'])}")
        print(f"• Arquivos a remover: {len(consolidation_plan['files_to_remove'])}")
        
        print(f"\n📁 Resultados salvos em: {results_dir}")
        
        # Top 5 rotas mais duplicadas
        print("\n🔝 TOP 5 ROTAS MAIS DUPLICADAS:")
        for i, (route, data) in enumerate(list(report['top_duplicated_routes'].items())[:5], 1):
            print(f"{i}. {route} ({data['duplicate_count']} duplicatas)")
            
        return consolidation_plan, report

if __name__ == "__main__":
    workspace = r"c:\Users\Arq\OneDrive\Python Projetos\SKPONTO_V2"
    
    analyzer = RouteAnalyzer(workspace)
    plan, report = analyzer.run_route_analysis()
    
    print("\n✅ Análise de rotas concluída!")
    print("📋 Execute o plano de consolidação para unificar as rotas duplicadas")
