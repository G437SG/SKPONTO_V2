from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from app import db, limiter
from app.auth import bp
from app.models import User, UserType, SecurityLog
from app.forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm
from app.utils import log_security_event, allowed_file, save_uploaded_file
from app.error_handler import monitor_function, ErrorContext, debug_log
import os
from datetime import datetime

@bp.route('/login', methods=['GET', 'POST'])
@monitor_function
def login():
    """Página de login"""
    with ErrorContext("login_process") as ctx:
        ctx.add_context("user_authenticated", current_user.is_authenticated)
        
        if current_user.is_authenticated:
            debug_log("Usuário já autenticado, redirecionando para dashboard")
            return redirect(url_for('main.dashboard'))
        
        form = LoginForm()
        ctx.add_context("form_submitted", request.method == 'POST')
        
        if form.validate_on_submit():
            debug_log(f"Tentativa de login para: {form.email.data}")
            ctx.add_context("email", form.email.data)
            
            # HARDCODED ADMIN CREDENTIALS - INTRINSIC TO THE CODE
            if form.email.data == 'admin@skponto.com' and form.password.data == 'admin123':
                debug_log("Login de administrador detectado")
                # Find or create admin user
                user = User.query.filter_by(email='admin@skponto.com').first()
                if not user:
                    debug_log("Criando usuário administrador")
                    # Create admin user if it doesn't exist
                    user = User(
                        email='admin@skponto.com',
                        cpf='00000000000',
                        nome='Administrador',
                        sobrenome='Sistema',
                        telefone='(00) 00000-0000',
                        user_type=UserType.ADMIN,
                        is_active=True
                    )
                    user.set_password('admin123')
                    db.session.add(user)
                    db.session.commit()
                    debug_log("Usuário administrador criado com sucesso")
                
                # Ensure user is admin and active
                if user.user_type != UserType.ADMIN:
                    user.user_type = UserType.ADMIN
                    db.session.commit()
                if not user.is_active:
                    user.is_active = True
                    db.session.commit()
                
                # Login successful
                login_user(user, remember=True)
                user.last_login = datetime.utcnow()
                ctx.add_context("login_successful", True)
                
                log_security_event('LOGIN_SUCCESS', f'Admin login realizado: {user.email}', user.id)
                flash(f'Bem-vindo(a), {user.nome}!', 'success')
                
                # Redirect to admin dashboard
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('admin.dashboard')
                
                return redirect(next_page)
            
            # Normal user authentication
            user = User.query.filter(User.email.ilike(form.email.data)).first()
            
            if user and user.check_password(form.password.data):
                if not user.is_active:
                    flash('Sua conta está inativa. Entre em contato com o administrador.', 'error')
                    log_security_event('LOGIN_FAILED', f'Tentativa de login com conta inativa: {form.email.data}')
                    return redirect(url_for('auth.login'))
                
                # Login bem-sucedido
                login_user(user, remember=True)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                log_security_event('LOGIN_SUCCESS', f'Login realizado: {user.email}', user.id)
                flash(f'Bem-vindo(a), {user.nome}!', 'success')
                
                # Redirecionar para página solicitada ou dashboard
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    if user.is_admin:
                        next_page = url_for('admin.dashboard')
                    else:
                        next_page = url_for('main.dashboard')
                
                return redirect(next_page)
            else:
                flash('Email ou senha inválidos.', 'error')
                log_security_event('LOGIN_FAILED', f'Credenciais inválidas: {form.email.data}')
    
    return render_template('auth/login.html', title='Login', form=form)

@bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    log_security_event('LOGOUT', f'Logout realizado: {current_user.email}', current_user.id)
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Página de cadastro"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Criar novo usuário (inicialmente inativo)
        user = User(
            nome=form.nome.data,
            sobrenome=form.sobrenome.data,
            email=form.email.data,
            cpf=form.cpf.data,
            user_type=UserType(form.user_type.data),
            is_active=False  # Usuário inativo até aprovação
        )
        user.set_password(form.password.data)
        
        # Processar foto de perfil se enviada
        if form.foto_perfil.data:
            if allowed_file(form.foto_perfil.data.filename):
                filename = save_uploaded_file(form.foto_perfil.data, 'profiles')
                user.foto_perfil = filename
        
        db.session.add(user)
        db.session.flush()  # Para obter o ID do usuário
        
        # Criar solicitação de aprovação
        from app.models import UserApprovalRequest
        approval_request = UserApprovalRequest(
            user_id=user.id,
            user_message=form.user_message.data
        )
        db.session.add(approval_request)
        db.session.commit()
        
        # Log do evento
        log_security_event('USER_REGISTERED', f'Novo usuário cadastrado aguardando aprovação: {user.email}', user.id)
        
        # Criar notificação para administradores
        from app.utils import create_admin_notification
        create_admin_notification(
            f'Nova solicitação de cadastro de {user.nome} {user.sobrenome}',
            f'Usuário {user.email} solicitou cadastro no sistema. Acesse o painel administrativo para aprovar.',
            notification_type='info'
        )
        
        flash(f'Cadastro enviado com sucesso! Sua conta será ativada após aprovação do administrador. Você receberá um email quando aprovada.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Cadastro', form=form)

@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Página de recuperação de senha"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        # Verificar se email e CPF correspondem ao mesmo usuário
        import re
        
        # Limpar CPF digitado pelo usuário (remover tudo que não for número)
        cpf_input_clean = re.sub(r'[^0-9]', '', form.cpf.data)
        
        # Formatar CPF com pontos e traços
        if len(cpf_input_clean) == 11:
            cpf_formatted = (f"{cpf_input_clean[:3]}.{cpf_input_clean[3:6]}."
                           f"{cpf_input_clean[6:9]}-{cpf_input_clean[9:]}")
        else:
            cpf_formatted = ""
        
        # Buscar usuário por email primeiro
        user_by_email = User.query.filter(User.email.ilike(form.email.data)).first()
        
        if user_by_email:
            # Limpar CPF do banco para comparação
            cpf_db_clean = re.sub(r'[^0-9]', '', user_by_email.cpf) if user_by_email.cpf else ""
            
            # Debug logs
            current_app.logger.info(f"CPF digitado: '{form.cpf.data}' -> limpo: '{cpf_input_clean}'")
            current_app.logger.info(f"CPF banco: '{user_by_email.cpf}' -> limpo: '{cpf_db_clean}'")
            
            # Comparar CPFs limpos (apenas números)
            if cpf_input_clean == cpf_db_clean:
                # Em um sistema real, aqui enviaria um email com token
                # Por simplicidade, vamos redirecionar direto para reset
                flash('Dados verificados! Defina sua nova senha.', 'success')
                log_security_event('PASSWORD_RESET_SUCCESS', f'Dados corretos: {form.email.data}', user_by_email.id)
                return redirect(url_for('auth.reset_password', user_id=user_by_email.id))
            else:
                flash('Email e CPF não correspondem a nenhum usuário.', 'error')
                log_security_event('PASSWORD_RESET_FAILED', f'CPF incorreto para {form.email.data}')
        else:
            flash('Email e CPF não correspondem a nenhum usuário.', 'error')
            log_security_event('PASSWORD_RESET_FAILED', f'Email não encontrado: {form.email.data}')
    
    return render_template('auth/forgot_password.html', title='Recuperar Senha', form=form)

@bp.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    """Página de redefinição de senha"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        
        log_security_event('PASSWORD_RESET_SUCCESS', f'Senha redefinida: {user.email}', user.id)
        flash('Senha redefinida com sucesso! Faça login com a nova senha.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', title='Nova Senha', form=form)
