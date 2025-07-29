#!/usr/bin/env python3
"""
🔧 CORREÇÃO DE ROTAS COM ERRO 500
===============================

Identifica e corrige problemas específicos nas rotas que estão retornando erro 500.
"""

import os
import sys
from pathlib import Path

def fix_route_errors():
    """Corrige problemas específicos das rotas com erro"""
    print("🔧 CORREÇÃO DE ROTAS COM ERRO 500")
    print("=" * 40)
    
    workspace = Path(r"c:\Users\Arq\OneDrive\Python Projetos\SKPONTO_V2")
    
    # 1. Verificar se templates essenciais existem
    essential_templates = [
        "app/templates/main/index.html",
        "app/templates/main/dashboard.html", 
        "app/templates/admin/usuarios.html",
        "app/templates/admin/system_config.html",
        "app/templates/admin/hour_bank.html",
        "app/templates/admin/hour_bank_users.html",
        "app/templates/admin/hour_compensations.html",
        "app/templates/admin/overtime_requests.html",
        "app/templates/main/my_hour_bank.html",
        "app/templates/main/my_compensations.html",
        "app/templates/main/request_compensation.html"
    ]
    
    missing_templates = []
    for template in essential_templates:
        template_path = workspace / template
        if not template_path.exists():
            missing_templates.append(template)
            print(f"❌ Template faltando: {template}")
        else:
            print(f"✅ Template OK: {template}")
    
    # 2. Criar templates faltando com base em templates similares
    if missing_templates:
        print(f"\n🔨 CRIANDO {len(missing_templates)} TEMPLATES FALTANDO...")
        
        # Template básico para usuários admin
        basic_admin_template = '''{% extends "base.html" %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">{{ title or 'Administração' }}</h3>
                </div>
                <div class="card-body">
                    <div class="text-center py-4">
                        <i class="fas fa-tools fa-3x text-muted mb-3"></i>
                        <h5>Página em Desenvolvimento</h5>
                        <p class="text-muted">Esta funcionalidade está sendo implementada.</p>
                        <a href="{{ url_for('admin.dashboard') }}" class="btn btn-primary">
                            <i class="fas fa-arrow-left"></i> Voltar ao Dashboard
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

        # Template básico para usuários normais
        basic_user_template = '''{% extends "base.html" %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">{{ title or 'Área do Usuário' }}</h3>
                </div>
                <div class="card-body">
                    <div class="text-center py-4">
                        <i class="fas fa-user fa-3x text-muted mb-3"></i>
                        <h5>Página em Desenvolvimento</h5>
                        <p class="text-muted">Esta funcionalidade está sendo implementada.</p>
                        <a href="{{ url_for('main.dashboard') }}" class="btn btn-primary">
                            <i class="fas fa-arrow-left"></i> Voltar ao Dashboard
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

        for template in missing_templates:
            template_path = workspace / template
            template_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Escolher template base
            if 'admin' in template:
                content = basic_admin_template
            else:
                content = basic_user_template
                
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Criado: {template}")
    
    # 3. Verificar e corrigir imports problemáticos
    print(f"\n🔍 VERIFICANDO IMPORTS...")
    
    # Verificar se UserType está sendo importado corretamente
    files_to_check = [
        "app/api/routes.py",
        "app/admin/routes.py", 
        "app/main/routes.py"
    ]
    
    for file_path in files_to_check:
        full_path = workspace / file_path
        if full_path.exists():
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Verificar se UserType está sendo importado
                if 'UserType' in content and 'from app.models import' in content:
                    print(f"✅ Imports OK: {file_path}")
                else:
                    print(f"⚠️ Verificar imports: {file_path}")
            except Exception as e:
                print(f"❌ Erro ao verificar {file_path}: {e}")
    
    # 4. Criar template específico para usuarios.html
    usuarios_template = '''{% extends "base.html" %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">
                        <i class="fas fa-users"></i> Gestão de Usuários
                    </h3>
                    <div class="card-tools">
                        <a href="{{ url_for('admin.novo_usuario') }}" class="btn btn-primary btn-sm">
                            <i class="fas fa-plus"></i> Novo Usuário
                        </a>
                    </div>
                </div>
                <div class="card-body">
                    <!-- Filtros -->
                    <form method="GET" class="row mb-3">
                        <div class="col-md-4">
                            <input type="text" class="form-control" name="busca" 
                                   placeholder="Buscar por nome, email ou CPF..." 
                                   value="{{ request.args.get('busca', '') }}">
                        </div>
                        <div class="col-md-2">
                            <select name="status" class="form-control">
                                <option value="todos">Todos</option>
                                <option value="ativo" {{ 'selected' if request.args.get('status') == 'ativo' }}>Ativos</option>
                                <option value="inativo" {{ 'selected' if request.args.get('status') == 'inativo' }}>Inativos</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <select name="tipo" class="form-control">
                                <option value="todos">Todos os Tipos</option>
                                <option value="admin" {{ 'selected' if request.args.get('tipo') == 'admin' }}>Admin</option>
                                <option value="trabalhador" {{ 'selected' if request.args.get('tipo') == 'trabalhador' }}>Trabalhador</option>
                                <option value="estagiario" {{ 'selected' if request.args.get('tipo') == 'estagiario' }}>Estagiário</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <button type="submit" class="btn btn-secondary">
                                <i class="fas fa-search"></i> Filtrar
                            </button>
                        </div>
                    </form>

                    <!-- Tabela de Usuários -->
                    {% if usuarios.items %}
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Nome</th>
                                    <th>Email</th>
                                    <th>CPF</th>
                                    <th>Tipo</th>
                                    <th>Status</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for usuario in usuarios.items %}
                                <tr>
                                    <td>{{ usuario.nome }} {{ usuario.sobrenome }}</td>
                                    <td>{{ usuario.email }}</td>
                                    <td>{{ usuario.cpf or '-' }}</td>
                                    <td>
                                        <span class="badge badge-{{ 'danger' if usuario.user_type.value == 'admin' else 'primary' if usuario.user_type.value == 'trabalhador' else 'warning' }}">
                                            {{ usuario.user_type.value.title() }}
                                        </span>
                                    </td>
                                    <td>
                                        <span class="badge badge-{{ 'success' if usuario.is_active else 'secondary' }}">
                                            {{ 'Ativo' if usuario.is_active else 'Inativo' }}
                                        </span>
                                    </td>
                                    <td>
                                        <a href="{{ url_for('admin.editar_usuario', id=usuario.id) }}" 
                                           class="btn btn-sm btn-outline-primary">
                                            <i class="fas fa-edit"></i>
                                        </a>
                                        {% if usuario.id != current_user.id %}
                                        <form method="POST" style="display: inline;" 
                                              action="{{ url_for('admin.toggle_user_status', id=usuario.id) }}">
                                            <button type="submit" 
                                                    class="btn btn-sm btn-outline-{{ 'danger' if usuario.is_active else 'success' }}">
                                                <i class="fas fa-{{ 'ban' if usuario.is_active else 'check' }}"></i>
                                            </button>
                                        </form>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- Paginação -->
                    {% if usuarios.pages > 1 %}
                    <nav aria-label="Navegação">
                        <ul class="pagination justify-content-center">
                            {% if usuarios.has_prev %}
                                <li class="page-item">
                                    <a class="page-link" href="{{ url_for('admin.usuarios', page=usuarios.prev_num, **request.args) }}">Anterior</a>
                                </li>
                            {% endif %}
                            
                            {% for page_num in usuarios.iter_pages() %}
                                {% if page_num %}
                                    {% if page_num != usuarios.page %}
                                        <li class="page-item">
                                            <a class="page-link" href="{{ url_for('admin.usuarios', page=page_num, **request.args) }}">{{ page_num }}</a>
                                        </li>
                                    {% else %}
                                        <li class="page-item active">
                                            <span class="page-link">{{ page_num }}</span>
                                        </li>
                                    {% endif %}
                                {% else %}
                                    <li class="page-item disabled">
                                        <span class="page-link">…</span>
                                    </li>
                                {% endif %}
                            {% endfor %}
                            
                            {% if usuarios.has_next %}
                                <li class="page-item">
                                    <a class="page-link" href="{{ url_for('admin.usuarios', page=usuarios.next_num, **request.args) }}">Próximo</a>
                                </li>
                            {% endif %}
                        </ul>
                    </nav>
                    {% endif %}
                    
                    {% else %}
                    <div class="text-center py-4">
                        <i class="fas fa-users fa-3x text-muted mb-3"></i>
                        <h5>Nenhum usuário encontrado</h5>
                        <p class="text-muted">Tente ajustar os filtros ou adicione um novo usuário.</p>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''
    
    # Criar template específico para usuarios
    usuarios_path = workspace / "app/templates/admin/usuarios.html"
    if not usuarios_path.exists():
        usuarios_path.parent.mkdir(parents=True, exist_ok=True)
        with open(usuarios_path, 'w', encoding='utf-8') as f:
            f.write(usuarios_template)
        print("✅ Criado template específico: usuarios.html")
    
    print(f"\n✅ CORREÇÃO CONCLUÍDA!")
    print("🔄 Reinicie o servidor para aplicar as correções")
    
    return True

if __name__ == "__main__":
    fix_route_errors()
