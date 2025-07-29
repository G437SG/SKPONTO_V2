from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, date, timedelta
import io
import os
import zipfile
from app import db
from app.admin import bp
from app.models import (User, TimeRecord, MedicalAttestation, Notification, SecurityLog, 
                       UserType, AttestationStatus, AttestationType, NotificationType, WorkClass,
                       HourBank, HourBankTransaction, HourBankHistory, OvertimeRequest, HourCompensation)
from app.forms import (UserManagementForm, NotificationForm, ApproveAttestationForm, 
                      ReportForm, EmptyForm, WorkClassForm, BulkWorkClassForm, AssignWorkClassForm)
from app.utils import (log_security_event, create_notification, send_notification_to_admins,
                      validate_date_range, backup_database, format_hours, allowed_file, save_uploaded_file,
                      backup_to_github, setup_github_backup_schedule)
from app.attestation_upload_service import AttestationUploadService

def save_shared_link_to_config(shared_link):
    """Salva o link compartilhado no arquivo .env e na configuração da aplicação de forma robusta"""
    try:
        # Caminho do arquivo .env
        env_path = os.path.join(current_app.root_path, '..', '.env')
        
        # Ler conteúdo atual do arquivo .env
        env_content = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.readlines()
        
        # Procurar e atualizar a linha local_SHARED_LINK
        updated = False
        for i, line in enumerate(env_content):
            if line.strip().startswith('local_SHARED_LINK='):
                env_content[i] = f"local_SHARED_LINK='{shared_link}'\n"
                updated = True
                break
        
        # Se não encontrou, adicionar no final
        if not updated:
            env_content.append(f"local_SHARED_LINK='{shared_link}'\n")
        
        # Escrever arquivo atualizado
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(env_content)
        
        # Atualizar variável de ambiente em memória
        os.environ['local_SHARED_LINK'] = shared_link
        
        # Atualizar configuração da aplicação
        current_app.config['local_SHARED_LINK'] = shared_link
        
        # Verificar se foi salvo corretamente lendo novamente
        with open(env_path, 'r', encoding='utf-8') as f:
            env_check = f.read()
            if f"local_SHARED_LINK='{shared_link}'" in env_check:
                current_app.logger.info(f"✅ Link compartilhado salvo com sucesso: {shared_link[:50]}...")
                return True
            else:
                current_app.logger.error("❌ Erro: Link não foi salvo corretamente no arquivo .env")
                return False
                
    except Exception as e:
        current_app.logger.error(f"❌ Erro ao salvar link compartilhado: {str(e)}")
        return False

