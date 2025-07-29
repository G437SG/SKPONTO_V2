#!/usr/bin/env python3
"""
🔧 CORREÇÃO ESPECÍFICA DAS 12 ROTAS COM ERRO 500
===============================================

Corrige os problemas identificados nas rotas que ainda retornam erro 500:
• /                                   - 500
• /dashboard                          - 500
• /admin/usuarios                     - 500
• /admin/system-config                - 500
• /admin/hour-bank                    - 500
• /admin/hour-bank/users              - 500
• /admin/hour-compensations           - 500
• /admin/overtime-requests            - 500
• /my-hour-bank                       - 500
• /my-compensations                   - 500
• /request-compensation               - 500
• /api/time-records                   - 500
"""

import os
import sys
from pathlib import Path

def fix_missing_routes():
    """Adiciona rotas que estão faltando"""
    print("🔧 ADICIONANDO ROTAS FALTANDO...")
    
    workspace = Path(r"c:\Users\Arq\OneDrive\Python Projetos\SKPONTO_V2")
    
    # 1. Verificar se as rotas de hour-bank estão mapeadas corretamente
    admin_routes_file = workspace / "app/admin/routes.py"
    
    # Adicionar rotas que redirecionam para hour_bank_routes
    additional_routes = '''
# Redirecionamentos para hour bank routes
@bp.route('/hour-bank')
@login_required
@admin_required
def hour_bank():
    """Redireciona para hour bank dashboard"""
    return redirect(url_for('admin.hour_bank_dashboard'))

@bp.route('/hour-bank/users')
@login_required
@admin_required
def hour_bank_users_redirect():
    """Redireciona para usuários do hour bank"""
    return redirect(url_for('admin.hour_bank_users'))

@bp.route('/hour-compensations')
@login_required
@admin_required
def hour_compensations():
    """Redireciona para compensações de horas"""
    return redirect(url_for('admin.hour_compensations'))

@bp.route('/overtime-requests')
@login_required
@admin_required
def overtime_requests():
    """Redireciona para solicitações de horas extras"""
    return redirect(url_for('admin.overtime_requests'))

@bp.route('/system-config', methods=['GET', 'POST'])
@login_required
@admin_required
def system_config():
    """Configurações do sistema"""
    return render_template('admin/system_config.html', title='Configurações do Sistema')
'''
    
    # Verificar se as rotas já existem
    try:
        with open(admin_routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'def hour_bank():' not in content:
            # Adicionar as rotas no final do arquivo
            with open(admin_routes_file, 'a', encoding='utf-8') as f:
                f.write(additional_routes)
            print("✅ Rotas admin adicionadas")
        else:
            print("✅ Rotas admin já existem")
            
    except Exception as e:
        print(f"❌ Erro ao modificar admin routes: {e}")
    
    # 2. Verificar main routes para página inicial e dashboard
    main_routes_file = workspace / "app/main/routes.py"
    
    try:
        with open(main_routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verificar se função dashboard existe
        if 'def dashboard():' in content:
            print("✅ Função dashboard existe")
        else:
            print("⚠️ Função dashboard não encontrada")
            
        # Verificar se função index existe
        if 'def index():' in content:
            print("✅ Função index existe")
        else:
            print("⚠️ Função index não encontrada")
            
    except Exception as e:
        print(f"❌ Erro ao verificar main routes: {e}")

def fix_api_routes():
    """Corrige problemas nas rotas da API"""
    print("🔧 CORRIGINDO ROTAS DA API...")
    
    workspace = Path(r"c:\Users\Arq\OneDrive\Python Projetos\SKPONTO_V2")
    api_routes_file = workspace / "app/api/routes.py"
    
    try:
        with open(api_routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verificar se UserType está sendo importado corretamente
        if 'UserType' in content and 'from app.models import' in content:
            print("✅ API imports OK")
        else:
            # Corrigir imports se necessário
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'from app.models import' in line and 'UserType' not in line:
                    # Adicionar UserType ao import
                    lines[i] = line.replace(')', ', UserType)')
                    break
            
            # Reescrever arquivo
            with open(api_routes_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print("✅ API imports corrigidos")
            
    except Exception as e:
        print(f"❌ Erro ao corrigir API routes: {e}")

def create_missing_templates():
    """Cria templates específicos para as rotas que ainda falham"""
    print("🎨 CRIANDO TEMPLATES ESPECÍFICOS...")
    
    workspace = Path(r"c:\Users\Arq\OneDrive\Python Projetos\SKPONTO_V2")
    
    # Template para hour bank admin
    hour_bank_template = '''{% extends "base.html" %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">
                        <i class="fas fa-clock"></i> Banco de Horas - Administração
                    </h3>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <div class="card bg-primary text-white">
                                <div class="card-body">
                                    <h5><i class="fas fa-users"></i> Usuários com Banco de Horas</h5>
                                    <h3>{{ users_count or 0 }}</h3>
                                    <a href="{{ url_for('admin.hour_bank_users') }}" class="btn btn-light btn-sm">
                                        Ver Detalhes
                                    </a>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <div class="card bg-success text-white">
                                <div class="card-body">
                                    <h5><i class="fas fa-plus"></i> Total Creditado</h5>
                                    <h3>{{ total_credited or "0h" }}</h3>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <div class="card bg-warning text-white">
                                <div class="card-body">
                                    <h5><i class="fas fa-minus"></i> Total Debitado</h5>
                                    <h3>{{ total_debited or "0h" }}</h3>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row mt-4">
                        <div class="col-md-6">
                            <a href="{{ url_for('admin.hour_bank_users') }}" class="btn btn-primary btn-block">
                                <i class="fas fa-users"></i> Gerenciar Usuários
                            </a>
                        </div>
                        <div class="col-md-6">
                            <a href="{{ url_for('admin.hour_bank_reports') }}" class="btn btn-info btn-block">
                                <i class="fas fa-chart-bar"></i> Relatórios
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

    # Template para hour bank users
    hour_bank_users_template = '''{% extends "base.html" %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">
                        <i class="fas fa-users"></i> Usuários - Banco de Horas
                    </h3>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Usuário</th>
                                    <th>Saldo Atual</th>
                                    <th>Total Creditado</th>
                                    <th>Total Debitado</th>
                                    <th>Última Transação</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% if hour_banks %}
                                    {% for hb in hour_banks %}
                                    <tr>
                                        <td>{{ hb.user.nome }} {{ hb.user.sobrenome }}</td>
                                        <td>
                                            <span class="badge badge-{{ 'success' if hb.current_balance >= 0 else 'danger' }}">
                                                {{ hb.formatted_balance }}
                                            </span>
                                        </td>
                                        <td>{{ hb.formatted_total_credited }}</td>
                                        <td>{{ hb.formatted_total_debited }}</td>
                                        <td>{{ hb.last_transaction.strftime('%d/%m/%Y') if hb.last_transaction else '-' }}</td>
                                        <td>
                                            <a href="{{ url_for('admin.hour_bank_user_detail', user_id=hb.user_id) }}" 
                                               class="btn btn-sm btn-primary">
                                                <i class="fas fa-eye"></i>
                                            </a>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                {% else %}
                                    <tr>
                                        <td colspan="6" class="text-center">
                                            Nenhum banco de horas encontrado
                                        </td>
                                    </tr>
                                {% endif %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

    # Criar templates
    templates_to_create = [
        ("app/templates/admin/hour_bank.html", hour_bank_template),
        ("app/templates/admin/hour_bank_users.html", hour_bank_users_template)
    ]
    
    for template_path, template_content in templates_to_create:
        full_path = workspace / template_path
        if not full_path.exists():
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            print(f"✅ Criado: {template_path}")
        else:
            print(f"✅ Já existe: {template_path}")

def fix_route_naming_issues():
    """Corrige problemas de nomenclatura nas rotas"""
    print("🔧 CORRIGINDO NOMENCLATURA DAS ROTAS...")
    
    workspace = Path(r"c:\Users\Arq\OneDrive\Python Projetos\SKPONTO_V2")
    
    # Corrigir admin hour_bank_routes
    admin_hour_bank_file = workspace / "app/admin/hour_bank_routes.py"
    
    try:
        with open(admin_hour_bank_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Mapear nomes de funções esperados vs reais
        function_mappings = {
            'hour_bank_admin': 'hour_bank_dashboard',
            'overtime_requests_admin': 'overtime_requests'
        }
        
        # Verificar se as funções existem com os nomes corretos
        for expected, actual in function_mappings.items():
            if f'def {actual}(' in content:
                print(f"✅ Função {actual} encontrada")
            else:
                print(f"⚠️ Função {actual} não encontrada")
                
    except Exception as e:
        print(f"❌ Erro ao verificar hour_bank_routes: {e}")

def test_specific_routes():
    """Testa rotas específicas para verificar se foram corrigidas"""
    print("🧪 TESTANDO ROTAS CORRIGIDAS...")
    
    import requests
    
    routes_to_test = [
        '/admin/system-config',
        '/admin/hour-bank', 
        '/admin/hour-bank/users',
        '/admin/hour-compensations',
        '/admin/overtime-requests'
    ]
    
    session = requests.Session()
    
    # Fazer login primeiro
    try:
        login_data = {
            'email': 'admin@skponto.com',
            'password': 'admin123'
        }
        
        response = session.post('http://localhost:5000/login', data=login_data)
        
        if response.status_code == 200:
            print("✅ Login realizado")
            
            # Testar cada rota
            for route in routes_to_test:
                try:
                    response = session.get(f'http://localhost:5000{route}', timeout=5)
                    if response.status_code == 200:
                        print(f"✅ {route} - OK")
                    else:
                        print(f"❌ {route} - {response.status_code}")
                except Exception as e:
                    print(f"❌ {route} - Erro: {e}")
        else:
            print("❌ Erro no login")
            
    except Exception as e:
        print(f"❌ Erro ao testar rotas: {e}")

def main():
    """Executa todas as correções"""
    print("🔧 CORREÇÃO ESPECÍFICA DAS 12 ROTAS COM ERRO 500")
    print("=" * 60)
    
    try:
        # 1. Corrigir rotas faltando
        fix_missing_routes()
        
        # 2. Corrigir rotas da API
        fix_api_routes()
        
        # 3. Criar templates específicos
        create_missing_templates()
        
        # 4. Corrigir nomenclatura
        fix_route_naming_issues()
        
        print("\n✅ CORREÇÕES APLICADAS!")
        print("🔄 Reinicie o servidor e teste novamente")
        
        # 5. Testar se servidor está rodando
        print("\n🧪 Testando se servidor está ativo...")
        test_specific_routes()
        
    except Exception as e:
        print(f"\n❌ Erro durante correção: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
