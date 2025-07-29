#!/usr/bin/env python3
"""
Lista todas as rotas disponíveis no SKPONTO
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def list_all_routes():
    """Lista todas as rotas disponíveis"""
    print("📋 LISTANDO TODAS AS ROTAS DO SKPONTO")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': rule.rule
            })
        
        # Ordenar por URL
        routes.sort(key=lambda x: x['rule'])
        
        print(f"📊 TOTAL DE ROTAS: {len(routes)}")
        print("\n🌐 ROTAS DISPONÍVEIS:")
        
        for route in routes:
            methods = ', '.join([m for m in route['methods'] if m not in ['HEAD', 'OPTIONS']])
            print(f"  {route['rule']:<40} [{methods:<15}] {route['endpoint']}")
        
        # Agrupar por blueprint/área
        print("\n📁 ROTAS POR ÁREA:")
        
        areas = {}
        for route in routes:
            if '.' in route['endpoint']:
                area = route['endpoint'].split('.')[0]
            else:
                area = 'main'
            
            if area not in areas:
                areas[area] = []
            areas[area].append(route)
        
        for area, area_routes in sorted(areas.items()):
            print(f"\n📂 {area.upper()} ({len(area_routes)} rotas):")
            for route in area_routes:
                methods = ', '.join([m for m in route['methods'] if m not in ['HEAD', 'OPTIONS']])
                print(f"  {route['rule']:<40} [{methods}]")

if __name__ == "__main__":
    list_all_routes()