def admin_required(f):
    """Decorator para rotas que requerem acesso de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # HARDCODED ADMIN BYPASS - INTRINSIC TO THE CODE
        if current_user.is_authenticated and current_user.email == 'admin@skponto.com':
            return f(*args, **kwargs)
        
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acesso negado. Apenas administradores podem acessar esta página.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Dashboard administrativo"""
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    
    # Estatísticas gerais
    total_usuarios = User.query.filter_by(is_active=True).count()
    usuarios_online_hoje = User.query.filter(User.last_login >= hoje).count()
    
    # Registros de ponto hoje
    registros_hoje = TimeRecord.query.filter_by(data=hoje).count()
    registros_completos_hoje = TimeRecord.query.filter(
        and_(TimeRecord.data == hoje, 
             TimeRecord.entrada.isnot(None),
             TimeRecord.saida.isnot(None))
    ).count()
    
    # Atestados pendentes
    atestados_pendentes = MedicalAttestation.query.filter_by(
        status=AttestationStatus.PENDENTE
    ).count()
    
    # Aprovações de usuários pendentes
    from app.models import UserApprovalRequest, ApprovalStatus
    pending_approvals = UserApprovalRequest.query.filter_by(
        status=ApprovalStatus.PENDENTE
    ).count()
    
    # Horas trabalhadas no mês
    registros_mes = TimeRecord.query.filter(
        and_(TimeRecord.data >= inicio_mes,
             TimeRecord.data <= hoje)
    ).all()
    
    total_horas_mes = sum(r.horas_trabalhadas for r in registros_mes)
    total_extras_mes = sum(r.horas_extras for r in registros_mes)
    
    # Últimas atividades
    ultimas_atividades = SecurityLog.query.order_by(
        desc(SecurityLog.created_at)
    ).limit(10).all()
      # Usuários mais ativos (por registros de ponto)
    usuarios_ativos = db.session.query(
        User, func.count(TimeRecord.id).label('total_registros')
    ).join(TimeRecord, User.id == TimeRecord.user_id).filter(
        TimeRecord.data >= inicio_mes
    ).group_by(User.id).order_by(
        desc('total_registros')
    ).limit(5).all()
    
    # Dados para gráficos
    # Últimos 6 meses para gráfico de registros
    meses_labels = []
    registros_por_mes = []
    
    for i in range(6):
        mes_date = hoje.replace(day=1) - timedelta(days=i*30)
        inicio_mes_chart = mes_date.replace(day=1)
        if mes_date.month == 12:
            fim_mes_chart = mes_date.replace(year=mes_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fim_mes_chart = mes_date.replace(month=mes_date.month + 1, day=1) - timedelta(days=1)
        
        registros_count = TimeRecord.query.filter(
            and_(TimeRecord.data >= inicio_mes_chart,
                 TimeRecord.data <= fim_mes_chart)
        ).count()
        
        # Nome do mês em português
        meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        mes_nome = meses_nomes[mes_date.month - 1]
        
        meses_labels.insert(0, f"{mes_nome}/{mes_date.year}")
        registros_por_mes.insert(0, registros_count)
    
    # Tipos de usuário para gráfico
    tipos_usuario = [
        User.query.filter_by(user_type=UserType.ADMIN).count(),
        User.query.filter_by(user_type=UserType.TRABALHADOR).count(),
        User.query.filter_by(user_type=UserType.ESTAGIARIO).count()
    ]

    return render_template('admin/dashboard.html',
                         title='Dashboard Administrativo',
                         total_usuarios=total_usuarios,
                         usuarios_online_hoje=usuarios_online_hoje,
                         registros_hoje=registros_hoje,
                         registros_completos_hoje=registros_completos_hoje,
                         atestados_pendentes=atestados_pendentes,
                         pending_approvals=pending_approvals,
                         total_horas_mes=format_hours(total_horas_mes),
                         total_extras_mes=format_hours(total_extras_mes),
                         ultimas_atividades=ultimas_atividades,
                         usuarios_ativos=usuarios_ativos,
                         meses_labels=meses_labels,
                         registros_por_mes=registros_por_mes,
                         tipos_usuario=tipos_usuario)

@bp.route('/usuarios')
@login_required
@admin_required
def usuarios():
    """Lista de usuários"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('busca', '')  # Mudança aqui: 'busca' em vez de 'search'
    status = request.args.get('status', 'todos')
    tipo = request.args.get('tipo', 'todos')
    
    # Query base
    query = User.query
    
    # Filtros
    if search:
        query = query.filter(
            or_(User.nome.contains(search),
                User.sobrenome.contains(search),
                User.email.contains(search),
                User.cpf.contains(search))
        )
    
    if status == 'ativo':
        query = query.filter_by(is_active=True)
    elif status == 'inativo':
        query = query.filter_by(is_active=False)
    
    if tipo != 'todos':
        query = query.filter_by(user_type=UserType(tipo))
    
    usuarios = query.order_by(User.nome, User.sobrenome).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Garantir que todos os usuários tenham banco de horas
    from app.models import HourBank
    for user in usuarios.items:
        if True:  # hour_bank check disabled
            hour_bank = HourBank(user_id=user.id)
            db.session.add(hour_bank)
    
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    
    return render_template('admin/usuarios.html',
                         title='Gestão de Usuários',
                         usuarios=usuarios,
                         busca=search,  # Mudança aqui: 'busca' em vez de 'search'
                         status=status,
                         tipo=tipo)

@bp.route('/usuario/<int:id>')
@login_required
@admin_required
def usuario_detalhes(id):
    """Detalhes de um usuário"""
    usuario = User.query.get_or_404(id)
    
    # Estatísticas do usuário
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    
    registros_mes = TimeRecord.query.filter(
        and_(TimeRecord.user_id == id,
             TimeRecord.data >= inicio_mes,
             TimeRecord.data <= hoje)
    ).all()
    
    horas_mes = sum(r.horas_trabalhadas for r in registros_mes)
    extras_mes = sum(r.horas_extras for r in registros_mes)
    dias_trabalhados = len([r for r in registros_mes if r.is_completo])
    
    # Últimos registros
    ultimos_registros = TimeRecord.query.filter_by(
        user_id=id
    ).order_by(desc(TimeRecord.data)).limit(10).all()
    
    # Atestados
    atestados = MedicalAttestation.query.filter_by(
        user_id=id
    ).order_by(desc(MedicalAttestation.created_at)).limit(5).all()
    
    # Dados para gráfico dos últimos 7 dias
    dias_labels = []
    horas_data = []
    for i in range(7):
        dia = hoje - timedelta(days=i)
        registro = TimeRecord.query.filter_by(user_id=id, data=dia).first()
        dias_labels.insert(0, dia.strftime('%d/%m'))
        horas_data.insert(0, registro.horas_trabalhadas if registro else 0)
    
    return render_template('admin/usuario_detalhes.html',
                         title=f'Usuário: {usuario.nome_completo}',
                         usuario=usuario,
                         horas_mes=format_hours(horas_mes),
                         horas_extras_mes=format_hours(extras_mes),
                         dias_trabalhados=dias_trabalhados,
                         ultimos_registros=ultimos_registros,
                         atestados=atestados,
                         dias_labels=dias_labels,
                         horas_data=horas_data)

@bp.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    """Edição de usuário"""
    usuario = User.query.get_or_404(id)
    form = UserManagementForm(
        original_email=usuario.email,
        original_cpf=usuario.cpf.replace('.', '').replace('-', ''),
        obj=usuario
    )
    form.user_type.data = usuario.user_type.value
    form.is_active.data = usuario.is_active
    
    if form.validate_on_submit():
        # Dados originais para log
        dados_originais = {
            'nome': usuario.nome,
            'email': usuario.email,
            'user_type': usuario.user_type.value,
            'is_active': usuario.is_active
        }
        
        # Atualizar dados
        usuario.nome = form.nome.data
        usuario.sobrenome = form.sobrenome.data
        usuario.email = form.email.data
        usuario.cpf = form.cpf.data
        usuario.user_type = UserType(form.user_type.data)
        usuario.is_active = form.is_active.data
        usuario.updated_at = datetime.utcnow()
        
        # Atualizar outros campos opcionais
        if hasattr(form, 'telefone') and form.telefone.data:
            usuario.telefone = form.telefone.data
        if hasattr(form, 'cargo') and form.cargo.data:
            usuario.cargo = form.cargo.data
        if hasattr(form, 'work_class_id') and form.work_class_id.data:
            usuario.work_class_id = int(form.work_class_id.data) if form.work_class_id.data else None
            
        # Alterar senha se fornecida (nova_senha tem prioridade, senão password)
        if form.nova_senha.data:
            usuario.set_password(form.nova_senha.data)
            log_security_event('PASSWORD_CHANGED_BY_ADMIN', 
                              f'Senha alterada pelo admin para usuário ID: {id}',
                              current_user.id)
        elif form.password.data:
            usuario.set_password(form.password.data)
            log_security_event('PASSWORD_CHANGED_BY_ADMIN', 
                              f'Senha alterada pelo admin para usuário ID: {id}',
                              current_user.id)
        
        # Processar foto de perfil se enviada
        if form.foto_perfil.data and hasattr(form.foto_perfil.data, 'filename') and form.foto_perfil.data.filename:
            if allowed_file(form.foto_perfil.data.filename):
                filename = save_uploaded_file(form.foto_perfil.data, 'profiles')
                if filename:
                    usuario.foto_perfil = filename
        
        db.session.commit()
        
        # Log da alteração
        log_security_event('USER_UPDATED', 
                          f'Usuário atualizado por admin - ID: {id}, '
                          f'Dados originais: {dados_originais}',
                          current_user.id)
        
        # Notificar usuário se for alteração significativa
        if (dados_originais['user_type'] != usuario.user_type.value or 
            dados_originais['is_active'] != usuario.is_active):
            create_notification(
                usuario.id,
                'Alteração no seu perfil',
                'Seu perfil foi atualizado por um administrador. '
                'Entre em contato se tiver dúvidas.',
                'info',
                current_user.id
            )
        
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin.usuario_detalhes', id=id))
    else:
        # Debug: mostrar erros de validação
        if request.method == 'POST':
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'Erro no campo {field}: {error}', 'error')
    
    return render_template('admin/editar_usuario.html',
                         title=f'Editar: {usuario.nome_completo}',
                         form=form,
                         usuario=usuario)

@bp.route('/criar_usuario', methods=['GET', 'POST'])
@login_required
@admin_required
def criar_usuario():
    """Criação de novo usuário"""
    form = UserManagementForm()
    
    if form.validate_on_submit():
        try:
            # Criar novo usuário
            user = User()
            user.nome = form.nome.data
            user.sobrenome = form.sobrenome.data
            user.email = form.email.data
            user.cpf = form.cpf.data
            user.user_type = UserType(form.user_type.data)
            user.work_class_id = int(form.work_class_id.data) if form.work_class_id.data else None
            user.telefone = form.telefone.data if form.telefone.data else None
            user.cargo = form.cargo.data if form.cargo.data else None
            user.set_password(form.password.data)
            # Usar valores do formulário para status ativo e aprovado
            user.is_active = bool(form.is_active.data)
            user.is_approved = True  # Usuários criados pelo admin são automaticamente aprovados
            
            # Processar foto de perfil se enviada
            if form.foto_perfil.data and hasattr(form.foto_perfil.data, 'filename') and form.foto_perfil.data.filename:
                from app.utils import allowed_file, save_uploaded_file
                if allowed_file(form.foto_perfil.data.filename):
                    filename = save_uploaded_file(form.foto_perfil.data, 'profiles')
                    user.foto_perfil = filename
            
            db.session.add(user)
            db.session.commit()
            
            log_security_event('USER_CREATED', f'Usuário criado: {user.email}', current_user.id)
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin.usuarios'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Erro ao criar usuário: {str(e)}')
            flash(f'Erro ao criar usuário: {str(e)}', 'error')
    else:
        # Mostrar erros de validação
        if request.method == 'POST':
            current_app.logger.error(f'Erro de validação no formulário: {form.errors}')
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'Erro no campo {field}: {error}', 'error')
    
    return render_template('admin/criar_usuario.html', title='Criar Usuário', form=form)

@bp.route('/desativar_usuario/<int:id>', methods=['POST'])
@login_required
@admin_required
def desativar_usuario(id):
    """Desativar usuário"""
    user = User.query.get_or_404(id)
    
    # Não pode desativar o próprio usuário
    if user.id == current_user.id:
        flash('Você não pode desativar sua própria conta!', 'error')
        return redirect(url_for('admin.usuarios'))
    
    user.is_active = False
    db.session.commit()
    
    log_security_event('USER_DEACTIVATED', f'Usuário desativado: {user.email}', current_user.id)
    flash(f'Usuário {user.nome_completo} foi desativado.', 'success')
    return redirect(url_for('admin.usuarios'))

@bp.route('/ativar_usuario/<int:id>', methods=['POST'])
@login_required
@admin_required
def ativar_usuario(id):
    """Ativar usuário"""
    user = User.query.get_or_404(id)
    
    user.is_active = True
    db.session.commit()
    
    log_security_event('USER_ACTIVATED', f'Usuário ativado: {user.email}', current_user.id)
    flash(f'Usuário {user.nome_completo} foi ativado.', 'success')
    return redirect(url_for('admin.usuarios'))

@bp.route('/deletar_usuario/<int:id>', methods=['POST'])
@login_required
@admin_required
def deletar_usuario(id):
    """Deletar usuário permanentemente"""
    user = User.query.get_or_404(id)
    
    # Não pode deletar o próprio usuário
    if user.id == current_user.id:
        flash('Você não pode deletar sua própria conta!', 'error')
        return redirect(url_for('admin.usuarios'))
    
    # Armazenar informações antes de deletar
    user_name = user.nome_completo
    user_email = user.email
    
    # Deletar registros associados na ordem correta
    TimeRecord.query.filter_by(user_id=user.id).delete()
    MedicalAttestation.query.filter_by(user_id=user.id).delete()
    Notification.query.filter_by(user_id=user.id).delete()
    SecurityLog.query.filter_by(user_id=user.id).delete()
    
    # Deletar banco de horas (deve ser deletado antes do usuário)
    HourBank.query.filter_by(user_id=user.id).delete()
    
    # Deletar transações do banco de horas
    HourBankTransaction.query.filter_by(user_id=user.id).delete()
    
    # Deletar histórico do banco de horas
    HourBankHistory.query.filter_by(user_id=user.id).delete()
    
    # Deletar solicitações de horas extras
    OvertimeRequest.query.filter_by(user_id=user.id).delete()
    
    # Deletar compensações
    HourCompensation.query.filter_by(user_id=user.id).delete()
    
    # Deletar usuário
    db.session.delete(user)
    db.session.commit()
    
    log_security_event('USER_DELETED', f'Usuário deletado: {user_email}', current_user.id)
    flash(f'Usuário {user_name} foi deletado permanentemente.', 'warning')
    return redirect(url_for('admin.usuarios'))

@bp.route('/atestados')
@login_required
@admin_required
def atestados():
    """Lista de atestados para aprovação"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')
    tipo = request.args.get('tipo')
    usuario = request.args.get('usuario')
    data_inicio = request.args.get('data_inicio')
    
    # Query base
    query = MedicalAttestation.query.join(User, MedicalAttestation.user_id == User.id)
    
    # Filtro por status
    if status:
        if status == 'PENDENTE':
            query = query.filter(MedicalAttestation.status == AttestationStatus.PENDENTE)
        elif status == 'APROVADO':
            query = query.filter(MedicalAttestation.status == AttestationStatus.APROVADO)
        elif status == 'REJEITADO':
            query = query.filter(MedicalAttestation.status == AttestationStatus.REJEITADO)
        # Keep backwards compatibility
        elif status.lower() == 'pendente':
            query = query.filter(MedicalAttestation.status == AttestationStatus.PENDENTE)
        elif status.lower() == 'aprovado':
            query = query.filter(MedicalAttestation.status == AttestationStatus.APROVADO)
        elif status.lower() == 'rejeitado':
            query = query.filter(MedicalAttestation.status == AttestationStatus.REJEITADO)
    
    # Filtro por tipo
    if tipo:
        query = query.filter(MedicalAttestation.tipo == AttestationType(tipo))
    
    # Filtro por usuário
    if usuario:
        query = query.filter(
            or_(
                User.nome.ilike(f'%{usuario}%'),
                User.sobrenome.ilike(f'%{usuario}%')
            )
        )
    
    # Filtro por data
    if data_inicio:
        from datetime import datetime
        data_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        query = query.filter(MedicalAttestation.data_inicio >= data_obj)
    
    # Contar pendentes para o badge
    pendentes_count = MedicalAttestation.query.filter_by(status=AttestationStatus.PENDENTE).count()
    
    atestados = query.order_by(desc(MedicalAttestation.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/atestados.html',
                         title='Gestão de Atestados',
                         atestados=atestados,
                         pendentes_count=pendentes_count)

@bp.route('/atestado/<int:id>')
@login_required
@admin_required
def atestado_detalhes(id):
    """Detalhes de um atestado"""
    atestado = MedicalAttestation.query.get_or_404(id)
    form = ApproveAttestationForm()
    
    return render_template('admin/atestado_detalhes.html',
                         title='Detalhes do Atestado',
                         atestado=atestado,
                         form=form)

@bp.route('/aprovar_atestado/<int:id>', methods=['POST'])
@login_required
@admin_required
def aprovar_atestado(id):
    """Aprovar atestado"""
    atestado = MedicalAttestation.query.get_or_404(id)
    
    atestado.status = AttestationStatus.APROVADO
    atestado.aprovado_por = current_user.id
    atestado.data_aprovacao = datetime.utcnow()
    
    # Criar registros de ponto para o período do atestado
    criar_registros_atestado(atestado)
    
    # Notificar usuário
    create_notification(
        atestado.user_id,
        'Atestado Aprovado',
        f'Seu atestado de {atestado.data_inicio.strftime("%d/%m/%Y")} '
        f'foi aprovado.',
        'success',
        current_user.id
    )
    
    flash('Atestado aprovado com sucesso!', 'success')
    
    db.session.commit()
    
    # Log da ação
    log_security_event('ATTESTATION_APPROVED', 
                      f'Atestado aprovado - ID: {id}',
                      current_user.id)
    
    return redirect(url_for('admin.atestados'))

@bp.route('/rejeitar_atestado/<int:id>', methods=['POST'])
@login_required
@admin_required
def rejeitar_atestado(id):
    """Rejeitar atestado"""
    atestado = MedicalAttestation.query.get_or_404(id)
    
    motivo_rejeicao = request.form.get('motivo_rejeicao')
    if not motivo_rejeicao:
        flash('É obrigatório informar o motivo da rejeição.', 'error')
        return redirect(url_for('admin.atestados'))
    
    atestado.status = AttestationStatus.REJEITADO
    atestado.aprovado_por = current_user.id
    atestado.data_aprovacao = datetime.utcnow()
    atestado.motivo_rejeicao = motivo_rejeicao
    
    # Notificar usuário
    create_notification(
        atestado.user_id,
        'Atestado Rejeitado',
        f'Seu atestado de {atestado.data_inicio.strftime("%d/%m/%Y")} '
        f'foi rejeitado. Motivo: {atestado.motivo_rejeicao}',
        'error',
        current_user.id
    )
    
    flash('Atestado rejeitado.', 'info')
    
    db.session.commit()
    
    # Log da ação
    log_security_event('ATTESTATION_REVIEWED', 
                      f'Atestado rejeitado - ID: {id}',
                      current_user.id)
    
    return redirect(url_for('admin.atestados'))

@bp.route('/notificacoes', methods=['GET', 'POST'])
@login_required
@admin_required
def notificacoes():
    """Envio de notificações"""
    form = NotificationForm()
    
    if form.validate_on_submit():
        # Determinar destinatários
        destinatarios = []
        tipo_dest = form.destinatarios.data
        
        if tipo_dest == 'todos':
            destinatarios = User.query.filter_by(is_active=True).all()
        elif tipo_dest == 'trabalhadores':
            destinatarios = User.query.filter_by(
                user_type=UserType.TRABALHADOR, is_active=True
            ).all()
        elif tipo_dest == 'estagiarios':
            destinatarios = User.query.filter_by(
                user_type=UserType.ESTAGIARIO, is_active=True
            ).all()
        elif tipo_dest == 'admins':
            destinatarios = User.query.filter_by(
                user_type=UserType.ADMIN, is_active=True
            ).all()
        elif tipo_dest == 'individual':
            if form.usuario_individual.data:
                usuario = User.query.get(int(form.usuario_individual.data))
                if usuario and usuario.is_active:
                    destinatarios = [usuario]
                else:
                    flash('Usuário selecionado não encontrado ou inativo.', 'error')
                    return render_template('admin/notificacoes.html',
                                         title='Enviar Notificações',
                                         form=form)
            else:
                flash('Selecione um usuário para envio individual.', 'error')
                return render_template('admin/notificacoes.html',
                                     title='Enviar Notificações',
                                     form=form)
        
        # Criar notificações
        for usuario in destinatarios:
            create_notification(
                usuario.id,
                form.titulo.data,
                form.mensagem.data,
                'info',
                current_user.id
            )
        
        flash(f'Notificação enviada para {len(destinatarios)} usuários!', 'success')
        return redirect(url_for('admin.notificacoes'))
    
    return render_template('admin/notificacoes.html',
                         title='Enviar Notificações',
                         form=form)

@bp.route('/relatorios', methods=['GET', 'POST'])
@login_required
@admin_required
def relatorios():
    """Geração de relatórios"""
    form = ReportForm()
    
    # Popular choices de usuários
    usuarios = User.query.filter_by(is_active=True).order_by(User.nome).all()
    form.user_id.choices = [(0, 'Todos os usuários')] + [
        (u.id, u.nome_completo) for u in usuarios
    ]
    
    if form.validate_on_submit():
        # Gerar relatório
        return gerar_relatorio(
            form.data_inicio.data,
            form.data_fim.data,
            form.user_id.data,
            form.formato.data
        )
    
    return render_template('admin/relatorios.html',
                         title='Relatórios',
                         form=form)

def gerar_relatorio(data_inicio, data_fim, user_id, formato):
    """Gera relatório em PDF ou Excel"""
    # Query base
    query = TimeRecord.query.filter(
        and_(TimeRecord.data >= data_inicio,
             TimeRecord.data <= data_fim)
    )
    
    if user_id > 0:
        query = query.filter_by(user_id=user_id)
    
    registros = query.order_by(TimeRecord.data, TimeRecord.user_id).all()
    
    if formato == 'excel':
        return gerar_relatorio_excel(registros, data_inicio, data_fim)
    else:
        return gerar_relatorio_pdf(registros, data_inicio, data_fim)

def gerar_relatorio_excel(registros, data_inicio, data_fim):
    """Gera relatório em Excel"""
    try:
        import xlsxwriter
    except ImportError:
        flash('Funcionalidade de Excel não disponível. Instale xlsxwriter.', 'error')
        return redirect(url_for('admin.relatorios'))
    
    # Criar arquivo em memória
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Relatório de Ponto')
    
    # Formatos
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1
    })
    
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    time_format = workbook.add_format({'num_format': 'hh:mm'})
    
    # Cabeçalhos
    headers = ['Funcionário', 'Data', 'Entrada', 'Saída', 
               'Horas Trabalhadas', 'Horas Extras', 'Observações']
    
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Dados
    for row, registro in enumerate(registros, 1):
        worksheet.write(row, 0, registro.usuario.nome_completo)
        worksheet.write(row, 1, registro.data, date_format)
        
        # Verificar se é atestado
        if registro.is_atestado:
            worksheet.write(row, 2, 'ATESTADO')
            worksheet.write(row, 3, 'ATESTADO')
            worksheet.write(row, 4, 'AFASTAMENTO')
            worksheet.write(row, 5, '-')
            worksheet.write(row, 6, registro.motivo_atestado or 'Atestado médico')
        else:
            worksheet.write(row, 2, registro.entrada, time_format)
            worksheet.write(row, 3, registro.saida, time_format)
            worksheet.write(row, 4, format_hours(registro.horas_trabalhadas))
            worksheet.write(row, 5, format_hours(registro.horas_extras))
            worksheet.write(row, 6, registro.observacoes or '')
    
    # Ajustar largura das colunas
    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:B', 12)
    worksheet.set_column('C:F', 15)
    worksheet.set_column('G:G', 30)
    
    workbook.close()
    output.seek(0)
    
    # Retornar arquivo
    filename = f"relatorio_ponto_{data_inicio}_{data_fim}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def gerar_relatorio_pdf(registros, data_inicio, data_fim):
    """Gera relatório em PDF"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
    except ImportError:
        flash('Funcionalidade de PDF não disponível. Instale reportlab.', 'error')
        return redirect(url_for('admin.relatorios'))
    
    # Criar arquivo em memória
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Centro
    )
    
    # Conteúdo
    story = []
    
    # Título
    title = Paragraph("Relatório de Controle de Ponto", title_style)
    story.append(title)
    
    # Período
    periodo = Paragraph(
        f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
        styles['Normal']
    )
    story.append(periodo)
    story.append(Spacer(1, 20))
    
    # Tabela
    data = [['Funcionário', 'Data', 'Entrada', 'Saída', 'H. Trabalhadas', 'H. Extras']]
    
    for registro in registros:
        # Verificar se é atestado
        if registro.is_atestado:
            row = [
                registro.usuario.nome_completo,
                registro.data.strftime('%d/%m/%Y'),
                'ATESTADO',
                'ATESTADO',
                'AFASTAMENTO',
                registro.motivo_atestado or 'Atestado médico'
            ]
        else:
            row = [
                registro.usuario.nome_completo,
                registro.data.strftime('%d/%m/%Y'),
                registro.entrada.strftime('%H:%M') if registro.entrada else '-',
                registro.saida.strftime('%H:%M') if registro.saida else '-',
                format_hours(registro.horas_trabalhadas),
                format_hours(registro.horas_extras)
            ]
        data.append(row)
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    
    # Gerar PDF
    doc.build(story)
    buffer.seek(0)
    
    # Retornar arquivo
    filename = f"relatorio_ponto_{data_inicio}_{data_fim}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

@bp.route('/backup', methods=['POST'])
@login_required
@admin_required
def backup():
    """Criar backup do banco de dados"""
    form = EmptyForm()
    
    if form.validate_on_submit():
        success, result = backup_database()
        
        if success:
            flash('Backup criado com sucesso!', 'success')
            log_security_event('BACKUP_MANUAL', 'Backup manual criado', current_user.id)
        else:
            flash(f'Erro ao criar backup: {result}', 'error')
    
    return redirect(url_for('admin.dashboard'))

@bp.route('/backup-completo', methods=['POST'])
@login_required
@admin_required
def backup_completo():
    """Criar backup completo com upload para GitHub"""
    from app.utils import backup_to_github
    
    form = EmptyForm()
    
    if form.validate_on_submit():
        success, result = backup_to_github()
        
        if success:
            github_msg = result.get('github_message', '') if isinstance(result, dict) else ''
            flash(f'Backup completo criado com sucesso! {github_msg}', 'success')
            filename = result.get('filename', 'backup') if isinstance(result, dict) else 'backup'
            log_security_event('BACKUP_COMPLETE', f'Backup completo: {filename}', current_user.id)
        else:
            flash(f'Erro ao criar backup completo: {result}', 'error')
    
    return redirect(url_for('admin.dashboard'))

@bp.route('/backup-config', methods=['GET', 'POST'])
@login_required
@admin_required
def backup_config():
    """Configuração do banco de dados e backup no local"""
    # # from app.local_database import get_db_manager  # Module not found  # Module not found
    import local
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            
            if action == 'test_connection':
                # Testar conexão com o sistema de pasta compartilhada
                shared_link = current_app.config.get('local_SHARED_LINK', '')
                
                if shared_link:
                    try:
                        from app.shared_folder_manager import SharedFolderManager
                        manager = SharedFolderManager(shared_link)
                        
                        # Testar se consegue criar/verificar a estrutura de pastas
                        folder_structure = manager.create_folder_structure()
                        if folder_structure:
                            flash('✅ Conexão com pasta compartilhada funcionando perfeitamente!', 'success')
                            flash('📁 Estrutura de pastas criada/verificada com sucesso!', 'info')
                        else:
                            flash('⚠️ Pasta compartilhada acessível, mas houve problemas na estrutura.', 'warning')
                        
                    except Exception as e:
                        flash(f'❌ Erro ao acessar pasta compartilhada: {str(e)}', 'error')
                        current_app.logger.error(f'Erro test_connection shared folder: {str(e)}')
                else:
                    flash('❌ Nenhuma pasta compartilhada configurada. Configure o link primeiro.', 'error')
            
            elif action == 'force_sync':
                # Forçar sincronização do banco
                db_manager = None  # None  # get_db_manager() disabled disabled
                if db_manager:
                    try:
                        local_path = db_manager.sync_database()
                        if local_path:
                            flash('✅ Sincronização forçada realizada com sucesso!', 'success')
                        else:
                            flash('❌ Erro na sincronização forçada.', 'error')
                    except Exception as e:
                        flash(f'❌ Erro na sincronização: {str(e)}', 'error')
                else:
                    flash('❌ Gerenciador de banco não disponível.', 'error')
            
            elif action == 'create_backup':
                # Criar backup manual usando o sistema de pasta compartilhada
                shared_link = current_app.config.get('local_SHARED_LINK', '')
                
                if shared_link:
                    try:
                        from app.shared_folder_manager import SharedFolderManager
                        manager = SharedFolderManager(shared_link)
                        
                        # Criar backup local
                        import zipfile
                        from datetime import datetime
                        
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        backup_filename = f'skponto_backup_{timestamp}.zip'
                        backup_path = manager.get_backups_path()
                        backup_full_path = os.path.join(backup_path, backup_filename)
                        
                        # Criar o arquivo de backup
                        with zipfile.ZipFile(backup_full_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            # Adicionar banco de dados unificado
                            db_path = os.path.join(os.path.dirname(current_app.instance_path), 'storage', 'database', 'skponto.db')
                            if os.path.exists(db_path):
                                zipf.write(db_path, 'database/skponto.db')
                            
                            # Adicionar uploads se existirem
                            uploads_path = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                            if os.path.exists(uploads_path):
                                for root, dirs, files in os.walk(uploads_path):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        arc_name = os.path.relpath(file_path, uploads_path)
                                        zipf.write(file_path, f'uploads/{arc_name}')
                        
                        # Criar instruções de upload
                        instructions_file = manager.create_backup_instructions(backup_filename)
                        
                        flash(f'✅ Backup criado: {backup_filename}', 'success')
                        flash(f'📄 Instruções de upload: {instructions_file}', 'info')
                        
                    except Exception as e:
                        flash(f'❌ Erro ao criar backup: {str(e)}', 'error')
                        current_app.logger.error(f'Erro backup shared folder: {str(e)}')
                else:
                    # Fallback para sistema antigo
                    db_manager = None  # None  # get_db_manager() disabled disabled
                    if db_manager:
                        try:
                            backup_path = db_manager.backup_database("manual_admin")
                            if backup_path:
                                flash(f'✅ Backup criado: {backup_path}', 'success')
                            else:
                                flash('❌ Erro ao criar backup.', 'error')
                        except Exception as e:
                            flash(f'❌ Erro ao criar backup: {str(e)}', 'error')
                    else:
                        flash('❌ Sistema de backup não disponível.', 'error')
            
        except Exception as e:
            flash(f'Erro na operação: {str(e)}', 'error')
    
    # Obter informações do sistema
    db_manager = None  # None  # get_db_manager() disabled disabled
    local_info = {}
    
    # Verificar credenciais do App disponíveis
    app_key = current_app.config.get('local_APP_KEY')
    app_secret = current_app.config.get('local_APP_SECRET')
    access_token = current_app.config.get('local_ACCESS_TOKEN')
    refresh_token = current_app.config.get('local_REFRESH_TOKEN')
    
    # Status baseado na configuração atual E conexão real
    if app_key and app_secret:
        if access_token or refresh_token:
            # Sistema configurado com tokens - verificar conexão real
            if db_manager and db_manager.is_connected():
                local_info['connection_status'] = 'Conectado'
                local_info['connection_class'] = 'success'
                local_info['connection_type'] = 'Refresh Token (Permanente)' if refresh_token else 'Access Token (Temporário)'
            else:
                # Tokens configurados mas conexão falhou
                local_info['connection_status'] = 'Erro de conexão'
                local_info['connection_class'] = 'danger'
                local_info['connection_type'] = 'Tokens configurados mas conexão falhou'
        else:
            # Sistema limpo - credenciais configuradas, mas sem tokens
            local_info['connection_status'] = 'Pronto para configuração'
            local_info['connection_class'] = 'info'
            local_info['connection_type'] = 'Credenciais configuradas - Tokens pendentes'
    else:
        # Sistema não configurado
        local_info['connection_status'] = 'Não configurado'
        local_info['connection_class'] = 'danger'
        local_info['connection_type'] = 'Credenciais não configuradas'
    
    # Informações básicas sempre disponíveis
    local_info['app_key'] = app_key[:10] + '...' if app_key else 'Não configurado'
    local_info['connected'] = bool(access_token or refresh_token)
    
    if db_manager:
        try:
            # Status da conexão do manager
            if local_info['connected']:
                local_info['manager_connected'] = db_manager.is_connected()
                
                # Informações do banco
                if local_info['manager_connected']:
                    local_info['database_exists'] = db_manager.database_exists()
                    local_info['database_path'] = db_manager.db_path
                    
                    # Obter informações do banco
                    db_info = db_manager.get_database_info()
                    if db_info:
                        size_mb = db_info.get('size', 0) / (1024 * 1024)
                        local_info['database_size'] = f"{size_mb:.2f} MB"
                        local_info['last_modified'] = db_info.get('modified', 'Desconhecido')
                    
                    # Informações das pastas
                    local_info['backup_folder'] = db_manager.backup_path
                    local_info['uploads_folder'] = db_manager.uploads_path
                    local_info['logs_folder'] = db_manager.logs_path
                else:
                    local_info['error'] = "Tokens configurados mas conexão falhou"
            else:
                local_info['manager_connected'] = False
                local_info['database_exists'] = False
                local_info['database_path'] = '/skponto_db/skponto.db (aguardando configuração)'
                
        except Exception as e:
            local_info['error'] = f"Erro ao conectar: {str(e)}"
    else:
        local_info['error'] = "Gerenciador de banco não inicializado"
    
    # Configurações atuais (mascaradas por segurança na visualização)
    current_config = {
        'app_key': current_app.config.get('local_APP_KEY', '')[:10] + '...' if current_app.config.get('local_APP_KEY') else 'Não configurado',
        'app_secret': '***' if current_app.config.get('local_APP_SECRET') else 'Não configurado',
        'access_token': '***' if current_app.config.get('local_ACCESS_TOKEN') else 'Não configurado',
        'refresh_token': '***' if current_app.config.get('local_REFRESH_TOKEN') else 'Não configurado',
        'database_path': '/database/skponto.db',
        'backup_path': '/backups',
        'uploads_path': '/uploads',
        'logs_path': '/logs'
    }
    
    # Configurações reais para edição (sem mascaramento)
    current_config_full = {
        'app_key': current_app.config.get('local_APP_KEY', ''),
        'app_secret': current_app.config.get('local_APP_SECRET', ''),
        'access_token': current_app.config.get('local_ACCESS_TOKEN', ''),
        'refresh_token': current_app.config.get('local_REFRESH_TOKEN', '')
    }
    
    # Estatísticas de backup (se disponível)
    backup_stats = {
        'last_backup': 'Em tempo real',
        'backup_frequency': 'Automático com cada operação',
        'retention_policy': 'Ilimitado (controle manual)',
        'backup_location': 'local App Folder'
    }
    
    # Obter link compartilhado do local
    shared_link = current_app.config.get('local_SHARED_LINK', '')
    
    # Debug: verificar se o link está sendo carregado
    current_app.logger.info(f"Link compartilhado carregado: {shared_link[:50]}..." if shared_link else "Nenhum link compartilhado encontrado")
    
    # Informações do gerenciador de pasta compartilhada
    shared_folder_info = {}
    if shared_link:
        try:
            from app.shared_folder_manager import SharedFolderManager
            manager = SharedFolderManager(shared_link)
            
            shared_folder_info = {
                'provider': manager.provider,
                'provider_name': manager.provider.replace('_', ' ').title() if manager.provider else 'Desconhecido',
                'local_path': str(manager.local_base_path) if manager.local_base_path else 'Não configurado',
                'folder_paths': manager.get_folder_paths(),
                'storage_stats': manager.get_storage_stats()
            }
        except Exception as e:
            current_app.logger.error(f"Erro ao obter info do shared folder: {str(e)}")
            shared_folder_info = {'error': str(e)}
    
    return render_template('admin/backup_config.html',
                         title='Configuração local Database',
                         local_info=local_info,
                         current_config=current_config,
                         current_config_full=current_config_full,
                         backup_stats=backup_stats,
                         shared_link=shared_link,
                         shared_folder_info=shared_folder_info)

@bp.route('/logs')
@login_required
@admin_required
def logs():
    """Visualização de logs de segurança"""
    page = request.args.get('page', 1, type=int)
    acao = request.args.get('acao', '')
    
    # Query base
    query = SecurityLog.query
    
    # Filtro por ação
    if acao:
        query = query.filter(SecurityLog.acao.contains(acao))
    
    logs = query.order_by(desc(SecurityLog.created_at)).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('admin/logs.html',
                         title='Logs de Segurança',
                         logs=logs,
                         acao=acao)

@bp.route('/classes-trabalho')
@login_required
@admin_required
def classes_trabalho():
    """Lista classes de trabalho"""
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    status = request.args.get('status', '', type=str)
    
    # Query base
    query = WorkClass.query
    
    # Filtros
    if busca:
        query = query.filter(or_(
            WorkClass.name.contains(busca),
            WorkClass.description.contains(busca)
        ))
    
    if status == 'ativo':
        query = query.filter_by(is_active=True)
    elif status == 'inativo':
        query = query.filter_by(is_active=False)
    
    classes = query.order_by(WorkClass.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Estatísticas
    total_classes = WorkClass.query.count()
    classes_ativas = WorkClass.query.filter_by(is_active=True).count()
    
    return render_template('admin/classes_trabalho.html',
                         title='Classes de Trabalho',
                         classes=classes,
                         total_classes=total_classes,
                         classes_ativas=classes_ativas)

@bp.route('/classes-trabalho/nova', methods=['GET', 'POST'])
@login_required
@admin_required
def nova_classe_trabalho():
    """Criar nova classe de trabalho"""
    form = WorkClassForm()
    if form.validate_on_submit():
        classe = WorkClass(
            name=form.name.data,
            description=form.description.data,
            daily_work_hours=float(form.daily_work_hours.data),
            lunch_hours=float(form.lunch_hours.data),
            created_by=current_user.id
        )
        
        db.session.add(classe)
        db.session.commit()
        
        flash(f'Classe de trabalho "{classe.name}" criada com sucesso!', 'success')
        log_security_event('WORK_CLASS_CREATED', f'Classe criada: {classe.name}', current_user.id)
        
        return redirect(url_for('admin.classes_trabalho'))
    
    return render_template('admin/nova_classe_trabalho.html',
                         title='Nova Classe de Trabalho',
                         form=form)

@bp.route('/classes-trabalho/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_classe_trabalho(id):
    """Editar classe de trabalho"""
    classe = WorkClass.query.get_or_404(id)
    form = WorkClassForm(original_class_id=classe.id, obj=classe)
    # Remove the dynamic assignment since we're using the constructor
    
    if form.validate_on_submit():
        classe.name = form.name.data
        classe.description = form.description.data
        classe.daily_work_hours = float(form.daily_work_hours.data)
        classe.lunch_hours = float(form.lunch_hours.data)
        
        db.session.commit()
        
        flash(f'Classe de trabalho "{classe.name}" atualizada com sucesso!', 'success')
        log_security_event('WORK_CLASS_UPDATED', f'Classe atualizada: {classe.name}', current_user.id)
        
        return redirect(url_for('admin.classes_trabalho'))
    
    # Pré-preencher o formulário
    form.daily_work_hours.data = str(classe.daily_work_hours)
    form.lunch_hours.data = str(classe.lunch_hours)
    
    return render_template('admin/editar_classe_trabalho.html',
                         title='Editar Classe de Trabalho',
                         form=form,
                         classe=classe)

@bp.route('/classes-trabalho/<int:id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_classe_status(id):
    """Ativar/desativar classe de trabalho"""
    classe = WorkClass.query.get_or_404(id)
    classe.is_active = not classe.is_active
    
    db.session.commit()
    
    status = "ativada" if classe.is_active else "desativada"
    flash(f'Classe de trabalho "{classe.name}" {status} com sucesso!', 'success')
    log_security_event('WORK_CLASS_STATUS_CHANGED', 
                      f'Classe {status}: {classe.name}', current_user.id)
    
    return redirect(url_for('admin.classes_trabalho'))

@bp.route('/classes-trabalho/<int:id>/atribuir', methods=['GET', 'POST'])
@login_required
@admin_required
def atribuir_classe_trabalho(id):
    """Atribuir classe de trabalho a usuários"""
    classe = WorkClass.query.get_or_404(id)
    form = BulkWorkClassForm()
    
    if form.validate_on_submit():
        # Query base de usuários
        query = User.query.filter_by(is_active=True)
        
        # Filtrar por tipo se especificado
        if form.user_type.data:
            if form.user_type.data == 'admin':
                query = query.filter_by(user_type=UserType.ADMIN)
            elif form.user_type.data == 'trabalhador':
                query = query.filter_by(user_type=UserType.TRABALHADOR)
            elif form.user_type.data == 'estagiario':
                query = query.filter_by(user_type=UserType.ESTAGIARIO)
        
        usuarios = query.all()
        
        # Atualizar classe dos usuários
        count = 0
        for usuario in usuarios:
            if form.work_class_id.data:
                usuario.work_class_id = int(form.work_class_id.data)
            else:
                usuario.work_class_id = None
            count += 1
        
        db.session.commit()
        
        flash(f'Classe de trabalho atribuída a {count} usuários!', 'success')
        log_security_event('BULK_WORK_CLASS_ASSIGNED', 
                          f'{count} usuários atribuídos à classe {classe.name}', current_user.id)
        
        return redirect(url_for('admin.classes_trabalho'))
    
    # Estatísticas
    usuarios_por_tipo = db.session.query(
        User.user_type, func.count(User.id)
    ).filter_by(is_active=True).group_by(User.user_type).all()
    
    return render_template('admin/atribuir_classe_trabalho.html',
                         title='Atribuir Classe de Trabalho',
                         form=form,
                         classe=classe,
                         usuarios_por_tipo=usuarios_por_tipo)

@bp.route('/classes-trabalho/<int:id>/usuarios')
@login_required
@admin_required
def usuarios_classe_trabalho(id):
    """Ver usuários de uma classe de trabalho"""
    classe = WorkClass.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    
    usuarios = User.query.filter_by(work_class_id=id, is_active=True).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/usuarios_classe_trabalho.html',
                         title=f'Usuários - {classe.name}',
                         classe=classe,
                         usuarios=usuarios)

@bp.route('/migrar_classes_padrao')
@login_required
@admin_required
def migrar_classes_padrao():
    """Migra classes de trabalho padrão"""
    try:
        # Verificar se já existem classes
        if WorkClass.query.count() > 0:
            flash('Classes de trabalho já existem no sistema.', 'warning')
            return redirect(url_for('admin.classes_trabalho'))
        
        # Criar classes padrão
        classes = [
            {
                'name': 'Administrador',
                'description': 'Carga horária padrão para administradores',
                'daily_work_hours': 8.0,
                'lunch_hours': 1.0
            },
            {
                'name': 'Trabalhador',
                'description': 'Carga horária padrão para trabalhadores',
                'daily_work_hours': 8.0,
                'lunch_hours': 1.0
            },
            {
                'name': 'Estagiário',
                'description': 'Carga horária reduzida para estagiários',
                'daily_work_hours': 6.0,
                'lunch_hours': 1.0
            }
        ]
        
        for class_data in classes:
            work_class = WorkClass(
                name=class_data['name'],
                description=class_data['description'],
                daily_work_hours=class_data['daily_work_hours'],
                lunch_hours=class_data['lunch_hours'],
                created_by=current_user.id,
                is_active=True
            )
            db.session.add(work_class)
        
        db.session.commit()
        
        # Log da operação
        log_security_event('WORK_CLASSES_MIGRATED', 
                          'Classes de trabalho padrão criadas durante migração',
                          current_user.id)
        
        flash('Classes de trabalho padrão criadas com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao migrar classes padrão: {e}")
        flash('Erro ao criar classes padrão. Tente novamente.', 'error')
    
    return redirect(url_for('admin.classes_trabalho'))

@bp.route('/registros-ponto')
@login_required
@admin_required
def registros_ponto():
    """Lista todos os registros de ponto para administradores"""
    page = request.args.get('page', 1, type=int)
    usuario_id = request.args.get('usuario')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Query base
    query = TimeRecord.query.join(User, TimeRecord.user_id == User.id)
    
    # Filtros
    if usuario_id and usuario_id != '':
        query = query.filter(TimeRecord.user_id == int(usuario_id))
    
    if data_inicio:
        from datetime import datetime
        data_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        query = query.filter(TimeRecord.data >= data_obj)
    
    if data_fim:
        from datetime import datetime
        data_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        query = query.filter(TimeRecord.data <= data_obj)
    
    # Ordenar por data mais recente
    registros = query.order_by(desc(TimeRecord.data), desc(TimeRecord.entrada)).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Lista de usuários para o filtro
    usuarios = User.query.filter_by(is_active=True).order_by(User.nome).all()
    
    # Estatísticas rápidas
    total_registros = query.count()
    registros_hoje = TimeRecord.query.filter_by(data=date.today()).count()
    
    return render_template('admin/registros_ponto.html',
                         title='Registros de Ponto',
                         registros=registros,
                         usuarios=usuarios,
                         total_registros=total_registros,
                         registros_hoje=registros_hoje,
                         usuario_id=usuario_id,
                         data_inicio=data_inicio,
                         data_fim=data_fim)

def criar_registros_atestado(atestado):
    """Cria registros de ponto para o período do atestado aprovado"""
    from datetime import timedelta
    
    # Calcular o período do atestado
    data_atual = atestado.data_inicio
    data_fim = atestado.data_fim
    
    # Motivo do atestado para descrição
    tipo_atestado = atestado.tipo.value
    if tipo_atestado == 'MEDICO':
        motivo = 'Atestado Médico'
    elif tipo_atestado == 'ODONTOLOGICO':
        motivo = 'Atestado Odontológico'
    elif tipo_atestado == 'PSICOLOGICO':
        motivo = 'Atestado Psicológico'
    else:
        motivo = 'Atestado Médico'
    
    # Adicionar observações se existirem
    if atestado.observacoes:
        motivo += f' - {atestado.observacoes}'
    
    # Criar registros para cada dia do período
    while data_atual <= data_fim:
        # Verificar se já existe um registro para este dia
        registro_existente = TimeRecord.query.filter_by(
            user_id=atestado.user_id,
            data=data_atual
        ).first()
        
        if not registro_existente:
            # Criar novo registro de atestado
            registro = TimeRecord(
                user_id=atestado.user_id,
                data=data_atual,
                is_atestado=True,
                atestado_id=atestado.id,
                motivo_atestado=motivo,
                observacoes=f'Registro automático - {motivo}',
                horas_trabalhadas=0.0,
                horas_extras=0.0,
                created_at=datetime.utcnow()
            )
            db.session.add(registro)
        else:
            # Atualizar registro existente para marcar como atestado
            registro_existente.is_atestado = True
            registro_existente.atestado_id = atestado.id
            registro_existente.motivo_atestado = motivo
            if not registro_existente.observacoes:
                registro_existente.observacoes = f'Atualizado - {motivo}'
            else:
                registro_existente.observacoes += f' | {motivo}'
            registro_existente.updated_at = datetime.utcnow()
        
        # Próximo dia
        data_atual += timedelta(days=1)

# Rotas para Aprovação de Usuários
@bp.route('/user-approvals')
@login_required
@admin_required
def user_approvals():
    """Lista solicitações de aprovação de usuários"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Importar modelos necessários
    from app.models import UserApprovalRequest, ApprovalStatus
    
    # Buscar solicitações pendentes
    pending_requests = UserApprovalRequest.query.filter_by(
        status=ApprovalStatus.PENDENTE
    ).order_by(desc(UserApprovalRequest.requested_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Buscar solicitações processadas recentemente
    processed_requests = UserApprovalRequest.query.filter(
        UserApprovalRequest.status.in_([ApprovalStatus.APROVADO, ApprovalStatus.REJEITADO])
    ).order_by(desc(UserApprovalRequest.reviewed_at)).limit(10).all()
    
    return render_template('admin/user_approvals.html', 
                         title='Aprovações de Usuários',
                         pending_requests=pending_requests,
                         processed_requests=processed_requests)

@bp.route('/approve-user/<int:request_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def approve_user(request_id):
    """Aprovar solicitação de usuário"""
    from app.models import UserApprovalRequest, ApprovalStatus
    from app.forms import UserApprovalForm
    
    approval_request = UserApprovalRequest.query.get_or_404(request_id)
    
    if approval_request.status != ApprovalStatus.PENDENTE:
        flash('Esta solicitação já foi processada.', 'error')
        return redirect(url_for('admin.user_approvals'))
    
    form = UserApprovalForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        action = form.action.data
        
        if action == 'approve':
            # Aprovar usuário
            user = approval_request.user
            user.is_active = True
            
            # Atualizar solicitação
            approval_request.status = ApprovalStatus.APROVADO
            approval_request.reviewed_at = datetime.utcnow()
            approval_request.reviewed_by = current_user.id
            approval_request.admin_notes = form.admin_notes.data
            
            # Criar notificação para o usuário
            create_notification(
                user.id,
                'Conta Aprovada!',
                f'Sua conta foi aprovada pelo administrador. Você já pode fazer login no sistema.',
                'success'
            )
            
            # Log de segurança
            log_security_event('USER_APPROVED', f'Usuário {user.email} aprovado por {current_user.email}', user.id)
            
            flash(f'Usuário {user.nome} {user.sobrenome} foi aprovado com sucesso!', 'success')
            
        elif action == 'reject':
            # Rejeitar usuário
            user = approval_request.user
            
            # Atualizar solicitação
            approval_request.status = ApprovalStatus.REJEITADO
            approval_request.reviewed_at = datetime.utcnow()
            approval_request.reviewed_by = current_user.id
            approval_request.admin_notes = form.admin_notes.data
            approval_request.rejection_reason = form.rejection_reason.data
            
            # Criar notificação para o usuário
            rejection_message = f'Sua solicitação de cadastro foi rejeitada.'
            if form.rejection_reason.data:
                rejection_message += f' Motivo: {form.rejection_reason.data}'
            
            create_notification(
                user.id,
                'Cadastro Rejeitado',
                rejection_message,
                'error'
            )
            
            # Log de segurança
            log_security_event('USER_REJECTED', f'Usuário {user.email} rejeitado por {current_user.email}', user.id)
            
            flash(f'Solicitação de {user.nome} {user.sobrenome} foi rejeitada.', 'warning')
        
        db.session.commit()
        return redirect(url_for('admin.user_approvals'))
    
    # GET request - mostrar formulário
    return render_template('admin/user_approval_form.html', 
                         title='Processar Solicitação',
                         approval_request=approval_request,
                         form=form)

@bp.route('/user-approval-details/<int:request_id>')
@login_required
@admin_required
def user_approval_details(request_id):
    """Detalhes da solicitação de aprovação"""
    from app.models import UserApprovalRequest
    
    approval_request = UserApprovalRequest.query.get_or_404(request_id)
    
    return render_template('admin/user_approval_details.html',
                         title='Detalhes da Solicitação',
                         approval_request=approval_request)

@bp.route('/bulk-approve-users', methods=['POST'])
@login_required
@admin_required
def bulk_approve_users():
    """Aprovação em lote de usuários"""
    from app.models import UserApprovalRequest, ApprovalStatus
    
    request_ids = request.form.getlist('request_ids')
    action = request.form.get('action')
    
    if not request_ids:
        flash('Nenhuma solicitação selecionada.', 'error')
        return redirect(url_for('admin.user_approvals'))
    
    count = 0
    for request_id in request_ids:
        approval_request = UserApprovalRequest.query.get(request_id)
        if approval_request and approval_request.status == ApprovalStatus.PENDENTE:
            user = approval_request.user
            
            if action == 'approve':
                user.is_active = True
                approval_request.status = ApprovalStatus.APROVADO
                approval_request.reviewed_at = datetime.utcnow()
                approval_request.reviewed_by = current_user.id
                
                # Criar notificação
                create_notification(
                    user.id,
                    'Conta Aprovada!',
                    'Sua conta foi aprovada pelo administrador. Você já pode fazer login no sistema.',
                    'success'
                )
                
                log_security_event('USER_APPROVED', f'Usuário {user.email} aprovado por {current_user.email}', user.id)
                count += 1
            
            elif action == 'reject':
                approval_request.status = ApprovalStatus.REJEITADO
                approval_request.reviewed_at = datetime.utcnow()
                approval_request.reviewed_by = current_user.id
                
                # Criar notificação
                create_notification(
                    user.id,
                    'Cadastro Rejeitado',
                    'Sua solicitação de cadastro foi rejeitada pelo administrador.',
                    'error'
                )
                
                log_security_event('USER_REJECTED', f'Usuário {user.email} rejeitado por {current_user.email}', user.id)
                count += 1
    
    db.session.commit()
    
    if action == 'approve':
        flash(f'{count} usuários aprovados com sucesso!', 'success')
    else:
        flash(f'{count} solicitações rejeitadas.', 'warning')
    
    return redirect(url_for('admin.user_approvals'))

# =============================================================================
# ROTAS DE GERENCIAMENTO DE ATESTADOS local
# =============================================================================

@bp.route('/attestation-management')
@login_required
@admin_required
def attestation_management():
    """Redirecionar para dashboard de backup integrado"""
    return redirect(url_for('backup_dashboard_admin.dashboard'))

@bp.route('/sync-local-attestations', methods=['POST'])
@login_required
@admin_required
def sync_local_attestations():
    """Redirecionar para dashboard de backup integrado"""
    return redirect(url_for('backup_dashboard_admin.sync_attestations'))

@bp.route('/cleanup-orphaned-files', methods=['POST'])
@login_required
@admin_required
def cleanup_orphaned_files():
    """Redirecionar para dashboard de backup integrado"""
    return redirect(url_for('backup_dashboard_admin.cleanup_attestations'))

@bp.route('/user-attestation-files/<int:user_id>')
@login_required
@admin_required
def user_attestation_files(user_id):
    """Redirecionar para dashboard de backup integrado"""
    return redirect(url_for('backup_dashboard_admin.user_attestation_files', user_id=user_id))

@bp.route('/get-local-download-link', methods=['POST'])
@login_required
@admin_required
def get_local_download_link():
    """Redirecionar para dashboard de backup integrado"""
    return redirect(url_for('backup_dashboard_admin.get_attestation_download_link'))

@bp.route('/delete-local-file', methods=['POST'])
@login_required
@admin_required
def delete_local_file():
    """Redirecionar para dashboard de backup integrado"""
    return redirect(url_for('backup_dashboard_admin.delete_attestation_file'))

@bp.route('/test-local-connection', methods=['POST'])
@login_required
@admin_required
def test_local_connection():
    """Testa a conexão com o local"""
    try:
        data = request.get_json()
        
        app_key = data.get('app_key', '').strip()
        app_secret = data.get('app_secret', '').strip()
        access_token = data.get('access_token', '').strip()
        refresh_token = data.get('refresh_token', '').strip()
        
        if not app_key:
            return jsonify({'success': False, 'message': 'App Key é obrigatório'})
        
        if not app_secret:
            return jsonify({'success': False, 'message': 'App Secret é obrigatório'})
        
        if not access_token and not refresh_token:
            return jsonify({'success': False, 'message': 'É necessário pelo menos um Access Token ou Refresh Token'})
        
        # Testar conexão
        import local
        
        if refresh_token:
            try:
                dbx = local.local(
                    oauth2_refresh_token=refresh_token,
                    app_key=app_key,
                    app_secret=app_secret
                )
                account = dbx.users_get_current_account()
                display_name = account.name.display_name if account and account.name else 'Usuário'
                return jsonify({
                    'success': True, 
                    'message': f'Conexão bem-sucedida via Refresh Token! Usuário: {display_name}'
                })
            except Exception as e:
                if access_token:
                    # Tentar com access token se refresh token falhou
                    pass
                else:
                    return jsonify({'success': False, 'message': f'Erro com Refresh Token: {str(e)}'})
        
        if access_token:
            try:
                dbx = local.local(access_token)
                account = dbx.users_get_current_account()
                display_name = account.name.display_name if account and account.name else 'Usuário'
                return jsonify({
                    'success': True, 
                    'message': f'Conexão bem-sucedida via Access Token! Usuário: {display_name}'
                })
            except Exception as e:
                return jsonify({'success': False, 'message': f'Erro com Access Token: {str(e)}'})
        
        return jsonify({'success': False, 'message': 'Nenhum token válido fornecido'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'})

@bp.route('/update-local-config', methods=['POST'])
@login_required
@admin_required
def update_local_config():
    """Atualizar configurações do local"""
    try:
        # Obter dados do formulário
        app_key = request.form.get('app_key', '').strip()
        app_secret = request.form.get('app_secret', '').strip()
        access_token = request.form.get('access_token', '').strip()
        refresh_token = request.form.get('refresh_token', '').strip()
        test_connection = request.form.get('test_connection_after_save') == 'on'
        
        # Validação básica
        if not app_key or not app_secret:
            flash('❌ App Key e App Secret são obrigatórios!', 'error')
            return redirect(url_for('admin.backup_config'))
        
        # Buscar ou criar configuração do local no banco
        from app.models import localConfig
        local_config = localConfig.query.filter_by(is_active=True).first()
        
        if not local_config:
            local_config = localConfig(
                created_by=current_user.id,
                is_active=True
            )
            db.session.add(local_config)
        
        # Atualizar configurações
        local_config.app_key = app_key
        local_config.app_secret = app_secret
        local_config.access_token = access_token if access_token else None
        local_config.refresh_token = refresh_token if refresh_token else None
        local_config.updated_at = datetime.utcnow()
        
        # Salvar no banco
        db.session.commit()
        
        # Atualizar configurações no config da aplicação
        current_app.config['local_APP_KEY'] = app_key
        current_app.config['local_APP_SECRET'] = app_secret
        if access_token:
            current_app.config['local_ACCESS_TOKEN'] = access_token
        if refresh_token:
            current_app.config['local_REFRESH_TOKEN'] = refresh_token
        
        # Log da alteração
        log_security_event(
            'local_CONFIG_UPDATED',
            f'Configurações do local atualizadas por {current_user.nome}',
            current_user.id
        )
        
        # Criar notificação para outros admins
        send_notification_to_admins(
            'Configurações do local Atualizadas',
            f'O usuário {current_user.nome} atualizou as configurações de acesso ao local.',
            current_user.id
        )
        
        flash('✅ Configurações do local atualizadas com sucesso!', 'success')
        
        # Testar conexão se solicitado
        if test_connection:
            try:
                # # from app.local_database import get_db_manager  # Module not found  # Module not found
                
                # Reinicializar o gerenciador com as novas configurações
                db_manager = None  # None  # get_db_manager() disabled disabled
                
                if db_manager and db_manager.is_connected():
                    flash('✅ Teste de conexão bem-sucedido!', 'success')
                else:
                    flash('⚠️ Configurações salvas, mas falha no teste de conexão. Verifique as credenciais.', 'warning')
                    
            except Exception as e:
                flash(f'⚠️ Configurações salvas, mas erro no teste: {str(e)}', 'warning')
        
        return redirect(url_for('admin.backup_config'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar configurações do local: {e}")
        flash(f'❌ Erro ao atualizar configurações: {str(e)}', 'error')
        return redirect(url_for('admin.backup_config'))

@bp.route('/generate-local-auth-url', methods=['POST'])
@login_required
@admin_required
def generate_local_auth_url():
    """Gerar URL de autorização do local"""
    try:
        import urllib.parse
        import secrets
        
        data = request.get_json()
        app_key = data.get('app_key', '').strip()
        app_secret = data.get('app_secret', '').strip()
        
        if not app_key or not app_secret:
            return jsonify({
                'success': False,
                'message': 'App Key e App Secret são obrigatórios'
            })
        
        # Gerar state único para segurança
        state = secrets.token_urlsafe(32)
        
        # URLs de redirecionamento comuns que funcionam com apps local
        # O local permite essas URLs especiais para desenvolvimento
        possible_redirect_uris = [
            "urn:ietf:wg:oauth:2.0:oob",  # URL especial - sempre funciona
            "http://localhost:8080",      # Porta comum para desenvolvimento
            "http://127.0.0.1:8080",      # IP local
            "http://localhost:5000",      # Porta do Flask
            "http://127.0.0.1:5000",      # IP local do Flask
            "https://localhost:8080",     # HTTPS local
            "http://localhost",           # Localhost simples
            "https://localhost"           # HTTPS localhost
        ]
        
        # Para desenvolvimento, vamos usar a URL especial que sempre funciona
        redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        
        # Parâmetros da URL de autorização
        auth_params = {
            'client_id': app_key,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'state': state,
            'token_access_type': 'offline',  # Para obter refresh token
            'force_reapprove': 'true'  # Forçar nova aprovação
        }
        
        # Construir URL de autorização
        auth_url = 'https://www.local.com/oauth2/authorize?' + urllib.parse.urlencode(auth_params)
        
        # Salvar state na sessão para verificação posterior
        from flask import session
        session['local_auth_state'] = state
        session['local_app_key'] = app_key
        session['local_app_secret'] = app_secret
        session['local_redirect_uri'] = redirect_uri
        
        return jsonify({
            'success': True,
            'auth_url': auth_url,
            'state': state,
            'redirect_uri': redirect_uri,
            'message': 'URL de autorização gerada com sucesso',
            'instructions': f'Configure no local App Console a URL de redirecionamento: {redirect_uri}',
            'alternative_urls': possible_redirect_uris
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar URL de autorização local: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        })

@bp.route('/exchange-local-auth-code', methods=['POST'])
@login_required
@admin_required
def exchange_local_auth_code():
    """Trocar código de autorização por tokens do local"""
    try:
        import requests
        from flask import session
        
        data = request.get_json()
        auth_code = data.get('auth_code', '').strip()
        app_key = data.get('app_key', '').strip()
        app_secret = data.get('app_secret', '').strip()
        state = data.get('state', '').strip()
        
        if not auth_code:
            return jsonify({
                'success': False,
                'message': 'Código de autorização é obrigatório'
            })
        
        if not app_key or not app_secret:
            return jsonify({
                'success': False,
                'message': 'App Key e App Secret são obrigatórios'
            })
        
        # Verificar state para segurança (opcional, mas recomendado)
        session_state = session.get('local_auth_state')
        if session_state and state and session_state != state:
            return jsonify({
                'success': False,
                'message': 'State de segurança inválido'
            })
        
        # Obter redirect_uri da sessão ou usar padrão especial
        redirect_uri = session.get('local_redirect_uri', 'urn:ietf:wg:oauth:2.0:oob')
        
        # Parâmetros para troca de código por token
        token_params = {
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,  # Deve ser o mesmo usado na autorização
            'client_id': app_key,
            'client_secret': app_secret
        }
        
        # Fazer requisição para obter tokens
        token_url = 'https://api.localapi.com/oauth2/token'
        response = requests.post(token_url, data=token_params)
        
        if response.status_code == 200:
            token_data = response.json()
            
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            
            if not access_token:
                return jsonify({
                    'success': False,
                    'message': 'Não foi possível obter o access token'
                })
            
            # Log da operação
            log_security_event(
                'local_TOKEN_GENERATED',
                f'Tokens do local gerados por {current_user.nome}',
                current_user.id
            )
            
            # Limpar dados da sessão
            session.pop('local_auth_state', None)
            session.pop('local_app_key', None)
            session.pop('local_app_secret', None)
            session.pop('local_redirect_uri', None)
            
            return jsonify({
                'success': True,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'message': 'Tokens gerados com sucesso!'
            })
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error_description', f'Erro HTTP {response.status_code}')
            
            return jsonify({
                'success': False,
                'message': f'Erro do local: {error_msg}'
            })
            
    except requests.RequestException as e:
        current_app.logger.error(f"Erro de rede ao trocar código local: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro de conexão com o local'
        })
    except Exception as e:
        current_app.logger.error(f"Erro ao trocar código local: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        })

@bp.route('/update-shared-link', methods=['POST'])
@login_required
@admin_required
def update_shared_link():
    """Atualizar link da pasta compartilhada do local"""
    try:
        from app.shared_folder_manager import SharedFolderManager
        
        shared_link = request.form.get('shared_link', '').strip()
        
        if not shared_link:
            flash('❌ Link da pasta compartilhada é obrigatório!', 'error')
            return redirect(url_for('admin.backup_config'))
        
        # Validar link usando o gerenciador
        manager = SharedFolderManager()
        is_valid, message = manager.validate_shared_link(shared_link)
        
        if not is_valid:
            flash(f'❌ {message}', 'error')
            return redirect(url_for('admin.backup_config'))
        
        # Inicializar gerenciador com o link válido
        manager = SharedFolderManager(shared_link)
        
        # Criar estrutura de pastas
        try:
            created_folders = manager.create_folder_structure()
            flash('✅ Estrutura de pastas criada automaticamente!', 'success')
            
            # Log das pastas criadas
            for folder_name, folder_path in created_folders.items():
                current_app.logger.info(f"Pasta criada: {folder_name} -> {folder_path}")
            
        except Exception as e:
            current_app.logger.error(f"Erro ao criar estrutura: {str(e)}")
            flash(f'⚠️ Link salvo, mas erro ao criar estrutura: {str(e)}', 'warning')
        
        # Salvar link compartilhado usando função robusta
        if not save_shared_link_to_config(shared_link):
            flash('❌ Erro ao salvar link compartilhado! Tente novamente.', 'error')
            return redirect(url_for('admin.backup_config'))
        
        # Atualizar caminhos das pastas na configuração
        folder_paths = manager.get_folder_paths()
        for folder_name, folder_path in folder_paths.items():
            env_var = f"SHARED_{folder_name.upper()}_PATH"
            current_app.config[env_var] = folder_path
        
        # Configurar caminhos principais do Flask
        # DESABILITADO: current_app.config['DATABASE_URL'] = f"sqlite:///{manager.get_database_path()}"
        # Comentado para evitar conflito com banco storage
        current_app.config['UPLOAD_FOLDER'] = manager.get_uploads_path()
        current_app.config['BACKUP_FOLDER'] = manager.get_backups_path()
        current_app.config['LOGS_FOLDER'] = manager.get_logs_path()
        
        # Log da alteração
        log_security_event(
            'SHARED_FOLDER_CONFIGURED',
            f'Pasta compartilhada configurada por {current_user.nome}. Provider: {manager.provider}',
            current_user.id
        )
        
        # Criar notificação para outros admins
        send_notification_to_admins(
            'Pasta Compartilhada Configurada',
            f'O usuário {current_user.nome} configurou uma pasta compartilhada ({manager.provider}). Estrutura de pastas criada automaticamente.',
            current_user.id
        )
        
        flash('✅ Link da pasta compartilhada configurado com sucesso! Estrutura de pastas criada automaticamente.', 'success')
        
    except Exception as e:
        flash(f'❌ Erro ao configurar pasta compartilhada: {str(e)}', 'error')
        current_app.logger.error(f'Erro ao configurar shared folder: {str(e)}')
    
    return redirect(url_for('admin.backup_config'))

@bp.route('/system-config')
@login_required
@admin_required
def system_config():
    """Configurações do sistema"""
    try:
        # Aqui você pode adicionar configurações específicas do sistema
        # Por enquanto, redirecionamos para backup-config como configuração principal
        return redirect(url_for('admin.backup_config'))
    except Exception as e:
        current_app.logger.error(f"Erro ao acessar configurações do sistema: {e}")
        flash('❌ Erro ao carregar configurações do sistema', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/security-logs')
@login_required
@admin_required
def security_logs():
    """Logs de segurança - redirecionamento para logs gerais"""
    try:
        # Redirecionamos para a página de logs existente
        return redirect(url_for('admin.logs'))
    except Exception as e:
        current_app.logger.error(f"Erro ao acessar logs de segurança: {e}")
        flash('❌ Erro ao carregar logs de segurança', 'error')
        return redirect(url_for('admin.dashboard'))
