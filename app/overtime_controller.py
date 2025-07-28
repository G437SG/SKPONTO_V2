#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controlador Principal de Horas Extras - SKPONTO
Sistema completo de controle e automação de horas extras
"""

import os
import sys
from datetime import datetime, date, timedelta
from flask import current_app, flash
from sqlalchemy import func, and_, or_
from app.models import (
    User, TimeRecord, HourBank, HourBankTransaction, OvertimeRequest,
    OvertimeSettings, OvertimeLimits, HourCompensation, WorkClass,
    OvertimeType, OvertimeStatus, HourBankTransactionType, CompensationStatus,
    Notification, NotificationType, UserType, HourBankHistory
)

class OvertimeController:
    """Controlador principal para horas extras"""
    
    def __init__(self):
        self.app = current_app
        # Importar db aqui para evitar circular import
        from app import db
        self.db = db
    
    def calculate_daily_hours(self, user_id, target_date):
        """Calcula horas trabalhadas em um dia específico"""
        try:
            # Buscar registro de ponto do dia
            time_record = TimeRecord.query.filter(
                TimeRecord.user_id == user_id,
                TimeRecord.data == target_date
            ).first()
            
            if not time_record:
                return {
                    'worked_hours': 0.0,
                    'expected_hours': 0.0,
                    'overtime_hours': 0.0,
                    'deficit_hours': 0.0,
                    'status': 'no_record'
                }
            
            # Obter classe de trabalho do usuário
            user = User.query.get(user_id)
            expected_hours = user.work_class.daily_work_hours if user.work_class else 8.0
            
            # Calcular horas trabalhadas
            worked_hours = 0.0
            if time_record.entrada and time_record.saida:
                from app.utils import calculate_work_hours
                worked_hours, _ = calculate_work_hours(
                    time_record.entrada,
                    time_record.saida,
                    target_date,
                    expected_hours
                )
            
            # Calcular horas extras e déficit
            overtime_hours = max(0.0, worked_hours - expected_hours)
            deficit_hours = max(0.0, expected_hours - worked_hours)
            
            return {
                'worked_hours': worked_hours,
                'expected_hours': expected_hours,
                'overtime_hours': overtime_hours,
                'deficit_hours': deficit_hours,
                'status': 'calculated'
            }
            
        except Exception as e:
            self.app.logger.error(f"Erro ao calcular horas diárias: {str(e)}")
            return {
                'worked_hours': 0.0,
                'expected_hours': 0.0,
                'overtime_hours': 0.0,
                'deficit_hours': 0.0,
                'status': 'error',
                'error': str(e)
            }
    
    def process_automatic_adjustments(self, user_id, target_date):
        """Processa ajustes automáticos de horas"""
        try:
            # Calcular horas do dia
            daily_calc = self.calculate_daily_hours(user_id, target_date)
            
            if daily_calc['status'] != 'calculated':
                return False
            
            user = User.query.get(user_id)
            
            # Criar ou atualizar banco de horas
            if not user.hour_bank:
                hour_bank = HourBank(user_id=user_id)
                self.db.session.add(hour_bank)
                self.db.session.commit()
            
            # Processar horas extras
            if daily_calc['overtime_hours'] > 0:
                self._process_overtime_addition(user, daily_calc, target_date)
            
            # Processar déficit de horas
            if daily_calc['deficit_hours'] > 0:
                self._process_deficit_subtraction(user, daily_calc, target_date)
            
            return True
            
        except Exception as e:
            self.app.logger.error(f"Erro no processamento automático: {str(e)}")
            return False
    
    def _process_overtime_addition(self, user, daily_calc, target_date):
        """Processa adição de horas extras ao banco"""
        try:
            overtime_hours = daily_calc['overtime_hours']
            
            # Obter configurações do usuário
            settings = OvertimeSettings.query.filter_by(user_id=user.id).first()
            multiplier = 1.5  # Padrão
            
            if settings:
                multiplier = settings.overtime_multiplier_normal
            
            # Calcular horas efetivas com multiplicador
            effective_hours = overtime_hours * multiplier
            
            # Adicionar ao banco de horas
            user.hour_bank.add_hours(
                effective_hours,
                HourBankTransactionType.CREDITO,
                f"Horas extras do dia {target_date.strftime('%d/%m/%Y')}: {overtime_hours:.2f}h (multiplicador {multiplier}x)"
            )
            
            # Criar notificação
            notification = Notification(
                user_id=user.id,
                titulo='Horas Extras Adicionadas',
                mensagem=f'Adicionadas {effective_hours:.2f}h ao seu banco de horas referente ao dia {target_date.strftime("%d/%m/%Y")}',
                tipo=NotificationType.SUCCESS
            )
            self.db.session.add(notification)
            self.db.session.commit()
            
            self.app.logger.info(f"Horas extras adicionadas: {user.nome} - {effective_hours:.2f}h")
            
        except Exception as e:
            self.app.logger.error(f"Erro ao processar horas extras: {str(e)}")
            self.db.session.rollback()
    
    def _process_deficit_subtraction(self, user, daily_calc, target_date):
        """Processa subtração de horas por déficit"""
        try:
            deficit_hours = daily_calc['deficit_hours']
            
            # Verificar se há saldo suficiente
            if not user.hour_bank.can_debit(deficit_hours):
                # Criar notificação de saldo insuficiente
                notification = Notification(
                    user_id=user.id,
                    titulo='Saldo Insuficiente no Banco de Horas',
                    mensagem=f'Déficit de {deficit_hours:.2f}h no dia {target_date.strftime("%d/%m/%Y")} não pôde ser debitado. Saldo atual: {user.hour_bank.current_balance:.2f}h',
                    tipo=NotificationType.WARNING
                )
                self.db.session.add(notification)
                self.db.session.commit()
                return
            
            # Debitar horas do banco
            user.hour_bank.debit_hours(
                deficit_hours,
                HourBankTransactionType.DEBITO,
                f"Déficit de horas do dia {target_date.strftime('%d/%m/%Y')}: {deficit_hours:.2f}h"
            )
            
            # Criar notificação
            notification = Notification(
                user_id=user.id,
                titulo='Horas Debitadas por Déficit',
                mensagem=f'Debitadas {deficit_hours:.2f}h do seu banco de horas referente ao déficit do dia {target_date.strftime("%d/%m/%Y")}',
                tipo=NotificationType.INFO
            )
            self.db.session.add(notification)
            self.db.session.commit()
            
            self.app.logger.info(f"Déficit de horas debitado: {user.nome} - {deficit_hours:.2f}h")
            
        except Exception as e:
            self.app.logger.error(f"Erro ao processar déficit: {str(e)}")
            self.db.session.rollback()
    
    def admin_adjust_hours(self, user_id, hours_adjustment, reason, admin_id):
        """Permite ao administrador ajustar horas manualmente"""
        try:
            user = User.query.get(user_id)
            admin = User.query.get(admin_id)
            
            if not user or not admin:
                return False, "Usuário ou administrador não encontrado"
            
            # Criar ou obter banco de horas
            hour_bank = user.hour_bank
            if not hour_bank:
                hour_bank = HourBank(user_id=user_id)
                self.db.session.add(hour_bank)
                self.db.session.flush()  # Para obter o ID
                user.hour_bank = hour_bank
            
            # Armazenar saldo anterior para histórico
            old_balance = hour_bank.current_balance
            
            # Aplicar ajuste usando o novo método que permite saldo negativo
            description = f"Ajuste manual pelo admin {admin.nome_completo}: {reason}"
            hour_bank.admin_adjust_hours(hours_adjustment, HourBankTransactionType.AJUSTE, description)
            
            # Atualizar a transação com o ID do admin
            transaction = HourBankTransaction.query.filter_by(
                user_id=user_id
            ).order_by(HourBankTransaction.created_at.desc()).first()
            
            if transaction:
                transaction.created_by = admin_id
            
            # Criar registro no histórico
            history = HourBankHistory(
                user_id=user_id,
                admin_id=admin_id,
                old_balance=old_balance,
                adjustment=hours_adjustment,
                new_balance=hour_bank.current_balance,
                reason=reason
            )
            self.db.session.add(history)
            
            # Criar notificação para o usuário
            notification = Notification(
                user_id=user.id,
                sender_id=admin_id,
                titulo='Ajuste Manual no Banco de Horas',
                mensagem=f'Seu banco de horas foi ajustado em {hours_adjustment:+.2f}h pelo administrador. Motivo: {reason}. Saldo anterior: {old_balance:.2f}h, novo saldo: {hour_bank.current_balance:.2f}h',
                tipo=NotificationType.INFO
            )
            self.db.session.add(notification)
            
            # Commit todas as alterações
            self.db.session.commit()
            
            self.app.logger.info(f"Ajuste manual aplicado: {admin.nome_completo} ajustou {hours_adjustment:+.2f}h para {user.nome_completo}. Saldo: {old_balance:.2f}h → {hour_bank.current_balance:.2f}h")
            
            return True, f"Ajuste aplicado com sucesso. Saldo: {old_balance:.2f}h → {hour_bank.current_balance:.2f}h"
            
        except Exception as e:
            self.app.logger.error(f"Erro no ajuste manual: {str(e)}")
            self.db.session.rollback()
            return False, f"Erro interno: {str(e)}"
    
    def get_user_overtime_summary(self, user_id, start_date=None, end_date=None):
        """Obtém resumo de horas extras de um usuário"""
        try:
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()
            
            # Buscar solicitações de horas extras
            overtime_requests = OvertimeRequest.query.filter(
                OvertimeRequest.user_id == user_id,
                OvertimeRequest.date >= start_date,
                OvertimeRequest.date <= end_date
            ).all()
            
            # Calcular totais
            total_requested = sum(req.estimated_hours for req in overtime_requests)
            total_approved = sum(req.effective_hours for req in overtime_requests if req.is_approved)
            total_pending = sum(req.estimated_hours for req in overtime_requests if req.is_pending)
            
            # Buscar transações do banco de horas
            bank_transactions = HourBankTransaction.query.filter(
                HourBankTransaction.user_id == user_id,
                HourBankTransaction.created_at >= datetime.combine(start_date, datetime.min.time()),
                HourBankTransaction.created_at <= datetime.combine(end_date, datetime.max.time())
            ).all()
            
            overtime_transactions = [t for t in bank_transactions if t.transaction_type == HourBankTransactionType.CREDITO]
            deficit_transactions = [t for t in bank_transactions if t.transaction_type == HourBankTransactionType.DEBITO]
            
            total_overtime_added = sum(t.hours for t in overtime_transactions if t.hours > 0)
            total_deficit_deducted = sum(abs(t.hours) for t in deficit_transactions if t.hours < 0)
            
            return {
                'total_requested': total_requested,
                'total_approved': total_approved,
                'total_pending': total_pending,
                'total_overtime_added': total_overtime_added,
                'total_deficit_deducted': total_deficit_deducted,
                'current_balance': User.query.get(user_id).hour_bank.current_balance if User.query.get(user_id).hour_bank else 0.0,
                'overtime_requests': overtime_requests,
                'bank_transactions': bank_transactions
            }
            
        except Exception as e:
            self.app.logger.error(f"Erro ao obter resumo: {str(e)}")
            return None
    
    def get_system_overtime_stats(self):
        """Obtém estatísticas gerais do sistema"""
        try:
            # Estatísticas gerais
            total_users = User.query.count()
            users_with_overtime = self.db.session.query(func.count(func.distinct(OvertimeRequest.user_id))).scalar()
            
            # Solicitações de horas extras
            total_requests = OvertimeRequest.query.count()
            pending_requests = OvertimeRequest.query.filter_by(status=OvertimeStatus.PENDENTE).count()
            approved_requests = OvertimeRequest.query.filter_by(status=OvertimeStatus.APROVADA).count()
            
            # Horas extras por tipo
            overtime_by_type = self.db.session.query(
                OvertimeRequest.overtime_type,
                func.sum(OvertimeRequest.estimated_hours)
            ).group_by(OvertimeRequest.overtime_type).all()
            
            # Usuários com maior banco de horas
            top_hour_banks = self.db.session.query(
                HourBank.user_id,
                HourBank.current_balance,
                User.nome,
                User.sobrenome
            ).join(User).order_by(HourBank.current_balance.desc()).limit(10).all()
            
            # Estatísticas de integração automática
            automatic_stats = self._get_automatic_integration_stats()
            
            # Alertas de limites
            alerts = self._check_overtime_limits()
            
            return {
                'total_users': total_users,
                'users_with_overtime': users_with_overtime,
                'total_requests': total_requests,
                'pending_requests': pending_requests,
                'approved_requests': approved_requests,
                'overtime_by_type': overtime_by_type,
                'top_hour_banks': top_hour_banks,
                'automatic_stats': automatic_stats,
                'alerts': alerts
            }
            
        except Exception as e:
            self.app.logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return None
    
    def _get_automatic_integration_stats(self):
        """Obtém estatísticas do sistema de integração automática"""
        try:
            # Transações automáticas dos últimos 30 dias
            thirty_days_ago = date.today() - timedelta(days=30)
            
            # Horas extras creditadas automaticamente
            auto_credits = self.db.session.query(func.sum(HourBankTransaction.hours)).filter(
                HourBankTransaction.transaction_type == HourBankTransactionType.CREDITO,
                HourBankTransaction.time_record_id.isnot(None),
                HourBankTransaction.created_at >= thirty_days_ago,
                HourBankTransaction.hours > 0
            ).scalar() or 0
            
            # Horas debitadas automaticamente (déficit)
            auto_debits = self.db.session.query(func.sum(func.abs(HourBankTransaction.hours))).filter(
                HourBankTransaction.transaction_type == HourBankTransactionType.DEBITO,
                HourBankTransaction.time_record_id.isnot(None),
                HourBankTransaction.created_at >= thirty_days_ago,
                HourBankTransaction.hours < 0
            ).scalar() or 0
            
            # Número de transações automáticas
            auto_transactions_count = HourBankTransaction.query.filter(
                HourBankTransaction.time_record_id.isnot(None),
                HourBankTransaction.created_at >= thirty_days_ago
            ).count()
            
            # Usuários que se beneficiaram do sistema automático
            users_with_auto_credits = self.db.session.query(
                func.count(func.distinct(HourBankTransaction.user_id))
            ).filter(
                HourBankTransaction.transaction_type == HourBankTransactionType.CREDITO,
                HourBankTransaction.time_record_id.isnot(None),
                HourBankTransaction.created_at >= thirty_days_ago
            ).scalar() or 0
            
            # Usuários que tiveram déficit compensado automaticamente
            users_with_auto_debits = self.db.session.query(
                func.count(func.distinct(HourBankTransaction.user_id))
            ).filter(
                HourBankTransaction.transaction_type == HourBankTransactionType.DEBITO,
                HourBankTransaction.time_record_id.isnot(None),
                HourBankTransaction.created_at >= thirty_days_ago
            ).scalar() or 0
            
            # Registros de ponto processados automaticamente hoje
            today_processed = TimeRecord.query.join(HourBankTransaction).filter(
                TimeRecord.data == date.today()
            ).count()
            
            return {
                'auto_credits': round(auto_credits, 2),
                'auto_debits': round(auto_debits, 2),
                'auto_transactions_count': auto_transactions_count,
                'users_with_auto_credits': users_with_auto_credits,
                'users_with_auto_debits': users_with_auto_debits,
                'today_processed': today_processed,
                'period_days': 30
            }
            
        except Exception as e:
            self.app.logger.error(f"Erro ao obter estatísticas automáticas: {str(e)}")
            return {
                'auto_credits': 0,
                'auto_debits': 0,
                'auto_transactions_count': 0,
                'users_with_auto_credits': 0,
                'users_with_auto_debits': 0,
                'today_processed': 0,
                'period_days': 30
            }
    
    def _check_overtime_limits(self):
        """Verifica limites de horas extras e gera alertas"""
        alerts = []
        
        try:
            # Verificar limites por usuário
            users = User.query.filter_by(is_active=True).all()
            
            for user in users:
                settings = OvertimeSettings.query.filter_by(user_id=user.id).first()
                if not settings:
                    continue
                
                # Verificar limite diário (últimas 24h)
                daily_overtime = self.db.session.query(func.sum(OvertimeRequest.estimated_hours)).filter(
                    OvertimeRequest.user_id == user.id,
                    OvertimeRequest.date >= date.today(),
                    OvertimeRequest.status.in_([OvertimeStatus.PENDENTE, OvertimeStatus.APROVADA])
                ).scalar() or 0
                
                if daily_overtime > settings.max_daily_overtime:
                    alerts.append({
                        'type': 'daily_limit_exceeded',
                        'user': user,
                        'current': daily_overtime,
                        'limit': settings.max_daily_overtime
                    })
                
                # Verificar limite semanal
                week_start = date.today() - timedelta(days=date.today().weekday())
                weekly_overtime = self.db.session.query(func.sum(OvertimeRequest.estimated_hours)).filter(
                    OvertimeRequest.user_id == user.id,
                    OvertimeRequest.date >= week_start,
                    OvertimeRequest.status.in_([OvertimeStatus.PENDENTE, OvertimeStatus.APROVADA])
                ).scalar() or 0
                
                if weekly_overtime > settings.max_weekly_overtime:
                    alerts.append({
                        'type': 'weekly_limit_exceeded',
                        'user': user,
                        'current': weekly_overtime,
                        'limit': settings.max_weekly_overtime
                    })
            
            return alerts
            
        except Exception as e:
            self.app.logger.error(f"Erro ao verificar limites: {str(e)}")
            return []
    
    def process_daily_batch(self, target_date=None):
        """Processa lote diário de ajustes automáticos"""
        if not target_date:
            target_date = date.today() - timedelta(days=1)  # Processar dia anterior
        
        try:
            # Buscar todos os usuários ativos
            users = User.query.filter_by(is_active=True).all()
            processed = 0
            errors = 0
            
            for user in users:
                try:
                    if self.process_automatic_adjustments(user.id, target_date):
                        processed += 1
                    else:
                        errors += 1
                except Exception as e:
                    self.app.logger.error(f"Erro ao processar usuário {user.id}: {str(e)}")
                    errors += 1
            
            self.app.logger.info(f"Lote diário processado: {processed} usuários, {errors} erros")
            return processed, errors
            
        except Exception as e:
            self.app.logger.error(f"Erro no lote diário: {str(e)}")
            return 0, 1

# Função para inicializar o controlador
def init_overtime_controller(app):
    """Inicializa o controlador de horas extras"""
    with app.app_context():
        controller = OvertimeController()
        app.overtime_controller = controller
        return controller

# Decorator para controle de horas extras
def track_overtime(func):
    """Decorator para rastrear horas extras"""
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # Processar horas extras se necessário
        if hasattr(current_app, 'overtime_controller'):
            # Implementar lógica de rastreamento
            pass
        
        return result
    return wrapper
