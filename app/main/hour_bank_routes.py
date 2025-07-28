"""
Rotas para usuários (não administradores) do sistema de banco de horas
"""
from datetime import datetime, date, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func
from app import db
from app.main import bp
from app.models import (
    User, HourBank, HourBankTransaction, OvertimeRequest, HourCompensation,
    OvertimeSettings, OvertimeType, OvertimeStatus, HourBankTransactionType,
    CompensationStatus, Notification, NotificationType
)
from app.forms import (
    OvertimeRequestForm, HourCompensationForm, OvertimeSettingsForm
)


@bp.route('/my-hour-bank')
@login_required
def my_hour_bank():
    """Dashboard do banco de horas do usuário atual"""
    try:
        # Criar banco de horas se não existir
        if not current_user.hour_bank:
            current_app.logger.info(f"Criando banco de horas para usuário {current_user.id}")
            hour_bank = HourBank(user_id=current_user.id)
            db.session.add(hour_bank)
            db.session.commit()
            current_app.logger.info(f"Banco de horas criado para usuário {current_user.id}")
    
        # Transações recentes
        recent_transactions = HourBankTransaction.query.filter_by(
            user_id=current_user.id
        ).order_by(HourBankTransaction.created_at.desc()).limit(10).all()
        
        # Solicitações de horas extras
        overtime_requests = OvertimeRequest.query.filter_by(
            user_id=current_user.id
        ).order_by(OvertimeRequest.created_at.desc()).limit(5).all()
        
        # Compensações
        compensations = HourCompensation.query.filter_by(
            user_id=current_user.id
        ).order_by(HourCompensation.created_at.desc()).limit(5).all()
        
        # Estatísticas do mês atual
        start_of_month = date.today().replace(day=1)
        monthly_credits = db.session.query(func.sum(HourBankTransaction.hours)).filter(
            HourBankTransaction.user_id == current_user.id,
            HourBankTransaction.hours > 0,
            HourBankTransaction.created_at >= start_of_month
        ).scalar() or 0
        
        monthly_debits = db.session.query(func.sum(func.abs(HourBankTransaction.hours))).filter(
            HourBankTransaction.user_id == current_user.id,
            HourBankTransaction.hours < 0,
            HourBankTransaction.created_at >= start_of_month
        ).scalar() or 0
        
        return render_template('main/hour_bank/dashboard.html',
                             hour_bank=current_user.hour_bank,
                             recent_transactions=recent_transactions,
                             overtime_requests=overtime_requests,
                             compensations=compensations,
                             monthly_credits=monthly_credits,
                             monthly_debits=monthly_debits)
    
    except Exception as e:
        current_app.logger.error(f"Erro no dashboard do banco de horas: {str(e)}")
        flash('Erro ao carregar o dashboard do banco de horas. Tente novamente.', 'error')
        return redirect(url_for('main.dashboard'))
    recent_transactions = HourBankTransaction.query.filter_by(
        user_id=current_user.id
    ).order_by(HourBankTransaction.created_at.desc()).limit(10).all()
    
    # Solicitações de horas extras
    overtime_requests = OvertimeRequest.query.filter_by(
        user_id=current_user.id
    ).order_by(OvertimeRequest.created_at.desc()).limit(5).all()
    
    # Compensações
    compensations = HourCompensation.query.filter_by(
        user_id=current_user.id
    ).order_by(HourCompensation.created_at.desc()).limit(5).all()
    
    # Estatísticas do mês atual
    start_of_month = date.today().replace(day=1)
    monthly_credits = db.session.query(func.sum(HourBankTransaction.hours)).filter(
        HourBankTransaction.user_id == current_user.id,
        HourBankTransaction.hours > 0,
        HourBankTransaction.created_at >= start_of_month
    ).scalar() or 0
    
    monthly_debits = db.session.query(func.sum(func.abs(HourBankTransaction.hours))).filter(
        HourBankTransaction.user_id == current_user.id,
        HourBankTransaction.hours < 0,
        HourBankTransaction.created_at >= start_of_month
    ).scalar() or 0
    
    return render_template('main/hour_bank/dashboard.html',
                         hour_bank=current_user.hour_bank,
                         recent_transactions=recent_transactions,
                         overtime_requests=overtime_requests,
                         compensations=compensations,
                         monthly_credits=monthly_credits,
                         monthly_debits=monthly_debits)


