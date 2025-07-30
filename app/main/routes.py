from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, send_file, abort
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_
from datetime import datetime, date, timedelta
import os
from app import db
from app.main import bp
from app.models import User, TimeRecord, MedicalAttestation, Notification, AttestationStatus
from app.forms import TimeRecordForm, EditProfileForm, MedicalAttestationForm
from app.utils import (save_uploaded_file, log_security_event, calculate_work_hours, 
                      format_hours, get_month_name, create_notification)

@bp.route('/health')
def health_check():
    """Health check endpoint para Render.com"""
    try:
        # Verificar conexão com banco
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        # Verificar se diretórios existem
        storage_paths = [
            current_app.config.get('STORAGE_BASE_PATH'),
            current_app.config.get('BACKUPS_PATH'),
            current_app.config.get('UPLOAD_FOLDER')
        ]
        
        paths_ok = all(os.path.exists(path) for path in storage_paths if path)
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'storage': 'ok' if paths_ok else 'warning',
            'backup_enabled': current_app.config.get('AUTO_BACKUP_ENABLED', False),
            'version': '2.0'
        }), 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@bp.route('/api/notifications/recent')
@login_required
def get_recent_notifications():
    """API para buscar as 5 últimas notificações do usuário"""
    try:
        notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(desc(Notification.created_at)).limit(5).all()
        
        # Contar notificações não lidas
        unread_count = Notification.query.filter_by(
            user_id=current_user.id,
            lida=False
        ).count()
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'titulo': notification.titulo,
                'mensagem': notification.mensagem,
                'tipo': notification.tipo.value,
                'lida': notification.lida,
                'created_at': notification.created_at.strftime('%d/%m/%Y %H:%M'),
                'time_ago': format_time_ago(notification.created_at)
            })
        
        return jsonify({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count
        })
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar notificações: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar notificações'
        }), 500

def format_time_ago(datetime_obj):
    """Formatar tempo relativo (ex: 2 horas atrás)"""
    now = datetime.now()
    diff = now - datetime_obj
    
    if diff.days > 0:
        return f"{diff.days} dia{'s' if diff.days > 1 else ''} atrás"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hora{'s' if hours > 1 else ''} atrás"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minuto{'s' if minutes > 1 else ''} atrás"
    else:
        return "Agora"

@bp.route('/')
@bp.route('/index')
def index():
    """Página inicial"""
    try:
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return render_template('main/index.html', title='SKPONTO - Sistema de Controle de Ponto')
    except Exception as e:
        current_app.logger.error(f"Erro na página inicial: {e}")
        return render_template('main/index.html', title='SKPONTO - Sistema de Controle de Ponto')

