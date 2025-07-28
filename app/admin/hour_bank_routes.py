"""
Rotas administrativas para gerenciamento do banco de horas
"""
from datetime import datetime, date, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, make_response
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func
from app import db
from app.admin import bp
from app.decorators import admin_required
from app.models import (
    User, HourBank, HourBankTransaction, OvertimeRequest, HourCompensation,
    OvertimeSettings, OvertimeLimits, OvertimeType, OvertimeStatus,
    HourBankTransactionType, CompensationStatus, Notification, NotificationType
)
from app.forms import (
    OvertimeRequestForm, OvertimeApprovalForm, HourCompensationForm,
    HourCompensationApprovalForm, OvertimeSettingsForm, HourBankAdjustmentForm,
    HourBankTransferForm, OvertimeLimitsForm, HourBankReportForm
)


@bp.route('/hour-bank')
@login_required
@admin_required
def hour_bank_dashboard():
    """Dashboard principal do banco de horas"""
    # Estatísticas gerais
    total_users_with_bank = HourBank.query.count()
    total_positive_balance = db.session.query(func.sum(HourBank.current_balance)).filter(
        HourBank.current_balance > 0
    ).scalar() or 0
    total_negative_balance = abs(db.session.query(func.sum(HourBank.current_balance)).filter(
        HourBank.current_balance < 0
    ).scalar() or 0)
    
    # Transações recentes
    recent_transactions = HourBankTransaction.query.join(User).order_by(
        HourBankTransaction.created_at.desc()
    ).limit(10).all()
    
    # Solicitações pendentes
    pending_overtime = OvertimeRequest.query.filter_by(
        status=OvertimeStatus.PENDENTE
    ).order_by(OvertimeRequest.created_at.desc()).limit(5).all()
    
    pending_compensations = HourCompensation.query.filter_by(
        status=CompensationStatus.PENDENTE
    ).order_by(HourCompensation.created_at.desc()).limit(5).all()
    
    # Usuários com maior saldo
    top_positive_balances = HourBank.query.join(User).filter(
        HourBank.current_balance > 0
    ).order_by(HourBank.current_balance.desc()).limit(5).all()
    
    # Usuários com saldo negativo
    negative_balances = HourBank.query.join(User).filter(
        HourBank.current_balance < 0
    ).order_by(HourBank.current_balance.asc()).limit(5).all()
    
    return render_template('admin/hour_bank/dashboard.html',
                         total_users_with_bank=total_users_with_bank,
                         total_positive_balance=total_positive_balance,
                         total_negative_balance=total_negative_balance,
                         recent_transactions=recent_transactions,
                         pending_overtime=pending_overtime,
                         pending_compensations=pending_compensations,
                         top_positive_balances=top_positive_balances,
                         negative_balances=negative_balances)


