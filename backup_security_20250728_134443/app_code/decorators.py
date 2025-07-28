"""
Decoradores para controle de acesso e funcionalidades administrativas
"""

from functools import wraps
from flask import flash, redirect, url_for, request, abort
from flask_login import current_user

def admin_required(f):
    """Decorator para rotas que requerem acesso de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Acesso negado. Faça login para continuar.', 'error')
            return redirect(url_for('auth.login'))
        
        # Verificar se o usuário é admin (is_admin é uma property, não campo de banco)
        try:
            is_user_admin = getattr(current_user, 'is_admin', False)
            if not is_user_admin:
                flash('Acesso negado. Apenas administradores podem acessar esta página.', 'error')
                return redirect(url_for('main.dashboard'))
        except Exception as e:
            # Log do erro para debug
            print(f"Erro ao verificar admin: {e}")
            flash('Erro ao verificar permissões administrativas.', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def approved_user_required(f):
    """Decorator para rotas que requerem usuário aprovado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Acesso negado. Faça login para continuar.', 'error')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_approved:
            flash('Sua conta está pendente de aprovação pelo administrador.', 'warning')
            return redirect(url_for('auth.pending_approval'))
        
        return f(*args, **kwargs)
    return decorated_function

def active_user_required(f):
    """Decorator para rotas que requerem usuário ativo"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Acesso negado. Faça login para continuar.', 'error')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_active:
            flash('Sua conta foi desativada. Entre em contato com o administrador.', 'error')
            return redirect(url_for('auth.logout'))
        
        return f(*args, **kwargs)
    return decorated_function