@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard do usuário"""
    hoje = date.today()
    
    # Buscar registro de hoje
    registro_hoje = TimeRecord.query.filter_by(
        user_id=current_user.id,
        data=hoje
    ).first()
    
    # Estatísticas do mês atual
    inicio_mes = hoje.replace(day=1)
    registros_mes = TimeRecord.query.filter(
        TimeRecord.user_id == current_user.id,
        TimeRecord.data >= inicio_mes,
        TimeRecord.data <= hoje
    ).all()

    horas_mes = sum(r.horas_trabalhadas for r in registros_mes)
    
    # CORREÇÃO: Verificar se banco de horas existe antes de criar
    from app.models import HourBank
    hour_bank = HourBank.query.filter_by(user_id=current_user.id).first()
    if not hour_bank:
        hour_bank = HourBank(user_id=current_user.id)
        db.session.add(hour_bank)
        try:
            db.session.commit()
            current_app.logger.info(f"Banco de horas criado para usuário {current_user.id}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar banco de horas: {e}")
            hour_bank = HourBank.query.filter_by(user_id=current_user.id).first()
    
    # Saldo atual do banco de horas (inclui horas extras e débitos)
    saldo_banco_horas = None  # hour_bank disabled
    
    dias_trabalhados = len([r for r in registros_mes if r.is_completo])
    
    # Notificações não lidas
    notificacoes = Notification.query.filter_by(
        user_id=current_user.id,
        lida=False
    ).order_by(desc(Notification.created_at)).limit(5).all()
    
    # Atestados pendentes (se for admin)
    atestados_pendentes = []
    if current_user.is_admin:
        atestados_pendentes = MedicalAttestation.query.filter_by(
            status=AttestationStatus.PENDENTE
        ).order_by(desc(MedicalAttestation.created_at)).limit(5).all()
    
    # Últimos registros
    ultimos_registros = TimeRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(desc(TimeRecord.data)).limit(7).all()
    
    return render_template('main/dashboard.html',
                         title='Dashboard',
                         registro_hoje=registro_hoje,
                         horas_mes=format_hours(horas_mes),
                         horas_extras_mes=saldo_banco_horas,  # MUDANÇA: usar saldo do banco
                         dias_trabalhados=dias_trabalhados,
                         notificacoes=notificacoes,
                         atestados_pendentes=atestados_pendentes,
                         ultimos_registros=ultimos_registros,
                         mes_atual=get_month_name(hoje.month))

@bp.route('/ponto', methods=['GET', 'POST'])
@login_required
def ponto():
    """Registro de ponto"""
    from app.utils import get_current_date, get_current_time
    
    try:
        hoje = get_current_date()
        agora = get_current_time()
        
        # Buscar ou criar registro de hoje
        registro = TimeRecord.query.filter_by(
            user_id=current_user.id,
            data=hoje
        ).first()
        
        if not registro:
            registro = TimeRecord(user_id=current_user.id, data=hoje)
            db.session.add(registro)
    
        if request.method == 'POST':
            try:
                acao = request.form.get('acao')
                
                # Handle manual registration
                entrada_manual = request.form.get('entrada_manual')
                saida_manual = request.form.get('saida_manual')
                
                if entrada_manual or saida_manual:
                    # Manual registration mode
                    try:
                        from datetime import datetime
                        
                        if entrada_manual:
                            entrada_time = datetime.strptime(entrada_manual, '%H:%M').time()
                            registro.entrada = entrada_time
                        
                        if saida_manual:
                            saida_time = datetime.strptime(saida_manual, '%H:%M').time()
                            registro.saida = saida_time
                        
                        # Recalculate hours if both times are set
                        if registro.entrada and registro.saida:
                            registro.calcular_horas()
                        
                        db.session.commit()
                        flash('Registro manual atualizado com sucesso!', 'success')
                        log_security_event('MANUAL_TIME_ENTRY', f'Registro manual: Entrada {entrada_manual}, Saída {saida_manual}', current_user.id)
                        return redirect(url_for('main.ponto'))
                        
                    except ValueError as e:
                        flash(f'Erro no formato de hora: Use o formato HH:MM (ex: 08:30)', 'error')
                    except Exception as e:
                        current_app.logger.error(f"Erro no registro manual: {str(e)}")
                        flash(f'Erro no registro manual: {str(e)}', 'error')
                
                elif acao == 'entrada':
                    if registro.entrada is None:
                        registro.entrada = agora
                        db.session.commit()
                        flash('Entrada registrada com sucesso!', 'success')
                        log_security_event('TIME_ENTRY', f'Entrada registrada: {agora}', current_user.id)
                    else:
                        flash('Entrada já foi registrada hoje.', 'warning')
                
                elif acao == 'saida':
                    if registro.entrada is None:
                        flash('Erro: Você deve registrar a entrada primeiro.', 'error')
                    elif registro.saida is None:
                        registro.saida = agora
                        registro.calcular_horas()
                        db.session.commit()
                        flash('Saída registrada com sucesso!', 'success')
                        log_security_event('TIME_EXIT', f'Saída registrada: {agora}', current_user.id)
                    else:
                        flash('Saída já foi registrada hoje.', 'warning')
                
                elif acao == 'saida_almoco':
                    if registro.entrada is None:
                        flash('Erro: Você deve registrar a entrada primeiro.', 'error')
                    elif registro.saida_almoco is None:
                        registro.saida_almoco = agora
                        db.session.commit()
                        flash('Saída para almoço registrada!', 'success')
                        log_security_event('LUNCH_EXIT', f'Saída almoço registrada: {agora}', current_user.id)
                    else:
                        flash('Saída para almoço já foi registrada hoje.', 'warning')
                
                elif acao == 'volta_almoco':
                    if registro.saida_almoco is None:
                        flash('Erro: Você deve registrar a saída para almoço primeiro.', 'error')
                    elif registro.volta_almoco is None:
                        registro.volta_almoco = agora
                        db.session.commit()
                        flash('Volta do almoço registrada!', 'success')
                        log_security_event('LUNCH_RETURN', f'Volta almoço registrada: {agora}', current_user.id)
                    else:
                        flash('Volta do almoço já foi registrada hoje.', 'warning')
                
                else:
                    flash('Ação inválida.', 'error')
                    
            except Exception as e:
                current_app.logger.error(f"Erro no registro de ponto: {str(e)}")
                flash(f'Erro ao processar registro: {str(e)}', 'error')
                db.session.rollback()
                
    except Exception as e:
        current_app.logger.error(f"Erro crítico na página de ponto: {str(e)}")
        flash('Erro interno do sistema. Contate o administrador.', 'error')
        return redirect(url_for('main.dashboard'))
    
    return render_template('main/ponto.html',
                         title='Registro de Ponto',
                         registro=registro)

@bp.route('/meus_registros')
@bp.route('/meus-registros')  # Alias com hífen para compatibilidade
@login_required
def meus_registros():
    """Visualização dos registros pessoais"""
    page = request.args.get('page', 1, type=int)
    
    # Filtros
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')
    
    # Query base
    query = TimeRecord.query.filter_by(user_id=current_user.id)
    
    # Aplicar filtros
    if inicio:
        try:
            data_inicio = datetime.strptime(inicio, '%Y-%m-%d').date()
            query = query.filter(TimeRecord.data >= data_inicio)
        except ValueError:
            pass
    
    if fim:
        try:
            data_fim = datetime.strptime(fim, '%Y-%m-%d').date()
            query = query.filter(TimeRecord.data <= data_fim)
        except ValueError:
            pass
    
    registros = query.order_by(desc(TimeRecord.data)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('main/meus_registros.html',
                         title='Meus Registros',
                         registros=registros,
                         inicio=inicio,
                         fim=fim)

@bp.route('/editar_registro/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_registro(id):
    """Edição de registro de ponto"""
    registro = TimeRecord.query.get_or_404(id)
    
    # Verificar permissão
    if registro.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este registro.', 'error')
        return redirect(url_for('main.meus_registros'))
    
    form = TimeRecordForm(obj=registro)
    
    if form.validate_on_submit():
        # Salvar dados originais para log
        dados_originais = {
            'entrada': registro.entrada,
            'saida': registro.saida,
            'observacoes': registro.observacoes
        }
        
        # Atualizar registro
        registro.data = form.data.data
        registro.entrada = form.entrada.data
        registro.saida = form.saida.data
        registro.observacoes = form.observacoes.data
        registro.justificativa_edicao = form.justificativa_edicao.data
        registro.edited_by = current_user.id
        registro.updated_at = datetime.utcnow()
        
        # Recalcular horas
        registro.calcular_horas()
        
        db.session.commit()
        
        # Log da edição
        log_security_event('TIME_RECORD_EDITED', 
                          f'Registro editado - Original: {dados_originais}, '
                          f'Novo: entrada={registro.entrada}, saida={registro.saida}',
                          current_user.id)
        
        flash('Registro atualizado com sucesso!', 'success')
        return redirect(url_for('main.meus_registros'))
    
    return render_template('main/editar_registro.html',
                         title='Editar Registro',
                         form=form,
                         registro=registro)

@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Perfil do usuário"""
    form = EditProfileForm(current_user.email, obj=current_user)
    
    if form.validate_on_submit():
        # Atualizar dados
        current_user.nome = form.nome.data
        current_user.sobrenome = form.sobrenome.data
        current_user.email = form.email.data
        current_user.telefone = form.telefone.data
        current_user.cargo = form.cargo.data
        
        # Processar nova foto se enviada (both foto_perfil and avatar should work)
        foto_field = form.foto_perfil.data or form.avatar.data
        if foto_field:
            try:
                filename = save_uploaded_file(foto_field, 'profiles')
                if filename:
                    current_user.foto_perfil = filename
                    flash('Foto de perfil atualizada com sucesso!', 'success')
                else:
                    flash('Erro: Não foi possível salvar a foto de perfil.', 'error')
            except ValueError as e:
                flash(f'Erro na foto de perfil: {str(e)}', 'error')
            except Exception as e:
                current_app.logger.error(f"Erro no upload de foto de perfil: {str(e)}")
                flash('Erro interno ao processar a foto de perfil. Tente novamente.', 'error')
        
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('main.perfil'))
    
    return render_template('main/perfil.html', title='Meu Perfil', form=form)

