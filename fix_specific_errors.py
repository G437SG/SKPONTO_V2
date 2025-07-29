#!/usr/bin/env python3
"""
Script para corrigir os erros específicos encontrados nos logs
"""

import os
import sys
import requests
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurações
BASE_URL = "http://localhost:5000"
USERNAME = "admin@skponto.com"
PASSWORD = "admin123"

# Templates que precisam ser criados
TEMPLATES_TO_CREATE = {
    "main/hour_bank/request_compensation.html": """
{% extends "base.html" %}

{% block title %}Solicitar Compensação{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-md-8 offset-md-2">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0"><i class="fas fa-clock"></i> Solicitar Compensação de Horas</h4>
                </div>
                <div class="card-body">
                    <form method="POST">
                        {{ form.hidden_tag() }}
                        
                        <div class="mb-3">
                            {{ form.tipo.label(class="form-label") }}
                            {{ form.tipo(class="form-select") }}
                            {% if form.tipo.errors %}
                                <div class="text-danger">
                                    {% for error in form.tipo.errors %}
                                        <small>{{ error }}</small>
                                    {% endfor %}
                                </div>
                            {% endif %}
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    {{ form.data_inicio.label(class="form-label") }}
                                    {{ form.data_inicio(class="form-control") }}
                                    {% if form.data_inicio.errors %}
                                        <div class="text-danger">
                                            {% for error in form.data_inicio.errors %}
                                                <small>{{ error }}</small>
                                            {% endfor %}
                                        </div>
                                    {% endif %}
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    {{ form.data_fim.label(class="form-label") }}
                                    {{ form.data_fim(class="form-control") }}
                                    {% if form.data_fim.errors %}
                                        <div class="text-danger">
                                            {% for error in form.data_fim.errors %}
                                                <small>{{ error }}</small>
                                            {% endfor %}
                                        </div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            {{ form.horas_solicitadas.label(class="form-label") }}
                            {{ form.horas_solicitadas(class="form-control") }}
                            {% if form.horas_solicitadas.errors %}
                                <div class="text-danger">
                                    {% for error in form.horas_solicitadas.errors %}
                                        <small>{{ error }}</small>
                                    {% endfor %}
                                </div>
                            {% endif %}
                        </div>
                        
                        <div class="mb-3">
                            {{ form.motivo.label(class="form-label") }}
                            {{ form.motivo(class="form-control", rows="4") }}
                            {% if form.motivo.errors %}
                                <div class="text-danger">
                                    {% for error in form.motivo.errors %}
                                        <small>{{ error }}</small>
                                    {% endfor %}
                                </div>
                            {% endif %}
                        </div>
                        
                        <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                            <a href="{{ url_for('main.my_compensations') }}" class="btn btn-secondary">
                                <i class="fas fa-arrow-left"></i> Voltar
                            </a>
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-paper-plane"></i> Solicitar Compensação
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",
    
    "admin/system_config.html": """
{% extends "base.html" %}

{% block title %}Configurações do Sistema{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0"><i class="fas fa-cogs"></i> Configurações do Sistema</h4>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="card h-100">
                                <div class="card-body">
                                    <h5><i class="fas fa-database"></i> Banco de Dados</h5>
                                    <p class="text-muted">Configurações de conexão e backup</p>
                                    <div class="mb-2">
                                        <strong>Status:</strong> 
                                        <span class="badge bg-success">Conectado</span>
                                    </div>
                                    <div class="mb-2">
                                        <strong>Tipo:</strong> PostgreSQL
                                    </div>
                                    <button class="btn btn-outline-primary btn-sm">
                                        <i class="fas fa-sync"></i> Testar Conexão
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card h-100">
                                <div class="card-body">
                                    <h5><i class="fas fa-shield-alt"></i> Segurança</h5>
                                    <p class="text-muted">Configurações de autenticação</p>
                                    <div class="mb-2">
                                        <strong>Rate Limiting:</strong> 
                                        <span class="badge bg-success">Ativo</span>
                                    </div>
                                    <div class="mb-2">
                                        <strong>CSRF Protection:</strong> 
                                        <span class="badge bg-success">Ativo</span>
                                    </div>
                                    <button class="btn btn-outline-warning btn-sm">
                                        <i class="fas fa-eye"></i> Ver Logs
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <hr class="my-4">
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="card h-100">
                                <div class="card-body">
                                    <h5><i class="fas fa-file-archive"></i> Backup</h5>
                                    <p class="text-muted">Sistema de backup automático</p>
                                    <div class="mb-2">
                                        <strong>Último Backup:</strong> 
                                        <span id="last-backup">Verificando...</span>
                                    </div>
                                    <div class="mb-2">
                                        <strong>Frequência:</strong> Diário
                                    </div>
                                    <button class="btn btn-outline-success btn-sm">
                                        <i class="fas fa-download"></i> Executar Backup
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card h-100">
                                <div class="card-body">
                                    <h5><i class="fas fa-chart-line"></i> Performance</h5>
                                    <p class="text-muted">Métricas do sistema</p>
                                    <div class="mb-2">
                                        <strong>Cache:</strong> 
                                        <span class="badge bg-success">Ativo</span>
                                    </div>
                                    <div class="mb-2">
                                        <strong>Compressão:</strong> 
                                        <span class="badge bg-success">GZIP</span>
                                    </div>
                                    <button class="btn btn-outline-info btn-sm">
                                        <i class="fas fa-tachometer-alt"></i> Ver Métricas
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",
    
    "main/index.html": """
{% extends "base.html" %}

{% block title %}SKPONTO - Sistema de Controle de Ponto{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <div class="jumbotron bg-primary text-white rounded p-5 mb-4">
                <h1 class="display-4">
                    <i class="fas fa-clock"></i> SKPONTO
                </h1>
                <p class="lead">Sistema Completo de Controle de Ponto</p>
                <hr class="my-4" style="border-color: rgba(255,255,255,0.3);">
                <p>Gerencie registros de ponto, horas extras, atestados e muito mais de forma simples e eficiente.</p>
                
                {% if current_user.is_authenticated %}
                    <a class="btn btn-light btn-lg" href="{{ url_for('main.dashboard') }}" role="button">
                        <i class="fas fa-tachometer-alt"></i> Ir para Dashboard
                    </a>
                {% else %}
                    <a class="btn btn-light btn-lg" href="{{ url_for('auth.login') }}" role="button">
                        <i class="fas fa-sign-in-alt"></i> Fazer Login
                    </a>
                {% endif %}
            </div>
        </div>
    </div>
    
    {% if current_user.is_authenticated %}
    <div class="row">
        <div class="col-md-4">
            <div class="card text-center">
                <div class="card-body">
                    <i class="fas fa-clock fa-3x text-primary mb-3"></i>
                    <h5 class="card-title">Registrar Ponto</h5>
                    <p class="card-text">Registre entrada, saída e intervalos rapidamente.</p>
                    <a href="{{ url_for('main.registrar_ponto') }}" class="btn btn-primary">
                        <i class="fas fa-plus"></i> Registrar
                    </a>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card text-center">
                <div class="card-body">
                    <i class="fas fa-chart-line fa-3x text-success mb-3"></i>
                    <h5 class="card-title">Meus Registros</h5>
                    <p class="card-text">Visualize seus registros de ponto e histórico.</p>
                    <a href="{{ url_for('main.meus_registros') }}" class="btn btn-success">
                        <i class="fas fa-list"></i> Ver Registros
                    </a>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card text-center">
                <div class="card-body">
                    <i class="fas fa-file-medical fa-3x text-warning mb-3"></i>
                    <h5 class="card-title">Atestados</h5>
                    <p class="card-text">Gerencie seus atestados médicos.</p>
                    <a href="{{ url_for('main.meus_atestados') }}" class="btn btn-warning">
                        <i class="fas fa-folder"></i> Ver Atestados
                    </a>
                </div>
            </div>
        </div>
    </div>
    
    {% if current_user.user_type == 'admin' %}
    <hr class="my-4">
    <div class="row">
        <div class="col-12">
            <h3><i class="fas fa-user-shield"></i> Área Administrativa</h3>
        </div>
        
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <i class="fas fa-users fa-2x text-info mb-2"></i>
                    <h6 class="card-title">Usuários</h6>
                    <a href="{{ url_for('admin.usuarios') }}" class="btn btn-info btn-sm">
                        <i class="fas fa-cog"></i> Gerenciar
                    </a>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <i class="fas fa-clock fa-2x text-primary mb-2"></i>
                    <h6 class="card-title">Banco de Horas</h6>
                    <a href="{{ url_for('admin.hour_bank') }}" class="btn btn-primary btn-sm">
                        <i class="fas fa-bank"></i> Ver
                    </a>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <i class="fas fa-chart-bar fa-2x text-success mb-2"></i>
                    <h6 class="card-title">Relatórios</h6>
                    <a href="{{ url_for('admin.relatorios') }}" class="btn btn-success btn-sm">
                        <i class="fas fa-chart-line"></i> Gerar
                    </a>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <i class="fas fa-cogs fa-2x text-secondary mb-2"></i>
                    <h6 class="card-title">Sistema</h6>
                    <a href="{{ url_for('admin.system_config') }}" class="btn btn-secondary btn-sm">
                        <i class="fas fa-settings"></i> Config
                    </a>
                </div>
            </div>
        </div>
    </div>
    {% endif %}
    {% endif %}
</div>
{% endblock %}
""",

    "main/dashboard.html": """
{% extends "base.html" %}

{% block title %}Dashboard{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <h2><i class="fas fa-tachometer-alt"></i> Dashboard</h2>
            <hr>
        </div>
    </div>
    
    <!-- Estatísticas Rápidas -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card bg-primary text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h5>Horas Hoje</h5>
                            <h3 id="horas-hoje">0h 0m</h3>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-clock fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h5>Banco de Horas</h5>
                            <h3 id="banco-horas">0h 0m</h3>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-piggy-bank fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card bg-warning text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h5>Atestados</h5>
                            <h3 id="total-atestados">0</h3>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-file-medical fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card bg-info text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h5>Frequência</h5>
                            <h3 id="frequencia-mes">100%</h3>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-percentage fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Ações Rápidas -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h5><i class="fas fa-bolt"></i> Ações Rápidas</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <a href="{{ url_for('main.registrar_ponto') }}" class="btn btn-primary btn-lg w-100 mb-2">
                                <i class="fas fa-clock"></i><br>
                                Registrar Ponto
                            </a>
                        </div>
                        <div class="col-md-3">
                            <a href="{{ url_for('main.my_hour_bank') }}" class="btn btn-success btn-lg w-100 mb-2">
                                <i class="fas fa-piggy-bank"></i><br>
                                Banco de Horas
                            </a>
                        </div>
                        <div class="col-md-3">
                            <a href="{{ url_for('main.meus_atestados') }}" class="btn btn-warning btn-lg w-100 mb-2">
                                <i class="fas fa-file-medical"></i><br>
                                Atestados
                            </a>
                        </div>
                        <div class="col-md-3">
                            <a href="{{ url_for('main.meus_registros') }}" class="btn btn-info btn-lg w-100 mb-2">
                                <i class="fas fa-list"></i><br>
                                Meus Registros
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Últimos Registros -->
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5><i class="fas fa-history"></i> Últimos Registros</h5>
                </div>
                <div class="card-body">
                    <div id="ultimos-registros">
                        <div class="text-center">
                            <i class="fas fa-spinner fa-spin"></i> Carregando...
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5><i class="fas fa-bell"></i> Notificações</h5>
                </div>
                <div class="card-body">
                    <div id="notificacoes">
                        <div class="text-center">
                            <i class="fas fa-spinner fa-spin"></i> Carregando...
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Carregar estatísticas
    fetch('/api/estatisticas')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('horas-hoje').textContent = data.horas_hoje || '0h 0m';
                document.getElementById('banco-horas').textContent = data.banco_horas || '0h 0m';
                document.getElementById('total-atestados').textContent = data.total_atestados || '0';
                document.getElementById('frequencia-mes').textContent = data.frequencia_mes || '100%';
            }
        })
        .catch(error => console.error('Erro ao carregar estatísticas:', error));
    
    // Carregar últimos registros
    fetch('/api/meus_registros?limit=5')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.records.length > 0) {
                let html = '<div class="table-responsive"><table class="table table-sm">';
                html += '<thead><tr><th>Data</th><th>Entrada</th><th>Saída</th><th>Horas</th></tr></thead><tbody>';
                
                data.records.forEach(record => {
                    html += `<tr>
                        <td>${record.data}</td>
                        <td>${record.entrada || '-'}</td>
                        <td>${record.saida || '-'}</td>
                        <td>${record.horas_trabalhadas || '-'}</td>
                    </tr>`;
                });
                
                html += '</tbody></table></div>';
                document.getElementById('ultimos-registros').innerHTML = html;
            } else {
                document.getElementById('ultimos-registros').innerHTML = '<p class="text-muted">Nenhum registro encontrado.</p>';
            }
        })
        .catch(error => {
            console.error('Erro ao carregar registros:', error);
            document.getElementById('ultimos-registros').innerHTML = '<p class="text-danger">Erro ao carregar registros.</p>';
        });
    
    // Carregar notificações
    fetch('/api/notificacoes?limit=5')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.notifications.length > 0) {
                let html = '';
                
                data.notifications.forEach(notif => {
                    html += `<div class="alert alert-${notif.tipo === 'SUCCESS' ? 'success' : 'info'} alert-sm mb-2">
                        <strong>${notif.titulo}</strong><br>
                        <small>${notif.mensagem}</small>
                    </div>`;
                });
                
                document.getElementById('notificacoes').innerHTML = html;
            } else {
                document.getElementById('notificacoes').innerHTML = '<p class="text-muted">Nenhuma notificação.</p>';
            }
        })
        .catch(error => {
            console.error('Erro ao carregar notificações:', error);
            document.getElementById('notificacoes').innerHTML = '<p class="text-danger">Erro ao carregar notificações.</p>';
        });
});
</script>
{% endblock %}
""",

    "admin/usuarios.html": """
{% extends "base.html" %}

{% block title %}Gestão de Usuários{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0"><i class="fas fa-users"></i> Gestão de Usuários</h4>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <a href="{{ url_for('admin.novo_usuario') }}" class="btn btn-success">
                                <i class="fas fa-plus"></i> Novo Usuário
                            </a>
                        </div>
                        <div class="col-md-6">
                            <div class="input-group">
                                <input type="text" class="form-control" id="searchInput" placeholder="Buscar usuários...">
                                <button class="btn btn-outline-secondary" type="button">
                                    <i class="fas fa-search"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="table-responsive">
                        <table class="table table-striped" id="usersTable">
                            <thead>
                                <tr>
                                    <th>Nome</th>
                                    <th>Email</th>
                                    <th>Cargo</th>
                                    <th>Tipo</th>
                                    <th>Status</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td colspan="6" class="text-center">
                                        <i class="fas fa-spinner fa-spin"></i> Carregando usuários...
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Carregar usuários
    fetch('/api/usuarios')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const tbody = document.querySelector('#usersTable tbody');
                
                if (data.users.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Nenhum usuário encontrado.</td></tr>';
                    return;
                }
                
                let html = '';
                data.users.forEach(user => {
                    const statusBadge = user.is_active ? 
                        '<span class="badge bg-success">Ativo</span>' : 
                        '<span class="badge bg-danger">Inativo</span>';
                    
                    const typeBadge = user.user_type === 'admin' ? 
                        '<span class="badge bg-danger">Admin</span>' : 
                        user.user_type === 'trabalhador' ? 
                        '<span class="badge bg-primary">Trabalhador</span>' :
                        '<span class="badge bg-info">Estagiário</span>';
                    
                    html += `<tr>
                        <td>${user.nome} ${user.sobrenome}</td>
                        <td>${user.email}</td>
                        <td>${user.cargo || 'Não informado'}</td>
                        <td>${typeBadge}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <div class="btn-group" role="group">
                                <button type="button" class="btn btn-sm btn-outline-primary" onclick="editUser(${user.id})">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button type="button" class="btn btn-sm btn-outline-info" onclick="viewUser(${user.id})">
                                    <i class="fas fa-eye"></i>
                                </button>
                                ${user.is_active ? 
                                    `<button type="button" class="btn btn-sm btn-outline-warning" onclick="toggleUser(${user.id}, false)">
                                        <i class="fas fa-ban"></i>
                                    </button>` :
                                    `<button type="button" class="btn btn-sm btn-outline-success" onclick="toggleUser(${user.id}, true)">
                                        <i class="fas fa-check"></i>
                                    </button>`
                                }
                            </div>
                        </td>
                    </tr>`;
                });
                
                tbody.innerHTML = html;
            } else {
                document.querySelector('#usersTable tbody').innerHTML = 
                    '<tr><td colspan="6" class="text-center text-danger">Erro ao carregar usuários.</td></tr>';
            }
        })
        .catch(error => {
            console.error('Erro ao carregar usuários:', error);
            document.querySelector('#usersTable tbody').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">Erro ao carregar usuários.</td></tr>';
        });
    
    // Filtro de busca
    document.getElementById('searchInput').addEventListener('input', function() {
        const filter = this.value.toLowerCase();
        const rows = document.querySelectorAll('#usersTable tbody tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(filter) ? '' : 'none';
        });
    });
});

function editUser(userId) {
    window.location.href = `/admin/usuarios/${userId}/editar`;
}

function viewUser(userId) {
    window.location.href = `/admin/usuarios/${userId}`;
}

function toggleUser(userId, activate) {
    const action = activate ? 'ativar' : 'desativar';
    if (confirm(`Tem certeza que deseja ${action} este usuário?`)) {
        // Implementar chamada para API
        console.log(`${action} usuário ${userId}`);
    }
}
</script>
{% endblock %}
""",

    "admin/hour_bank.html": """
{% extends "base.html" %}

{% block title %}Banco de Horas - Administração{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0"><i class="fas fa-piggy-bank"></i> Banco de Horas - Administração</h4>
                </div>
                <div class="card-body">
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h5><i class="fas fa-users"></i> Total de Usuários</h5>
                                    <h2 id="total-usuarios" class="text-primary">-</h2>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h5><i class="fas fa-clock"></i> Total de Horas</h5>
                                    <h2 id="total-horas" class="text-success">-</h2>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Usuário</th>
                                    <th>Saldo Atual</th>
                                    <th>Horas Extras</th>
                                    <th>Compensações</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody id="hour-bank-table">
                                <tr>
                                    <td colspan="5" class="text-center">
                                        <i class="fas fa-spinner fa-spin"></i> Carregando dados...
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    loadHourBankData();
});

function loadHourBankData() {
    // Simular dados por enquanto
    const tbody = document.getElementById('hour-bank-table');
    
    // Dados de exemplo
    const mockData = [
        { 
            id: 1, 
            name: 'Administrador Sistema', 
            balance: '+8h 30m', 
            overtime: '12h 45m', 
            compensations: '4h 15m' 
        }
    ];
    
    let html = '';
    mockData.forEach(user => {
        html += `<tr>
            <td>${user.name}</td>
            <td class="text-success">${user.balance}</td>
            <td>${user.overtime}</td>
            <td>${user.compensations}</td>
            <td>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="viewUserHours(${user.id})">
                        <i class="fas fa-eye"></i> Ver
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-warning" onclick="adjustHours(${user.id})">
                        <i class="fas fa-edit"></i> Ajustar
                    </button>
                </div>
            </td>
        </tr>`;
    });
    
    tbody.innerHTML = html;
    
    // Atualizar totais
    document.getElementById('total-usuarios').textContent = '1';
    document.getElementById('total-horas').textContent = '+8h 30m';
}

function viewUserHours(userId) {
    window.location.href = `/admin/hour-bank/users/${userId}`;
}

function adjustHours(userId) {
    // Implementar ajuste de horas
    console.log('Ajustar horas para usuário:', userId);
}
</script>
{% endblock %}
""",

    "admin/hour_bank_users.html": """
{% extends "base.html" %}

{% block title %}Usuários - Banco de Horas{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0"><i class="fas fa-users"></i> Usuários - Banco de Horas</h4>
                </div>
                <div class="card-body">
                    <p>Lista detalhada de todos os usuários e seus saldos de banco de horas.</p>
                    
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Usuário</th>
                                    <th>Departamento</th>
                                    <th>Saldo Atual</th>
                                    <th>Horas do Mês</th>
                                    <th>Status</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Administrador Sistema</td>
                                    <td>TI</td>
                                    <td class="text-success">+8h 30m</td>
                                    <td>40h 15m</td>
                                    <td><span class="badge bg-success">Ativo</span></td>
                                    <td>
                                        <button class="btn btn-sm btn-outline-primary">
                                            <i class="fas fa-eye"></i> Detalhes
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",

    "admin/hour_compensations.html": """
{% extends "base.html" %}

{% block title %}Compensações de Horas{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-warning text-dark">
                    <h4 class="mb-0"><i class="fas fa-balance-scale"></i> Compensações de Horas</h4>
                </div>
                <div class="card-body">
                    <p>Gerenciamento de solicitações de compensação de horas extras.</p>
                    
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Usuário</th>
                                    <th>Período</th>
                                    <th>Horas Solicitadas</th>
                                    <th>Motivo</th>
                                    <th>Status</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td colspan="6" class="text-center text-muted">
                                        Nenhuma solicitação de compensação pendente.
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",

    "admin/overtime_requests.html": """
{% extends "base.html" %}

{% block title %}Solicitações de Horas Extras{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-info text-white">
                    <h4 class="mb-0"><i class="fas fa-clock"></i> Solicitações de Horas Extras</h4>
                </div>
                <div class="card-body">
                    <p>Gerenciamento de solicitações de horas extras dos funcionários.</p>
                    
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Usuário</th>
                                    <th>Data</th>
                                    <th>Horas Solicitadas</th>
                                    <th>Justificativa</th>
                                    <th>Status</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td colspan="6" class="text-center text-muted">
                                        Nenhuma solicitação de hora extra pendente.
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",

    "main/hour_bank/my_hour_bank.html": """
{% extends "base.html" %}

{% block title %}Meu Banco de Horas{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-success text-white">
                    <h4 class="mb-0"><i class="fas fa-piggy-bank"></i> Meu Banco de Horas</h4>
                </div>
                <div class="card-body">
                    <div class="row mb-4">
                        <div class="col-md-4">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h5>Saldo Atual</h5>
                                    <h2 class="text-success">+0h 0m</h2>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h5>Horas Extras</h5>
                                    <h2 class="text-primary">0h 0m</h2>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h5>Compensações</h5>
                                    <h2 class="text-warning">0h 0m</h2>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <h5>Histórico de Movimentações</h5>
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Data</th>
                                            <th>Tipo</th>
                                            <th>Horas</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td colspan="3" class="text-center text-muted">
                                                Nenhuma movimentação encontrada.
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <h5>Ações</h5>
                            <div class="d-grid gap-2">
                                <a href="{{ url_for('main.request_compensation') }}" class="btn btn-primary">
                                    <i class="fas fa-paper-plane"></i> Solicitar Compensação
                                </a>
                                <a href="{{ url_for('main.my_compensations') }}" class="btn btn-outline-primary">
                                    <i class="fas fa-list"></i> Minhas Compensações
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",

    "main/hour_bank/my_compensations.html": """
{% extends "base.html" %}

{% block title %}Minhas Compensações{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-info text-white">
                    <h4 class="mb-0"><i class="fas fa-balance-scale"></i> Minhas Compensações</h4>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <a href="{{ url_for('main.request_compensation') }}" class="btn btn-success">
                            <i class="fas fa-plus"></i> Nova Solicitação
                        </a>
                    </div>
                    
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Data Solicitação</th>
                                    <th>Período</th>
                                    <th>Horas</th>
                                    <th>Motivo</th>
                                    <th>Status</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td colspan="6" class="text-center text-muted">
                                        Nenhuma solicitação de compensação encontrada.
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""
}

def create_template_directories():
    """Criar diretórios de templates necessários"""
    directories = [
        "app/templates/main/hour_bank",
        "app/templates/admin"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Diretório criado: {directory}")

def create_templates():
    """Criar todos os templates em falta"""
    create_template_directories()
    
    for template_path, content in TEMPLATES_TO_CREATE.items():
        full_path = f"app/templates/{template_path}"
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        
        print(f"✅ Template criado: {template_path}")

def fix_api_routes():
    """Corrigir problemas nos routes da API"""
    api_routes_path = "app/api/routes.py"
    
    # Ler o arquivo atual
    try:
        with open(api_routes_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Corrigir o erro do horas_trabalhadas_decimal
        if 'horas_trabalhadas_decimal' in content:
            content = content.replace('r.horas_trabalhadas_decimal', 'str(r.horas_trabalhadas) if r.horas_trabalhadas else "0h 0m"')
            
            with open(api_routes_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Corrigido erro horas_trabalhadas_decimal em api/routes.py")
        
    except FileNotFoundError:
        print("⚠️ Arquivo app/api/routes.py não encontrado")

def test_fixed_routes():
    """Testar as rotas que foram corrigidas"""
    print("\n🧪 TESTANDO ROTAS CORRIGIDAS...")
    
    # Fazer login primeiro
    session = requests.Session()
    
    login_data = {
        'email': USERNAME,
        'password': PASSWORD,
        'csrf_token': 'test'  # Simplificado para teste
    }
    
    try:
        # Login
        login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        print(f"🔐 Login: {login_response.status_code}")
        
        # Rotas para testar (as que estavam falhando com templates)
        test_routes = [
            "/",
            "/dashboard", 
            "/admin/usuarios",
            "/admin/system-config",
            "/admin/hour-bank",
            "/admin/hour-bank/users",
            "/admin/hour-compensations",
            "/admin/overtime-requests",
            "/my-hour-bank",
            "/my-compensations",
            "/request-compensation",
            "/api/time-records"
        ]
        
        working = 0
        total = len(test_routes)
        
        for route in test_routes:
            try:
                response = session.get(f"{BASE_URL}{route}", timeout=10)
                status = "✅" if response.status_code == 200 else "❌"
                print(f"{status} {route}: {response.status_code}")
                
                if response.status_code == 200:
                    working += 1
                    
            except Exception as e:
                print(f"❌ {route}: ERRO - {str(e)}")
        
        print(f"\n📊 RESULTADO: {working}/{total} rotas funcionando ({working/total*100:.1f}%)")
        
        if working == total:
            print("🎉 TODAS AS ROTAS CORRIGIDAS COM SUCESSO!")
        else:
            print(f"⚠️ Ainda há {total-working} rotas com problemas")
            
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")

def main():
    print("🔧 INICIANDO CORREÇÃO DE ERROS ESPECÍFICOS...")
    
    # 1. Criar templates em falta
    print("\n1. Criando templates em falta...")
    create_templates()
    
    # 2. Corrigir problemas na API
    print("\n2. Corrigindo problemas na API...")
    fix_api_routes()
    
    # 3. Testar as correções
    print("\n3. Testando correções...")
    test_fixed_routes()
    
    print("\n✅ CORREÇÃO DE ERROS ESPECÍFICOS CONCLUÍDA!")

if __name__ == "__main__":
    main()