@bp.route('/hour-bank/users')
@login_required
@admin_required
def hour_bank_users():
    """Lista todos os usuários e seus bancos de horas"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    balance_filter = request.args.get('balance', '', type=str)
    
    # Query base
    query = db.session.query(User).outerjoin(HourBank)
    
    # Filtro de busca
    if search:
        query = query.filter(
            or_(
                User.nome.contains(search),
                User.sobrenome.contains(search),
                User.email.contains(search)
            )
        )
    
    # Filtro por saldo
    if balance_filter == 'positive':
        query = query.filter(HourBank.current_balance > 0)
    elif balance_filter == 'negative':
        query = query.filter(HourBank.current_balance < 0)
    elif balance_filter == 'zero':
        query = query.filter(
            or_(HourBank.current_balance == 0, HourBank.current_balance.is_(None))
        )
    
    users = query.order_by(User.nome).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/hour_bank/users.html',
                         users=users,
                         search=search,
                         balance_filter=balance_filter)


@bp.route('/hour-bank/user/<int:user_id>')
@login_required
@admin_required
def hour_bank_user_detail(user_id):
    """Detalhes do banco de horas de um usuário específico"""
    user = User.query.get_or_404(user_id)
    
    # Criar banco de horas se não existir
    if not user.hour_bank:
        hour_bank = HourBank(user_id=user.id)
        db.session.add(hour_bank)
        db.session.commit()
    
    # Histórico de transações
    page = request.args.get('page', 1, type=int)
    transactions = HourBankTransaction.query.filter_by(
        user_id=user.id
    ).order_by(HourBankTransaction.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Solicitações de horas extras
    overtime_requests = OvertimeRequest.query.filter_by(
        user_id=user.id
    ).order_by(OvertimeRequest.created_at.desc()).limit(10).all()
    
    # Compensações
    compensations = HourCompensation.query.filter_by(
        user_id=user.id
    ).order_by(HourCompensation.created_at.desc()).limit(10).all()
    
    return render_template('admin/hour_bank/user_detail.html',
                         user=user,
                         transactions=transactions,
                         overtime_requests=overtime_requests,
                         compensations=compensations)


@bp.route('/hour-bank/adjust/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def hour_bank_adjust(user_id):
    """Ajustar banco de horas de um usuário"""
    user = User.query.get_or_404(user_id)
    form = HourBankAdjustmentForm()
    
    # Criar banco de horas se não existir
    if not user.hour_bank:
        hour_bank = HourBank(user_id=user.id)
        db.session.add(hour_bank)
        db.session.commit()
    
    if form.validate_on_submit():
        try:
            hours = form.hours.data
            description = form.description.data
            reference_date = form.reference_date.data
            
            # Usar o método admin_adjust_hours que permite saldos negativos
            user.hour_bank.admin_adjust_hours(
                hours_adjustment=hours,
                transaction_type=HourBankTransactionType.AJUSTE,
                description=f"Ajuste manual: {description}"
            )
            
            # Atualizar referência da transação
            transaction = HourBankTransaction.query.filter_by(
                user_id=user.id
            ).order_by(HourBankTransaction.created_at.desc()).first()
            
            if transaction:
                transaction.reference_date = reference_date
                transaction.created_by = current_user.id
            
            db.session.commit()
            
            # Notificar usuário
            notification = Notification(
                user_id=user.id,
                sender_id=current_user.id,
                titulo='Ajuste no Banco de Horas',
                mensagem=f'Seu banco de horas foi ajustado em {hours:+.1f}h. Motivo: {description}',
                tipo=NotificationType.INFO
            )
            db.session.add(notification)
            db.session.commit()
            
            flash(f'Banco de horas de {user.nome_completo} ajustado com sucesso!', 'success')
            return redirect(url_for('admin.hour_bank_user_detail', user_id=user.id))
            
        except ValueError as e:
            flash(f'Erro ao ajustar banco de horas: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro inesperado: {str(e)}', 'error')
    
    return render_template('admin/hour_bank/adjust.html', user=user, form=form)


@bp.route('/hour-bank/transfer', methods=['GET', 'POST'])
@login_required
@admin_required
def hour_bank_transfer():
    """Transferir horas entre usuários"""
    form = HourBankTransferForm()
    
    if form.validate_on_submit():
        try:
            from_user_id = int(form.from_user_id.data)
            to_user_id = int(form.to_user_id.data)
            hours = form.hours.data
            description = form.description.data
            
            from_user = User.query.get_or_404(from_user_id)
            to_user = User.query.get_or_404(to_user_id)
            
            # Verificar se usuário de origem tem banco de horas
            if not from_user.hour_bank:
                flash('Usuário de origem não possui banco de horas.', 'error')
                return render_template('admin/hour_bank/transfer.html', form=form)
            
            # Verificar saldo suficiente
            if not from_user.hour_bank.can_debit(hours):
                flash(f'Saldo insuficiente. Saldo atual: {from_user.hour_bank.formatted_balance}', 'error')
                return render_template('admin/hour_bank/transfer.html', form=form)
            
            # Criar banco de horas do destinatário se não existir
            if not to_user.hour_bank:
                to_hour_bank = HourBank(user_id=to_user.id)
                db.session.add(to_hour_bank)
                db.session.flush()
            
            # Realizar transferência
            from_user.hour_bank.debit_hours(
                hours,
                HourBankTransactionType.DEBITO,
                f"Transferência para {to_user.nome_completo}: {description}"
            )
            
            to_user.hour_bank.add_hours(
                hours,
                HourBankTransactionType.CREDITO,
                f"Transferência de {from_user.nome_completo}: {description}"
            )
            
            # Atualizar transações com criador
            recent_transactions = HourBankTransaction.query.filter(
                or_(
                    HourBankTransaction.user_id == from_user_id,
                    HourBankTransaction.user_id == to_user_id
                )
            ).order_by(HourBankTransaction.created_at.desc()).limit(2).all()
            
            for transaction in recent_transactions:
                transaction.created_by = current_user.id
            
            db.session.commit()
            
            # Notificar usuários
            from_notification = Notification(
                user_id=from_user.id,
                sender_id=current_user.id,
                titulo='Transferência de Horas - Débito',
                mensagem=f'{hours:.1f}h foram transferidas para {to_user.nome_completo}. Motivo: {description}',
                tipo=NotificationType.WARNING
            )
            
            to_notification = Notification(
                user_id=to_user.id,
                sender_id=current_user.id,
                titulo='Transferência de Horas - Crédito',
                mensagem=f'{hours:.1f}h foram recebidas de {from_user.nome_completo}. Motivo: {description}',
                tipo=NotificationType.SUCCESS
            )
            
            db.session.add_all([from_notification, to_notification])
            db.session.commit()
            
            flash(f'Transferência de {hours:.1f}h realizada com sucesso!', 'success')
            return redirect(url_for('admin.hour_bank_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao realizar transferência: {str(e)}', 'error')
    
    return render_template('admin/hour_bank/transfer.html', form=form)


@bp.route('/overtime-requests')
@login_required
@admin_required
def overtime_requests():
    """Lista solicitações de horas extras"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '', type=str)
    user_filter = request.args.get('user', '', type=str)
    
    query = OvertimeRequest.query.join(User)
    
    # Filtros
    if status_filter:
        query = query.filter(OvertimeRequest.status == OvertimeStatus(status_filter))
    
    if user_filter:
        query = query.filter(
            or_(
                User.nome.contains(user_filter),
                User.sobrenome.contains(user_filter),
                User.email.contains(user_filter)
            )
        )
    
    requests = query.order_by(OvertimeRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/hour_bank/overtime_requests.html',
                         requests=requests,
                         status_filter=status_filter,
                         user_filter=user_filter,
                         overtime_status=OvertimeStatus)