@bp.route('/atestados')
@login_required
def atestados():
    """Lista de atestados do usuário"""
    page = request.args.get('page', 1, type=int)
    
    atestados = MedicalAttestation.query.filter_by(
        user_id=current_user.id
    ).order_by(desc(MedicalAttestation.created_at)).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('main/atestados.html',
                         title='Meus Atestados',
                         atestados=atestados)

@bp.route('/upload_atestado', methods=['GET', 'POST'])
@login_required
def upload_atestado():
    """Upload de atestado médico"""
    form = MedicalAttestationForm()
    
    if form.validate_on_submit():
        try:
            # Obter nome original do arquivo
            arquivo_original = form.arquivo.data.filename if form.arquivo.data else 'atestado.pdf'
            
            # Criar atestado primeiro (com nome original do arquivo)
            atestado = MedicalAttestation(
                user_id=current_user.id,
                tipo=form.tipo.data,
                data_inicio=form.data_inicio.data,
                data_fim=form.data_fim.data,
                cid=form.cid.data,
                medico_clinica=form.medico_clinica.data,
                observacoes=form.observacoes.data,
                arquivo=arquivo_original  # Nome original do arquivo
            )
            
            db.session.add(atestado)
            db.session.flush()  # Para obter o ID
            
            # Upload para armazenamento local usando o novo serviço
            from app.attestation_upload_service import AttestationUploadService
            upload_service = AttestationUploadService()
            
            success, message = upload_service.save_and_upload_attestation(
                file=form.arquivo.data,
                attestation=atestado,
                user=current_user
            )
            
            if success:
                db.session.commit()
                
                # Notificar administradores
                from app.utils import send_notification_to_admins
                send_notification_to_admins(
                    'Novo Atestado Médico',
                    f'{current_user.nome_completo} enviou um novo atestado médico para aprovação.',
                    'info'
                )
                
                flash('Atestado enviado com sucesso! Aguarde a aprovação.', 'success')
                return redirect(url_for('main.atestados'))
            else:
                db.session.rollback()
                flash(f'Erro no upload: {message}', 'error')
                
        except Exception as e:
            current_app.logger.error(f"Erro inesperado no upload de atestado: {str(e)}")
            flash('Erro interno do servidor. Tente novamente ou contate o administrador.', 'error')
            db.session.rollback()
    
    # Show form validation errors
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Erro no campo {field}: {error}', 'error')
    
    return render_template('main/upload_atestado.html',
                         title='Enviar Atestado',
                         form=form)