@bp.route('/my-hour-bank/history')
@login_required
def my_hour_bank_history():
    """Histórico completo do banco de horas do usuário"""
    page = request.args.get('page', 1, type=int)
    transaction_type = request.args.get('type', '', type=str)
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)
    
    # Query base
    query = HourBankTransaction.query.filter_by(user_id=current_user.id)
    
    # Filtros
    if transaction_type:
        query = query.filter(HourBankTransaction.transaction_type == HourBankTransactionType(transaction_type))
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(HourBankTransaction.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(HourBankTransaction.created_at <= end_dt)
        except ValueError:
            pass
    
    transactions = query.order_by(HourBankTransaction.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('main/hour_bank/history.html',
                         transactions=transactions,
                         transaction_type=transaction_type,
                         start_date=start_date,
                         end_date=end_date,
                         transaction_types=HourBankTransactionType)


@bp.route('/overtime-request', methods=['GET', 'POST'])
@login_required
def request_overtime():
    """Solicitar horas extras"""
    form = OvertimeRequestForm()
    
    if form.validate_on_submit():
        # Calcular horas estimadas
        start_time = form.start_time.data
        end_time = form.end_time.data
        start_dt = datetime.combine(form.date.data, start_time)
        end_dt = datetime.combine(form.date.data, end_time)
        
        # Ajustar se end_time for menor que start_time (próximo dia)
        if end_time <= start_time:
            end_dt += timedelta(days=1)
        
        estimated_hours = (end_dt - start_dt).total_seconds() / 3600
        
        # Verificar limites do usuário
        settings = OvertimeSettings.query.filter_by(user_id=current_user.id).first()
        if settings:
            # Verificar limite diário
            date_overtime = db.session.query(func.sum(OvertimeRequest.estimated_hours)).filter(
                OvertimeRequest.user_id == current_user.id,
                OvertimeRequest.date == form.date.data,
                OvertimeRequest.status.in_([OvertimeStatus.PENDENTE, OvertimeStatus.APROVADA])
            ).scalar() or 0
            
            if date_overtime + estimated_hours > settings.max_daily_overtime:
                flash(f'Limite diário de horas extras excedido. Máximo: {settings.max_daily_overtime}h, '
                      f'já solicitado: {date_overtime}h, tentativa: {estimated_hours}h', 'error')
                return render_template('main/hour_bank/request_overtime.html', form=form)
        
        # Verificar se já existe solicitação para a mesma data e horário
        existing_request = OvertimeRequest.query.filter(
            OvertimeRequest.user_id == current_user.id,
            OvertimeRequest.date == form.date.data,
            OvertimeRequest.status.in_([OvertimeStatus.PENDENTE, OvertimeStatus.APROVADA]),
            or_(
                and_(OvertimeRequest.start_time <= start_time, OvertimeRequest.end_time > start_time),
                and_(OvertimeRequest.start_time < end_time, OvertimeRequest.end_time >= end_time),
                and_(start_time <= OvertimeRequest.start_time, end_time >= OvertimeRequest.end_time)
            )
        ).first()
        
        if existing_request:
            flash('Já existe uma solicitação para este período.', 'error')
            return render_template('main/hour_bank/request_overtime.html', form=form)
        
        # Criar solicitação
        overtime_request = OvertimeRequest(
            user_id=current_user.id,
            date=form.date.data,
            start_time=start_time,
            end_time=end_time,
            estimated_hours=estimated_hours,
            overtime_type=OvertimeType(form.overtime_type.data),
            justification=form.justification.data
        )
        
        # Verificar se requer aprovação
        if settings and estimated_hours <= settings.auto_approval_limit and not settings.requires_approval:
            overtime_request.status = OvertimeStatus.APROVADA
            overtime_request.approved_by = None  # Aprovação automática
            overtime_request.approved_at = datetime.now()
            overtime_request.multiplier_applied = settings.get_multiplier(overtime_request.overtime_type)
            
            flash('Solicitação de horas extras aprovada automaticamente!', 'success')
        else:
            flash('Solicitação de horas extras enviada para aprovação!', 'info')
        
        db.session.add(overtime_request)
        db.session.commit()
        
        return redirect(url_for('main.my_overtime_requests'))
    
    return render_template('main/hour_bank/request_overtime.html', form=form)


@bp.route('/my-overtime-requests')
@login_required
def my_overtime_requests():
    """Lista solicitações de horas extras do usuário"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '', type=str)
    
    query = OvertimeRequest.query.filter_by(user_id=current_user.id)
    
    if status_filter:
        query = query.filter(OvertimeRequest.status == OvertimeStatus(status_filter))
    
    requests = query.order_by(OvertimeRequest.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('main/hour_bank/my_overtime_requests.html',
                         requests=requests,
                         status_filter=status_filter,
                         overtime_status=OvertimeStatus)


@bp.route('/overtime-request/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_overtime_request(request_id):
    """Cancelar solicitação de horas extras"""
    overtime_request = OvertimeRequest.query.filter_by(
        id=request_id,
        user_id=current_user.id
    ).first_or_404()
    
    if overtime_request.status != OvertimeStatus.PENDENTE:
        flash('Só é possível cancelar solicitações pendentes.', 'error')
        return redirect(url_for('main.my_overtime_requests'))
    
    overtime_request.status = OvertimeStatus.CANCELADA
    db.session.commit()
    
    flash('Solicitação de horas extras cancelada.', 'info')
    return redirect(url_for('main.my_overtime_requests'))


@bp.route('/request-compensation', methods=['GET', 'POST'])
@login_required
def request_compensation():
    """Solicitar compensação de horas"""
    form = HourCompensationForm()
    
    if form.validate_on_submit():
        # Verificar se usuário tem saldo suficiente
        if not current_user.hour_bank or not current_user.hour_bank.can_debit(form.hours_to_compensate.data):
            current_balance = current_user.hour_bank.formatted_balance if current_user.hour_bank else "0h 0m"
            flash(f'Saldo insuficiente no banco de horas. Saldo atual: {current_balance}', 'error')
            return render_template('main/hour_bank/request_compensation.html', form=form)
        
        # Verificar se já existe solicitação para a mesma data
        existing_compensation = HourCompensation.query.filter(
            HourCompensation.user_id == current_user.id,
            HourCompensation.requested_date == form.requested_date.data,
            HourCompensation.status.in_([CompensationStatus.PENDENTE, CompensationStatus.APLICADA])
        ).first()
        
        if existing_compensation:
            flash('Já existe uma solicitação de compensação para esta data.', 'error')
            return render_template('main/hour_bank/request_compensation.html', form=form)
        
        # Criar solicitação
        compensation = HourCompensation(
            user_id=current_user.id,
            requested_date=form.requested_date.data,
            hours_to_compensate=form.hours_to_compensate.data,
            justification=form.justification.data
        )
        
        db.session.add(compensation)
        db.session.commit()
        
        flash('Solicitação de compensação enviada para aprovação!', 'info')
        return redirect(url_for('main.my_compensations'))
    
    return render_template('main/hour_bank/request_compensation.html', form=form)


@bp.route('/my-compensations')
@login_required
def my_compensations():
    """Lista compensações do usuário"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '', type=str)
    
    query = HourCompensation.query.filter_by(user_id=current_user.id)
    
    if status_filter:
        query = query.filter(HourCompensation.status == CompensationStatus(status_filter))
    
    compensations = query.order_by(HourCompensation.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('main/hour_bank/my_compensations.html',
                         compensations=compensations,
                         status_filter=status_filter,
                         compensation_status=CompensationStatus)


@bp.route('/compensation/<int:compensation_id>/cancel', methods=['POST'])
@login_required
def cancel_compensation(compensation_id):
    """Cancelar solicitação de compensação"""
    compensation = HourCompensation.query.filter_by(
        id=compensation_id,
        user_id=current_user.id
    ).first_or_404()
    
    if compensation.status != CompensationStatus.PENDENTE:
        flash('Só é possível cancelar solicitações pendentes.', 'error')
        return redirect(url_for('main.my_compensations'))
    
    compensation.status = CompensationStatus.CANCELADA
    db.session.commit()
    
    flash('Solicitação de compensação cancelada.', 'info')
    return redirect(url_for('main.my_compensations'))


@bp.route('/my-hour-bank/settings', methods=['GET', 'POST'])
@login_required
def my_hour_bank_settings():
    """Configurações pessoais do banco de horas"""
    settings = OvertimeSettings.query.filter_by(user_id=current_user.id).first()
    
    if not settings:
        settings = OvertimeSettings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()
    
    form = OvertimeSettingsForm(obj=settings)
    
    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        
        flash('Configurações do banco de horas atualizadas!', 'success')
        return redirect(url_for('main.my_hour_bank'))
    
    return render_template('main/hour_bank/settings.html', form=form, settings=settings)


@bp.route('/api/my-hour-bank/chart-data')
@login_required
def my_hour_bank_chart_data():
    """Dados para gráficos do banco de horas do usuário"""
    # Últimos 6 meses
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    
    end_date = datetime.now()
    start_date = end_date - relativedelta(months=6)
    
    # Transações por mês
    monthly_data = db.session.query(
        func.date_trunc('month', HourBankTransaction.created_at).label('month'),
        func.sum(func.case([(HourBankTransaction.hours > 0, HourBankTransaction.hours)], else_=0)).label('credits'),
        func.sum(func.case([(HourBankTransaction.hours < 0, func.abs(HourBankTransaction.hours))], else_=0)).label('debits'),
        func.sum(HourBankTransaction.hours).label('net')
    ).filter(
        HourBankTransaction.user_id == current_user.id,
        HourBankTransaction.created_at >= start_date
    ).group_by('month').order_by('month').all()
    
    # Preparar dados para o gráfico
    months = []
    credits_data = []
    debits_data = []
    net_data = []
    
    for data in monthly_data:
        months.append(data.month.strftime('%m/%Y'))
        credits_data.append(float(data.credits or 0))
        debits_data.append(float(data.debits or 0))
        net_data.append(float(data.net or 0))
    
    # Saldo atual por tipo de transação
    transaction_types = db.session.query(
        HourBankTransaction.transaction_type,
        func.sum(HourBankTransaction.hours).label('total')
    ).filter(
        HourBankTransaction.user_id == current_user.id
    ).group_by(HourBankTransaction.transaction_type).all()
    
    types_labels = []
    types_values = []
    
    for t_type, total in transaction_types:
        if total != 0:  # Só incluir tipos com valores não-zero
            types_labels.append(t_type.value)
            types_values.append(float(total))
    
    return jsonify({
        'monthly': {
            'months': months,
            'credits': credits_data,
            'debits': debits_data,
            'net': net_data
        },
        'by_type': {
            'labels': types_labels,
            'values': types_values
        },
        'current_balance': float(current_user.hour_bank.current_balance if current_user.hour_bank else 0)
    })


@bp.route('/api/overtime-quick-request', methods=['POST'])
@login_required
def quick_overtime_request():
    """API para solicitação rápida de horas extras"""
    data = request.get_json()
    
    try:
        # Validar dados básicos
        date_str = data.get('date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        justification = data.get('justification', '').strip()
        
        if not all([date_str, start_time_str, end_time_str, justification]):
            return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
        
        # Converter strings para objetos
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validações
        if date_obj < date.today():
            return jsonify({'error': 'Data não pode ser no passado'}), 400
        
        if end_time <= start_time:
            return jsonify({'error': 'Horário de fim deve ser posterior ao início'}), 400
        
        if len(justification) < 10:
            return jsonify({'error': 'Justificativa deve ter pelo menos 10 caracteres'}), 400
        
        # Calcular horas
        start_dt = datetime.combine(date_obj, start_time)
        end_dt = datetime.combine(date_obj, end_time)
        estimated_hours = (end_dt - start_dt).total_seconds() / 3600
        
        # Criar solicitação
        overtime_request = OvertimeRequest(
            user_id=current_user.id,
            date=date_obj,
            start_time=start_time,
            end_time=end_time,
            estimated_hours=estimated_hours,
            overtime_type=OvertimeType.NORMAL,
            justification=justification
        )
        
        # Verificar aprovação automática
        settings = OvertimeSettings.query.filter_by(user_id=current_user.id).first()
        if settings and estimated_hours <= settings.auto_approval_limit and not settings.requires_approval:
            overtime_request.status = OvertimeStatus.APROVADA
            overtime_request.approved_at = datetime.now()
            overtime_request.multiplier_applied = settings.get_multiplier(overtime_request.overtime_type)
            status_message = 'Solicitação aprovada automaticamente!'
        else:
            status_message = 'Solicitação enviada para aprovação!'
        
        db.session.add(overtime_request)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': status_message,
            'request_id': overtime_request.id,
            'estimated_hours': estimated_hours
        })
        
    except ValueError as e:
        return jsonify({'error': f'Formato de data/hora inválido: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@bp.route('/api/compensation-quick-request', methods=['POST'])
@login_required
def quick_compensation_request():
    """API para solicitação rápida de compensação"""
    data = request.get_json()
    
    try:
        # Validar dados
        date_str = data.get('date')
        hours = data.get('hours')
        justification = data.get('justification', '').strip()
        
        if not all([date_str, hours]):
            return jsonify({'error': 'Data e horas são obrigatórios'}), 400
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        hours = float(hours)
        
        # Validações
        if date_obj <= date.today():
            return jsonify({'error': 'Data deve ser futura'}), 400
        
        if hours <= 0 or hours > 8:
            return jsonify({'error': 'Horas devem estar entre 0.5 e 8'}), 400
        
        # Verificar saldo
        if not current_user.hour_bank or not current_user.hour_bank.can_debit(hours):
            current_balance = current_user.hour_bank.formatted_balance if current_user.hour_bank else "0h 0m"
            return jsonify({'error': f'Saldo insuficiente. Saldo atual: {current_balance}'}), 400
        
        # Criar solicitação
        compensation = HourCompensation(
            user_id=current_user.id,
            requested_date=date_obj,
            hours_to_compensate=hours,
            justification=justification or f"Compensação de {hours}h"
        )
        
        db.session.add(compensation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Solicitação de compensação enviada!',
            'compensation_id': compensation.id
        })
        
    except ValueError as e:
        return jsonify({'error': f'Dados inválidos: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