@bp.route('/overtime-request/<int:request_id>/approve', methods=['GET', 'POST'])
@login_required
@admin_required
def approve_overtime_request(request_id):
    """Aprovar ou rejeitar solicitação de horas extras"""
    overtime_request = OvertimeRequest.query.get_or_404(request_id)
    form = OvertimeApprovalForm()
    
    if form.validate_on_submit():
        action = form.action.data
        
        if action == 'approve':
            overtime_request.status = OvertimeStatus.APROVADA
            overtime_request.approved_by = current_user.id
            overtime_request.approved_at = datetime.now()
            overtime_request.actual_hours = form.actual_hours.data or overtime_request.estimated_hours
            
            # Calcular multiplicador
            settings = OvertimeSettings.query.filter_by(user_id=overtime_request.user_id).first()
            if settings:
                overtime_request.multiplier_applied = settings.get_multiplier(overtime_request.overtime_type)
            else:
                overtime_request.multiplier_applied = 1.5
            
            # Notificar usuário
            notification = Notification(
                user_id=overtime_request.user_id,
                sender_id=current_user.id,
                titulo='Solicitação de Horas Extras Aprovada',
                mensagem=f'Sua solicitação de horas extras para {overtime_request.date.strftime("%d/%m/%Y")} foi aprovada.',
                tipo=NotificationType.SUCCESS
            )
            
            flash('Solicitação de horas extras aprovada!', 'success')
            
        elif action == 'reject':
            overtime_request.status = OvertimeStatus.REJEITADA
            overtime_request.approved_by = current_user.id
            overtime_request.approved_at = datetime.now()
            overtime_request.rejection_reason = form.rejection_reason.data
            
            # Notificar usuário
            notification = Notification(
                user_id=overtime_request.user_id,
                sender_id=current_user.id,
                titulo='Solicitação de Horas Extras Rejeitada',
                mensagem=f'Sua solicitação de horas extras para {overtime_request.date.strftime("%d/%m/%Y")} foi rejeitada. Motivo: {form.rejection_reason.data}',
                tipo=NotificationType.ERROR
            )
            
            flash('Solicitação de horas extras rejeitada.', 'warning')
        
        db.session.add(notification)
        db.session.commit()
        
        return redirect(url_for('admin.overtime_requests'))
    
    return render_template('admin/hour_bank/approve_overtime.html',
                         overtime_request=overtime_request,
                         form=form)