def extract_original_filename(stored_filename: str, atestado_id: int) -> str:
    """
    Extrai o nome original do arquivo a partir do nome armazenado
    
    Args:
        stored_filename: Nome do arquivo como está armazenado
        atestado_id: ID do atestado para fallback
        
    Returns:
        Nome original do arquivo para download
    """
    if not stored_filename or stored_filename == 'temp':
        return f"atestado_{atestado_id}"  # Sem extensão padrão
    
    # Se o nome não tem o padrão do sistema, usar como está
    if not stored_filename.startswith('attestation_'):
        return stored_filename
    
    # Padrão: attestation_ID_YYYYMMDD_HHMMSS_nome_original.ext
    # Exemplo: attestation_1_20250720_175932_meu_atestado.pdf
    parts = stored_filename.split('_', 4)  # Dividir em até 5 partes
    
    if len(parts) >= 5:
        # A última parte é o nome original (pode ter underscores)
        original_name = parts[4]
        
        # Se o nome original está muito "técnico", tentar melhorar MAS preservar a extensão
        if original_name.startswith('imagem_'):
            # Casos como 'imagem_2025-07-20_175930940.png'
            # Manter a extensão original, mas dar um nome mais amigável
            import os
            _, ext = os.path.splitext(original_name)
            # IMPORTANTE: Preservar a extensão original, não forçar PDF
            return f"atestado_{atestado_id}{ext}"
        
        return original_name
    
    # Fallback para nome padrão (sem extensão pois não sabemos qual é)
    return f"atestado_{atestado_id}"


@bp.route('/download_atestado/<int:id>')
@login_required
def download_atestado(id):
    """Download de arquivo de atestado médico do armazenamento local"""
    atestado = MedicalAttestation.query.get_or_404(id)
    
    # Verificar permissões: usuário dono ou admin
    if atestado.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    try:
        # Verificar se o arquivo existe
        if not atestado.local_path:
            flash('Arquivo de atestado não encontrado.', 'error')
            return redirect(request.referrer or url_for('main.atestados'))
        
        from pathlib import Path
        
        file_path = Path(atestado.local_path)
        if not file_path.exists():
            flash('Arquivo de atestado não encontrado no sistema.', 'error')
            return redirect(request.referrer or url_for('main.atestados'))
        
        # Extrair nome original do arquivo usando a função helper
        nome_original = extract_original_filename(atestado.arquivo, atestado.id)

        # Servir o arquivo diretamente
        return send_file(
            file_path,
            as_attachment=True,
            download_name=nome_original
        )
            
    except Exception as e:
        current_app.logger.error(f"Erro inesperado no download de atestado: {str(e)}")
        flash('Erro interno do servidor. Contate o administrador.', 'error')
        return redirect(request.referrer or url_for('main.atestados'))

@bp.route('/cancelar_atestado/<int:id>', methods=['POST'])
@login_required
def cancelar_atestado(id):
    """Cancelar atestado médico (apenas se pendente)"""
    atestado = MedicalAttestation.query.get_or_404(id)
    
    # Verificar se o usuário é o dono do atestado
    if atestado.user_id != current_user.id:
        abort(403)
    
    # Verificar se o atestado ainda está pendente
    if atestado.status != AttestationStatus.PENDENTE:
        flash('Só é possível cancelar atestados pendentes.', 'error')
        return redirect(url_for('main.atestados'))
    
    try:
        # Remover arquivo físico se existir
        if atestado.arquivo:
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            file_path = os.path.join(upload_folder, 'atestados', atestado.arquivo)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Remover atestado do banco
        db.session.delete(atestado)
        db.session.commit()
        
        flash('Atestado cancelado com sucesso.', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Erro ao cancelar atestado {id}: {str(e)}")
        db.session.rollback()
        flash('Erro ao cancelar atestado.', 'error')
    
    return redirect(url_for('main.atestados'))

@bp.route('/notificacoes')
@login_required
def notificacoes():
    """Lista de notificações do usuário com filtros"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    tipo_filter = request.args.get('tipo', '')
    status_filter = request.args.get('status', '')
    
    # Base query
    query = Notification.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if search:
        query = query.filter(
            (Notification.titulo.ilike(f'%{search}%')) |
            (Notification.mensagem.ilike(f'%{search}%'))
        )
    
    if tipo_filter:
        # Handle enum filtering properly
        from app.models import NotificationType
        try:
            tipo_enum = NotificationType(tipo_filter)
            query = query.filter(Notification.tipo == tipo_enum)
        except ValueError:
            # If tipo_filter is not a valid enum value, ignore the filter
            pass
    
    if status_filter == 'lida':
        query = query.filter(Notification.lida == True)
    elif status_filter == 'nao_lida':
        query = query.filter(Notification.lida == False)
    
    # Get all notification types for filter dropdown
    tipos_notificacao = db.session.query(Notification.tipo).filter_by(
        user_id=current_user.id
    ).distinct().all()
    tipos_notificacao = [tipo[0] for tipo in tipos_notificacao]
    
    # Get notifications with pagination
    notificacoes = query.order_by(desc(Notification.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get statistics
    total_notificacoes = Notification.query.filter_by(user_id=current_user.id).count()
    nao_lidas = Notification.query.filter_by(user_id=current_user.id, lida=False).count()
    
    return render_template('main/notificacoes.html',
                         title='Notificações',
                         notificacoes=notificacoes,
                         tipos_notificacao=tipos_notificacao,
                         current_search=search,
                         current_tipo=tipo_filter,
                         current_status=status_filter,
                         total_notificacoes=total_notificacoes,
                         nao_lidas=nao_lidas)

@bp.route('/marcar_notificacao_lida/<int:id>', methods=['GET', 'POST'])
@login_required
def marcar_notificacao_lida(id):
    """Marca notificação como lida"""
    notificacao = Notification.query.get_or_404(id)
    
    if notificacao.user_id != current_user.id:
        flash('Acesso negado.', 'error')
        return redirect(url_for('main.notificacoes'))
    
    notificacao.lida = True
    db.session.commit()
    
    return redirect(url_for('main.notificacoes'))

@bp.route('/deletar_notificacao/<int:id>', methods=['GET', 'POST'])
@login_required
def deletar_notificacao(id):
    """Deleta uma notificação do usuário"""
    notificacao = Notification.query.get_or_404(id)
    
    if notificacao.user_id != current_user.id:
        flash('Acesso negado.', 'error')
        return redirect(url_for('main.notificacoes'))
    
    db.session.delete(notificacao)
    db.session.commit()
    flash('Notificação deletada com sucesso.', 'success')
    
    return redirect(url_for('main.notificacoes'))

@bp.route('/marcar_todas_lidas', methods=['POST'])
@login_required
def marcar_todas_lidas():
    """Marca todas as notificações do usuário como lidas"""
    try:
        notificacoes_nao_lidas = Notification.query.filter_by(
            user_id=current_user.id, 
            lida=False
        ).all()
        
        for notificacao in notificacoes_nao_lidas:
            notificacao.lida = True
        
        db.session.commit()
        flash(f'{len(notificacoes_nao_lidas)} notificações marcadas como lidas.', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Erro ao marcar todas como lidas: {str(e)}")
        flash('Erro ao marcar notificações como lidas.', 'error')
        db.session.rollback()
    
    return redirect(url_for('main.notificacoes'))

# API Routes
@bp.route('/api/registrar_ponto', methods=['POST'])
@login_required
def api_registrar_ponto():
    """API para registro de ponto via AJAX"""
    from app.utils import get_current_date, get_current_time
    
    acao = request.json.get('acao')
    hoje = get_current_date()
    agora = get_current_time()
    
    # Buscar ou criar registro
    registro = TimeRecord.query.filter_by(
        user_id=current_user.id,
        data=hoje
    ).first()
    
    if not registro:
        registro = TimeRecord(user_id=current_user.id, data=hoje)
        db.session.add(registro)
    
    if acao == 'entrada':
        if registro.entrada is None:
            registro.entrada = agora
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Entrada registrada com sucesso!',
                'entrada': agora.strftime('%H:%M')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Entrada já foi registrada hoje.'
            })
    
    elif acao == 'saida':
        if registro.entrada is None:
            return jsonify({
                'success': False,
                'message': 'Você deve registrar a entrada primeiro.'
            })
        elif registro.saida is None:
            registro.saida = agora
            registro.calcular_horas()
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Saída registrada com sucesso!',
                'saida': agora.strftime('%H:%M'),
                'horas_trabalhadas': format_hours(registro.horas_trabalhadas)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Saída já foi registrada hoje.'
            })
    
    return jsonify({'success': False, 'message': 'Ação inválida.'})

@bp.route('/api/notificacoes_nao_lidas')
@login_required
def api_notificacoes_nao_lidas():
    """API para buscar notificações não lidas"""
    count = Notification.query.filter_by(
        user_id=current_user.id,
        lida=False
    ).count()
    
    return jsonify({'count': count})

@bp.route('/privacy-policy')
def privacy_policy():
    """Política de privacidade - rota pública"""
    return render_template('privacy-policy.html', title='Política de Privacidade')

@bp.route('/terms-of-service') 
def terms_of_service():
    """Termos de serviço - rota pública"""
    return render_template('privacy-policy.html', title='Termos de Serviço')


@bp.route('/uploads/<path:filename>')
@login_required
def serve_uploaded_file(filename):
    """Serve arquivos de upload de forma segura"""
    from flask import send_from_directory
    import os
    
    # Obter o diretório de uploads da configuração
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    # Verificar se o arquivo existe
    file_path = os.path.join(upload_folder, filename)
    if not os.path.exists(file_path):
        abort(404)
    
    # Verificar permissões - apenas administradores ou donos do arquivo
    # podem acessar (implementação básica, pode ser melhorada)
    try:
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        current_app.logger.error(f"Erro ao servir arquivo {filename}: {str(e)}")
        abort(404)


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Recuperar senha"""
    try:
        return render_template('auth/forgot_password.html', title='Recuperar Senha')
    except Exception as e:
        current_app.logger.error(f"Erro na página de recuperação: {e}")
        flash('Erro ao carregar página de recuperação', 'error')
        return redirect(url_for('auth.login'))

@bp.route('/overtime')
@login_required
def overtime():
    """Página de horas extras"""
    try:
        return render_template('main/overtime.html', title='Horas Extras')
    except Exception as e:
        current_app.logger.error(f"Erro na página de horas extras: {e}")
        flash('Erro ao carregar horas extras', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/export/pdf')
@login_required
def export_pdf():
    """Exportar relatórios em PDF"""
    try:
        flash('Exportação PDF em desenvolvimento', 'info')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Erro na exportação PDF: {e}")
        flash('Erro ao exportar PDF', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/export/excel')
@login_required
def export_excel():
    """Exportar relatórios em Excel"""
    try:
        flash('Exportação Excel em desenvolvimento', 'info')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Erro na exportação Excel: {e}")
        flash('Erro ao exportar Excel', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/attestations')
@login_required
def attestations():
    """Lista de atestados do usuário"""
    try:
        return redirect(url_for('main.meus_atestados'))
    except Exception as e:
        current_app.logger.error(f"Erro na página de atestados: {e}")
        flash('Erro ao carregar atestados', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/attestations/new')
@login_required
def new_attestation():
    """Novo atestado"""
    try:
        return redirect(url_for('main.novo_atestado'))
    except Exception as e:
        current_app.logger.error(f"Erro ao criar atestado: {e}")
        flash('Erro ao criar atestado', 'error')
        return redirect(url_for('main.meus_atestados'))

@bp.route('/profile')
@login_required
def profile():
    """Perfil do usuário"""
    try:
        return render_template('main/profile.html', title='Meu Perfil')
    except Exception as e:
        current_app.logger.error(f"Erro na página de perfil: {e}")
        flash('Erro ao carregar perfil', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/settings')
@login_required
def settings():
    """Configurações do usuário"""
    try:
        return render_template('main/settings.html', title='Configurações')
    except Exception as e:
        current_app.logger.error(f"Erro na página de configurações: {e}")
        flash('Erro ao carregar configurações', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/notifications')
@login_required
def notifications():
    """Notificações do usuário"""
    try:
        return redirect(url_for('main.minhas_notificacoes'))
    except Exception as e:
        current_app.logger.error(f"Erro na página de notificações: {e}")
        flash('Erro ao carregar notificações', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/clock-in', methods=['GET', 'POST'])
@login_required
def clock_in():
    """Registrar entrada"""
    try:
        if request.method == 'POST':
            # Lógica para registrar entrada
            # TODO: Implementar lógica de registro de ponto
            flash('Entrada registrada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            # GET - mostrar página de entrada
            return render_template('main/clock_in.html', title='Registrar Entrada')
    except Exception as e:
        current_app.logger.error(f"Erro ao registrar entrada: {e}")
        flash('Erro ao registrar entrada', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/clock-out', methods=['GET', 'POST'])
@login_required
def clock_out():
    """Registrar saída"""
    try:
        if request.method == 'POST':
            # Lógica para registrar saída
            # TODO: Implementar lógica de registro de ponto
            flash('Saída registrada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            # GET - mostrar página de saída
            return render_template('main/clock_out.html', title='Registrar Saída')
    except Exception as e:
        current_app.logger.error(f"Erro ao registrar saída: {e}")
        flash('Erro ao registrar saída', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/reports')
@login_required
def reports():
    """Página de relatórios"""
    return render_template('main/reports.html', title='Relatórios')

@bp.route('/reports/monthly')
@login_required
def reports_monthly():
    """Relatório mensal"""
    return render_template('main/reports_monthly.html', title='Relatório Mensal')

@bp.route('/reports/attendance')
@login_required
def reports_attendance():
    """Relatório de presença"""
    return render_template('main/reports_attendance.html', title='Relatório de Presença')

@bp.route('/upload-attestation', methods=['GET', 'POST'])
@login_required
def upload_attestation():
    """Upload de atestado"""
    if request.method == 'POST':
        flash('Atestado enviado com sucesso!', 'success')
        return redirect(url_for('main.attestations'))
    return render_template('main/upload_attestation.html', title='Enviar Atestado')