@bp.route('/hour-compensations')
@login_required
@admin_required
def hour_compensations():
    """Lista solicitações de compensação de horas"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '', type=str)
    user_filter = request.args.get('user', '', type=str)
    
    query = HourCompensation.query.join(User)
    
    # Filtros
    if status_filter:
        query = query.filter(HourCompensation.status == CompensationStatus(status_filter))
    
    if user_filter:
        query = query.filter(
            or_(
                User.nome.contains(user_filter),
                User.sobrenome.contains(user_filter),
                User.email.contains(user_filter)
            )
        )
    
    compensations = query.order_by(HourCompensation.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/hour_bank/compensations.html',
                         compensations=compensations,
                         status_filter=status_filter,
                         user_filter=user_filter,
                         compensation_status=CompensationStatus)


@bp.route('/hour-compensation/<int:compensation_id>/approve', methods=['GET', 'POST'])
@login_required
@admin_required
def approve_compensation(compensation_id):
    """Aprovar ou rejeitar solicitação de compensação"""
    compensation = HourCompensation.query.get_or_404(compensation_id)
    form = HourCompensationApprovalForm()
    
    if form.validate_on_submit():
        action = form.action.data
        
        if action == 'approve':
            # Verificar se usuário tem saldo suficiente
            if not compensation.can_apply():
                flash('Usuário não possui saldo suficiente para esta compensação.', 'error')
                return render_template('admin/hour_bank/approve_compensation.html',
                                     compensation=compensation, form=form)
            
            # Aplicar compensação
            compensation.user.hour_bank.debit_hours(
                compensation.hours_to_compensate,
                HourBankTransactionType.COMPENSACAO,
                f"Compensação aprovada para {compensation.requested_date.strftime('%d/%m/%Y')}"
            )
            
            compensation.status = CompensationStatus.APLICADA
            compensation.approved_by = current_user.id
            compensation.approved_at = datetime.now()
            compensation.applied_at = datetime.now()
            
            # Associar transação
            transaction = HourBankTransaction.query.filter_by(
                user_id=compensation.user_id
            ).order_by(HourBankTransaction.created_at.desc()).first()
            
            if transaction:
                compensation.hour_bank_transaction_id = transaction.id
            
            # Notificar usuário
            notification = Notification(
                user_id=compensation.user_id,
                sender_id=current_user.id,
                titulo='Compensação de Horas Aprovada',
                mensagem=f'Sua solicitação de compensação para {compensation.requested_date.strftime("%d/%m/%Y")} foi aprovada.',
                tipo=NotificationType.SUCCESS
            )
            
            flash('Compensação aprovada e aplicada!', 'success')
            
        elif action == 'reject':
            compensation.status = CompensationStatus.CANCELADA
            compensation.approved_by = current_user.id
            compensation.approved_at = datetime.now()
            compensation.rejection_reason = form.rejection_reason.data
            
            # Notificar usuário
            notification = Notification(
                user_id=compensation.user_id,
                sender_id=current_user.id,
                titulo='Compensação de Horas Rejeitada',
                mensagem=f'Sua solicitação de compensação para {compensation.requested_date.strftime("%d/%m/%Y")} foi rejeitada. Motivo: {form.rejection_reason.data}',
                tipo=NotificationType.ERROR
            )
            
            flash('Compensação rejeitada.', 'warning')
        
        db.session.add(notification)
        db.session.commit()
        
        return redirect(url_for('admin.hour_compensations'))
    
    return render_template('admin/hour_bank/approve_compensation.html',
                         compensation=compensation,
                         form=form)


@bp.route('/hour-bank/settings')
@login_required
@admin_required
def hour_bank_settings():
    """Configurações gerais do banco de horas"""
    # Buscar configurações existentes
    overtime_limits = OvertimeLimits.query.filter_by(is_active=True).all()
    
    # Estatísticas de uso
    total_overtime_requests = OvertimeRequest.query.count()
    pending_overtime_requests = OvertimeRequest.query.filter_by(status=OvertimeStatus.PENDENTE).count()
    total_compensations = HourCompensation.query.count()
    pending_compensations = HourCompensation.query.filter_by(status=CompensationStatus.PENDENTE).count()
    
    return render_template('admin/hour_bank/settings.html',
                         overtime_limits=overtime_limits,
                         total_overtime_requests=total_overtime_requests,
                         pending_overtime_requests=pending_overtime_requests,
                         total_compensations=total_compensations,
                         pending_compensations=pending_compensations)


@bp.route('/hour-bank/reports', methods=['GET', 'POST'])
@login_required
@admin_required
def hour_bank_reports():
    """Relatórios do banco de horas"""
    form = HourBankReportForm()
    
    if form.validate_on_submit():
        # Construir query baseada nos filtros
        query = HourBankTransaction.query.join(User)
        
        # Filtros
        if form.user_id.data:
            query = query.filter(HourBankTransaction.user_id == int(form.user_id.data))
        
        if form.start_date.data:
            query = query.filter(HourBankTransaction.created_at >= form.start_date.data)
        
        if form.end_date.data:
            end_date = datetime.combine(form.end_date.data, datetime.max.time())
            query = query.filter(HourBankTransaction.created_at <= end_date)
        
        if form.transaction_type.data:
            query = query.filter(HourBankTransaction.transaction_type == HourBankTransactionType(form.transaction_type.data))
        
        transactions = query.order_by(HourBankTransaction.created_at.desc()).all()
        
        # Gerar relatório baseado no formato
        if form.format_type.data == 'pdf':
            return generate_hour_bank_pdf_report(transactions, form)
        elif form.format_type.data == 'excel':
            return generate_hour_bank_excel_report(transactions, form)
        else:
            # HTML
            return render_template('admin/hour_bank/report_result.html',
                                 transactions=transactions,
                                 form=form)
    
    return render_template('admin/hour_bank/reports.html', form=form)


def generate_hour_bank_pdf_report(transactions, form):
    """Gera relatório em PDF"""
    try:
        from app.pdf_utils import create_hour_bank_report_pdf
        
        # Preparar dados para o PDF
        report_data = {
            'title': 'Relatório de Banco de Horas',
            'generated_at': datetime.now(),
            'generated_by': current_user.nome_completo,
            'filters': {
                'user': form.user_id.data,
                'start_date': form.start_date.data,
                'end_date': form.end_date.data,
                'transaction_type': form.transaction_type.data
            },
            'transactions': transactions
        }
        
        pdf_content = create_hour_bank_report_pdf(report_data)
        
        response = make_response(pdf_content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=relatorio_banco_horas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        return response
        
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'error')
        return redirect(url_for('admin.hour_bank_reports'))


def generate_hour_bank_excel_report(transactions, form):
    """Gera relatório em Excel"""
    try:
        import pandas as pd
        from io import BytesIO
        
        # Preparar dados
        data = []
        for t in transactions:
            data.append({
                'Data': t.created_at.strftime('%d/%m/%Y %H:%M'),
                'Usuário': t.user.nome_completo,
                'Email': t.user.email,
                'Tipo': t.transaction_type.value,
                'Horas': t.hours,
                'Saldo Anterior': t.balance_before or 0,
                'Saldo Após': t.balance_after,
                'Descrição': t.description or '',
                'Data Referência': t.reference_date.strftime('%d/%m/%Y') if t.reference_date else '',
                'Criado Por': t.creator.nome_completo if t.creator else 'Sistema'
            })
        
        # Criar DataFrame
        df = pd.DataFrame(data)
        
        # Criar arquivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Banco de Horas', index=False)
        
        output.seek(0)
        
        response = make_response(output.read())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=relatorio_banco_horas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except ImportError:
        flash('Pandas não está instalado. Instale com: pip install pandas openpyxl', 'error')
        return redirect(url_for('admin.hour_bank_reports'))
    except Exception as e:
        flash(f'Erro ao gerar Excel: {str(e)}', 'error')
        return redirect(url_for('admin.hour_bank_reports'))


@bp.route('/api/hour-bank/stats')
@login_required
@admin_required
def hour_bank_stats_api():
    """API para estatísticas do banco de horas (para gráficos)"""
    # Estatísticas por mês (últimos 12 meses)
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    
    end_date = datetime.now()
    start_date = end_date - relativedelta(months=12)
    
    # Transações por mês
    monthly_stats = db.session.query(
        func.date_trunc('month', HourBankTransaction.created_at).label('month'),
        func.sum(func.case([(HourBankTransaction.hours > 0, HourBankTransaction.hours)], else_=0)).label('credits'),
        func.sum(func.case([(HourBankTransaction.hours < 0, func.abs(HourBankTransaction.hours))], else_=0)).label('debits')
    ).filter(
        HourBankTransaction.created_at >= start_date
    ).group_by('month').order_by('month').all()
    
    # Converter para formato JSON
    months = []
    credits = []
    debits = []
    
    for stat in monthly_stats:
        months.append(stat.month.strftime('%Y-%m'))
        credits.append(float(stat.credits or 0))
        debits.append(float(stat.debits or 0))
    
    return jsonify({
        'months': months,
        'credits': credits,
        'debits': debits,
        'total_users': HourBank.query.count(),
        'positive_balance_users': HourBank.query.filter(HourBank.current_balance > 0).count(),
        'negative_balance_users': HourBank.query.filter(HourBank.current_balance < 0).count()
    })
