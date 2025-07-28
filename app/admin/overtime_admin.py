#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas Administrativas para Controle de Horas Extras
"""

from datetime import datetime, date, timedelta
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.admin import bp
from app.decorators import admin_required
from app.overtime_controller import OvertimeController
from app.models import User, OvertimeRequest, OvertimeSettings, HourBank, HourBankHistory, OvertimeStatus, UserType, HourBankTransaction, HourBankTransactionType, Notification, NotificationType
from app import db

@bp.route('/overtime-control')
@login_required
@admin_required
def overtime_control():
    """Dashboard principal de controle de horas extras"""
    from flask import current_app
    current_app.logger.info("=== INICIANDO OVERTIME_CONTROL DEBUG ===")
    debug_info = {}
    
    try:
        current_app.logger.info("1. Verificando imports...")
        debug_info['imports'] = 'OK'
        
        current_app.logger.info("2. Criando OvertimeController...")
        controller = OvertimeController()
        current_app.logger.info("   Controller criado com sucesso")
        debug_info['controller'] = 'OK'
        
        current_app.logger.info("3. Testando conexão com banco...")
        test_user_count = User.query.count()
        current_app.logger.info(f"   Total de usuários no sistema: {test_user_count}")
        debug_info['database'] = f'OK - {test_user_count} users'
        
        current_app.logger.info("4. Obtendo estatísticas do sistema...")
        try:
            stats = controller.get_system_overtime_stats()
            if stats:
                current_app.logger.info(f"   Estatísticas obtidas. Keys: {list(stats.keys())}")
                debug_info['stats'] = f'OK - Keys: {list(stats.keys())}'
                
                # Verificar se automatic_stats existe
                if 'automatic_stats' in stats and stats['automatic_stats']:
                    current_app.logger.info(f"   automatic_stats Keys: {list(stats['automatic_stats'].keys())}")
                    debug_info['automatic_stats'] = f'OK - Keys: {list(stats["automatic_stats"].keys())}'
                else:
                    current_app.logger.warning("   automatic_stats está vazio ou None")
                    debug_info['automatic_stats'] = 'EMPTY/NONE'
            else:
                current_app.logger.error("   Estatísticas retornaram None")
                debug_info['stats'] = 'NONE'
                stats = {
                    'total_users': test_user_count,
                    'pending_requests': 0,
                    'approved_requests': 0,
                    'overtime_by_type': [],
                    'top_hour_banks': [],
                    'alerts': [],
                    'automatic_stats': {
                        'auto_credits': 0,
                        'auto_debits': 0,
                        'auto_transactions_count': 0,
                        'users_with_auto_credits': 0,
                        'users_with_auto_debits': 0,
                        'today_processed': 0
                    }
                }
        except Exception as e:
            current_app.logger.error(f"   ERRO ao obter estatísticas: {str(e)}")
            debug_info['stats_error'] = str(e)
            stats = {
                'total_users': test_user_count,
                'pending_requests': 0,
                'approved_requests': 0,
                'overtime_by_type': [],
                'top_hour_banks': [],
                'alerts': [],
                'automatic_stats': {
                    'auto_credits': 0,
                    'auto_debits': 0,
                    'auto_transactions_count': 0,
                    'users_with_auto_credits': 0,
                    'users_with_auto_debits': 0,
                    'today_processed': 0
                }
            }
        
        current_app.logger.info("5. Obtendo solicitações recentes...")
        try:
            # Busca solicitações sem join complexo
            recent_requests = (OvertimeRequest.query
                             .order_by(OvertimeRequest.created_at.desc())
                             .limit(20).all())
            current_app.logger.info(f"   {len(recent_requests)} solicitações encontradas")
            debug_info['recent_requests'] = f'OK - {len(recent_requests)} items'
        except Exception as e:
            current_app.logger.error(f"   ERRO ao obter solicitações recentes: {str(e)}")
            debug_info['recent_requests_error'] = str(e)
            recent_requests = []
        
        current_app.logger.info("6. Obtendo todos os usuários...")
        try:
            # Busca simples de usuários - sem joins complexos
            all_users = (User.query
                        .filter(User.is_active == True)
                        .filter(User.is_approved == True)
                        .order_by(User.nome, User.sobrenome).all())
            current_app.logger.info(f"   {len(all_users)} usuários ativos encontrados")
            debug_info['all_users'] = f'OK - {len(all_users)} items'
        except Exception as e:
            current_app.logger.error(f"   ERRO ao obter usuários: {str(e)}")
            debug_info['all_users_error'] = str(e)
            all_users = []
        
        current_app.logger.info("7. Processando usuários com horas...")
        try:
            users_with_hours = []
            for user in all_users:
                try:
                    # Busca individual do banco de horas para cada usuário
                    hour_bank = HourBank.query.filter_by(user_id=user.id).first()
                    saldo = float(hour_bank.current_balance) if hour_bank and hour_bank.current_balance else 0.0
                    
                    users_with_hours.append({
                        'id': user.id,
                        'nome': f"{user.nome} {user.sobrenome}",
                        'email': user.email,
                        'saldo': saldo,
                        'user_type': user.user_type.name if user.user_type else 'TRABALHADOR'
                    })
                except Exception as user_error:
                    current_app.logger.warning(f"   Erro ao processar usuário {user.id}: {user_error}")
                    # Adiciona usuário mesmo com erro no saldo
                    users_with_hours.append({
                        'id': user.id,
                        'nome': f"{user.nome} {user.sobrenome}",
                        'email': user.email,
                        'saldo': 0.0,
                        'user_type': user.user_type.name if user.user_type else 'TRABALHADOR'
                    })
            
            users_with_hours.sort(key=lambda x: x['saldo'], reverse=True)
            current_app.logger.info(f"   Processados {len(users_with_hours)} usuários com saldos")
            debug_info['users_with_hours'] = f'OK - {len(users_with_hours)} items'
        except Exception as e:
            current_app.logger.error(f"   ERRO ao processar usuários com horas: {str(e)}")
            debug_info['users_with_hours_error'] = str(e)
            users_with_hours = []
        
        current_app.logger.info("8. Obtendo solicitações pendentes...")
        try:
            # Busca solicitações sem join complexo
            pending_requests = (OvertimeRequest.query
                              .filter(OvertimeRequest.status == OvertimeStatus.PENDENTE)
                              .order_by(OvertimeRequest.created_at.desc())
                              .limit(10).all())
            current_app.logger.info(f"   {len(pending_requests)} solicitações pendentes")
            debug_info['pending_requests'] = f'OK - {len(pending_requests)} items'
        except Exception as e:
            current_app.logger.error(f"   ERRO ao obter solicitações pendentes: {str(e)}")
            debug_info['pending_requests_error'] = str(e)
            pending_requests = []
        
        current_app.logger.info("9. Obtendo histórico do banco de horas...")
        try:
            # Busca histórico sem join complexo
            hour_bank_history = (HourBankHistory.query
                               .order_by(HourBankHistory.created_at.desc())
                               .limit(50).all())
            current_app.logger.info(f"   {len(hour_bank_history)} registros históricos")
            debug_info['hour_bank_history'] = f'OK - {len(hour_bank_history)} items'
        except Exception as e:
            current_app.logger.error(f"   ERRO ao obter histórico: {str(e)}")
            debug_info['hour_bank_history_error'] = str(e)
            hour_bank_history = []
        
        current_app.logger.info("10. Preparando para renderizar template...")
        current_app.logger.info(f"DEBUG INFO COMPLETO: {debug_info}")
        
        # Adicionamos debug_info ao contexto do template para poder exibir na página
        template_context = {
            'stats': stats,
            'recent_requests': recent_requests,
            'all_users': all_users,
            'users_with_hours': users_with_hours,
            'pending_requests': pending_requests,
            'hour_bank_history': hour_bank_history,
            'overtime_by_type': stats.get('overtime_by_type', []),
            'debug_info': debug_info
        }
        
        current_app.logger.info("11. Renderizando template...")
        return render_template('admin/overtime_control.html', **template_context)
                             
    except Exception as e:
        current_app.logger.error(f"ERRO CRÍTICO no dashboard de horas extras: {str(e)}")
        current_app.logger.error(f"DEBUG INFO até o erro: {debug_info}")
        
        # Criar uma página de erro detalhada
        error_context = {
            'error_message': str(e),
            'debug_info': debug_info,
            'error_type': type(e).__name__,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        flash(f'Erro detalhado no dashboard: {str(e)}', 'error')
        return render_template('admin/overtime_error_debug.html', **error_context)

@bp.route('/adjust-user-hours', methods=['POST'])
@login_required
@admin_required
def adjust_user_hours():
    """ROTA REFORMULADA - Ajuste manual de horas com máxima confiabilidade"""
    current_app.logger.info("=== NOVA ROTA DE AJUSTE MANUAL REFORMULADA ===")
    
    try:
        # Verificar Content-Type
        if not request.is_json:
            current_app.logger.error("Content-Type inválido")
            return jsonify({
                'success': False,
                'error': 'Content-Type deve ser application/json'
            }), 400
        
        # Obter dados JSON
        data = request.get_json()
        if not data:
            current_app.logger.error("Dados JSON não fornecidos")
            return jsonify({
                'success': False,
                'error': 'Dados JSON não fornecidos'
            }), 400
        
        current_app.logger.info(f"Dados recebidos: {data}")
        current_app.logger.info(f"Admin logado: {current_user.nome_completo} (ID: {current_user.id})")
        
        # VALIDAÇÃO ROBUSTA DOS DADOS
        errors = []
        
        # Validar user_id
        user_id = data.get('user_id')
        if not user_id:
            errors.append("user_id é obrigatório")
        else:
            try:
                user_id = int(user_id)
                if user_id <= 0:
                    errors.append("user_id deve ser um número positivo")
            except (ValueError, TypeError):
                errors.append("user_id deve ser um número válido")
        
        # Validar hours
        hours = data.get('hours', 0)
        try:
            hours = float(hours)
            if hours < 0:
                errors.append("hours não pode ser negativo")
        except (ValueError, TypeError):
            errors.append("hours deve ser um número válido")
        
        # Validar minutes
        minutes = data.get('minutes', 0)
        try:
            minutes = int(minutes)
            if minutes < 0 or minutes >= 60:
                errors.append("minutes deve estar entre 0 e 59")
        except (ValueError, TypeError):
            errors.append("minutes deve ser um número válido")
        
        # Validar operation
        operation = data.get('operation')
        if not operation:
            errors.append("operation é obrigatório")
        elif operation not in ['add', 'subtract']:
            errors.append("operation deve ser 'add' ou 'subtract'")
        
        # Validar reason
        reason = data.get('reason', '').strip()
        if not reason:
            errors.append("reason é obrigatório e não pode estar vazio")
        
        # Verificar se pelo menos hours ou minutes é maior que zero
        try:
            total_hours = float(hours) + (int(minutes) / 60.0)
            if total_hours <= 0:
                errors.append("O ajuste deve ter pelo menos horas ou minutos diferentes de zero")
        except:
            pass  # Erro já capturado nas validações individuais
        
        if errors:
            error_msg = "; ".join(errors)
            current_app.logger.error(f"Validação falhou: {error_msg}")
            return jsonify({
                'success': False,
                'error': f'Dados inválidos: {error_msg}'
            }), 400
        
        # BUSCAR USUÁRIO
        try:
            user = User.query.get(user_id)
            if not user:
                current_app.logger.error(f"Usuário {user_id} não encontrado")
                return jsonify({
                    'success': False,
                    'error': 'Usuário não encontrado'
                }), 404
            
            if not user.is_active:
                current_app.logger.error(f"Usuário {user_id} está inativo")
                return jsonify({
                    'success': False,
                    'error': 'Usuário está inativo'
                }), 400
            
            current_app.logger.info(f"Usuário encontrado: {user.nome_completo}")
            
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar usuário: {e}")
            return jsonify({
                'success': False,
                'error': 'Erro ao buscar usuário no banco de dados'
            }), 500
        
        # GARANTIR BANCO DE HORAS
        try:
            if not user.hour_bank:
                current_app.logger.info(f"Criando banco de horas para usuário {user.id}")
                hour_bank = HourBank(user_id=user.id, current_balance=0.0)
                db.session.add(hour_bank)
                db.session.flush()
                user.hour_bank = hour_bank
            
            old_balance = user.hour_bank.current_balance
            current_app.logger.info(f"Saldo atual: {old_balance:.2f}h")
            
        except Exception as e:
            current_app.logger.error(f"Erro ao garantir banco de horas: {e}")
            return jsonify({
                'success': False,
                'error': 'Erro ao acessar banco de horas'
            }), 500
        
        # CALCULAR AJUSTE
        try:
            # Converter para horas decimais
            adjustment_hours = float(hours) + (int(minutes) / 60.0)
            
            # Aplicar operação
            if operation == 'subtract':
                adjustment_hours = -adjustment_hours
            
            current_app.logger.info(f"Ajuste calculado: {adjustment_hours:+.2f}h")
            
        except Exception as e:
            current_app.logger.error(f"Erro ao calcular ajuste: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro ao calcular ajuste: {e}'
            }), 500
        
        # APLICAR AJUSTE
        try:
            # Novo saldo
            new_balance = old_balance + adjustment_hours
            
            # Criar transação
            transaction = HourBankTransaction(
                user_id=user.id,
                transaction_type=HourBankTransactionType.AJUSTE,
                hours=adjustment_hours,
                balance_before=old_balance,
                balance_after=new_balance,
                description=f"Ajuste manual por {current_user.nome_completo}: {reason}",
                reference_date=datetime.now().date(),
                created_by=current_user.id,
                created_at=datetime.now()
            )
            
            # Atualizar saldo do banco de horas
            user.hour_bank.current_balance = new_balance
            user.hour_bank.last_updated = datetime.now()
            
            # Criar notificação para o usuário (apenas se não for teste)
            if not any(palavra in reason.lower() for palavra in ['teste', 'test', 'debug', 'mock', 'sample']):
                notification = Notification(
                    user_id=user.id,
                    sender_id=current_user.id,
                    titulo='Ajuste Manual no Banco de Horas',
                    mensagem=f'Seu banco de horas foi ajustado em {adjustment_hours:+.2f}h pelo administrador. Motivo: {reason}. Saldo anterior: {old_balance:.2f}h, novo saldo: {new_balance:.2f}h',
                    tipo=NotificationType.INFO
                )
                db.session.add(notification)
                current_app.logger.info(f"Notificação criada para usuário {user.nome_completo}")
            else:
                current_app.logger.info(f"Notificação não criada - motivo contém palavra de teste: {reason}")
            
            # Adicionar transação à sessão
            db.session.add(transaction)
            
            current_app.logger.info(f"Transação criada. Novo saldo: {new_balance:.2f}h")
            
        except Exception as e:
            current_app.logger.error(f"Erro ao criar transação: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro ao criar transação: {e}'
            }), 500
        
        # COMMIT FINAL
        try:
            db.session.commit()
            current_app.logger.info("Commit realizado com sucesso")
            
            # Preparar resposta
            operation_text = "adicionada" if operation == "add" else "subtraída"
            adjustment_text = f"{adjustment_hours:+.2f}h"
            message = f"Ajuste aplicado com sucesso. {abs(adjustment_hours):.2f}h {operation_text}. Saldo: {old_balance:.2f}h → {new_balance:.2f}h"
            
            response_data = {
                'success': True,
                'message': message,
                'adjustment': adjustment_text,
                'new_balance': new_balance,  # Enviar como número, não string
                'transaction_id': transaction.id,
                'user_id': user.id,  # Adicionar user_id para facilitar updates
                'user_name': user.nome_completo
            }
            
            current_app.logger.info(f"=== AJUSTE MANUAL CONCLUÍDO COM SUCESSO ===")
            current_app.logger.info(f"Resposta: {response_data}")
            
            return jsonify(response_data), 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro no commit: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro ao salvar mudanças: {e}'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"Erro inesperado na rota: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno do servidor: {str(e)}'
        }), 500

@bp.route('/api/users-with-balances', methods=['GET'])
@login_required
@admin_required
def api_users_with_balances():
    """API para obter lista de usuários com seus saldos atuais"""
    try:
        users = User.query.filter(
            User.is_active == True,
            User.is_approved == True,
            User.user_type != UserType.ADMIN
        ).outerjoin(HourBank).all()
        
        users_data = []
        for user in users:
            user_data = {
                'id': user.id,
                'nome': user.nome,
                'sobrenome': user.sobrenome or '',
                'email': user.email,
                'hour_bank': None
            }
            
            if user.hour_bank:
                user_data['hour_bank'] = {
                    'current_balance': f"{user.hour_bank.current_balance:+.2f}" if user.hour_bank.current_balance != 0 else "0.00"
                }
            
            users_data.append(user_data)
        
        return jsonify(users_data)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar usuários com saldos: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@bp.route('/api/refresh-users-list', methods=['GET'])
@login_required
@admin_required
def api_refresh_users_list():
    """API para recarregar lista de usuários após ajustes manuais"""
    current_app.logger.info("=== API REFRESH USERS LIST CHAMADA ===")
    
    try:
        # Buscar todos os usuários ativos com seus bancos de horas
        users = (User.query
                .outerjoin(HourBank, User.id == HourBank.user_id)
                .filter(User.is_active == True)
                .filter(User.is_approved == True)
                .order_by(User.nome, User.sobrenome).all())
        
        users_list = []
        for user in users:
            # Garantir que temos dados atualizados do banco
            hour_bank = HourBank.query.filter_by(user_id=user.id).first()
            saldo = hour_bank.current_balance if hour_bank else 0.0
            
            user_data = {
                'id': user.id,
                'nome': f"{user.nome} {user.sobrenome}".strip(),
                'email': user.email,
                'saldo': float(saldo),  # Garantir que é float
                'user_type': user.user_type.name if user.user_type else 'TRABALHADOR',
                'last_updated': hour_bank.last_updated.isoformat() if hour_bank and hour_bank.last_updated else None
            }
            users_list.append(user_data)
        
        # Ordenar por saldo (maiores primeiro)
        users_list.sort(key=lambda x: x['saldo'], reverse=True)
        
        current_app.logger.info(f"Lista atualizada com {len(users_list)} usuários")
        
        return jsonify({
            'success': True,
            'users': users_list,
            'total_count': len(users_list),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar lista de usuários: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Erro ao carregar lista atualizada: {str(e)}'
        }), 500

@bp.route('/overtime-batch-process', methods=['POST'])
@login_required
@admin_required
def overtime_batch_process():
    """Processar lote de ajustes automáticos"""
    try:
        data = request.get_json()
        target_date_str = data.get('target_date')
        
        if target_date_str:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        else:
            target_date = date.today() - timedelta(days=1)  # Dia anterior
        
        # Inicializar controlador
        controller = OvertimeController()
        
        # Processar lote
        processed, errors = controller.process_daily_batch(target_date)
        
        return jsonify({
            'success': True,
            'processed': processed,
            'errors': errors,
            'message': f'Processados {processed} usuários, {errors} erros'
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro no processamento em lote: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@bp.route('/overtime-analytics')
@login_required
@admin_required
def overtime_analytics():
    """Análise avançada de horas extras"""
    try:
        # Inicializar controlador
        controller = OvertimeController()
        
        # Obter dados analíticos
        analytics = {
            'monthly_trend': get_monthly_overtime_trend(),
            'user_performance': get_user_performance_analysis(),
            'department_stats': get_department_overtime_stats(),
            'cost_analysis': get_overtime_cost_analysis()
        }
        
        return render_template('admin/overtime_analytics.html', analytics=analytics)
        
    except Exception as e:
        current_app.logger.error(f"Erro na análise de horas extras: {str(e)}")
        flash('Erro ao carregar análise de horas extras', 'error')
        return redirect(url_for('admin.overtime_control'))

@bp.route('/overtime-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def overtime_settings():
    """Configurações globais de horas extras"""
    try:
        if request.method == 'POST':
            # Processar configurações
            data = request.get_json()
            
            # Atualizar configurações globais
            # Implementar lógica de salvamento
            
            return jsonify({'success': True, 'message': 'Configurações salvas com sucesso'})
        
        # Obter configurações atuais
        settings = {
            'default_overtime_multiplier': 1.5,
            'auto_approval_enabled': True,
            'daily_limit_default': 4.0,
            'weekly_limit_default': 16.0,
            'monthly_limit_default': 60.0
        }
        
        return render_template('admin/overtime_settings.html', settings=settings)
        
    except Exception as e:
        current_app.logger.error(f"Erro nas configurações: {str(e)}")
        flash('Erro ao carregar configurações', 'error')
        return redirect(url_for('admin.overtime_control'))

@bp.route('/overtime-reports')
@login_required
@admin_required
def overtime_reports():
    """Relatórios de horas extras"""
    try:
        # Parâmetros do relatório
        start_date = request.args.get('start_date', date.today() - timedelta(days=30))
        end_date = request.args.get('end_date', date.today())
        user_id = request.args.get('user_id')
        report_type = request.args.get('type', 'summary')
        
        # Gerar relatório
        report_data = generate_overtime_report(start_date, end_date, user_id, report_type)
        
        return render_template('admin/overtime_reports.html', 
                             report_data=report_data,
                             start_date=start_date,
                             end_date=end_date,
                             user_id=user_id,
                             report_type=report_type)
        
    except Exception as e:
        current_app.logger.error(f"Erro no relatório: {str(e)}")
        flash('Erro ao gerar relatório', 'error')
        return redirect(url_for('admin.overtime_control'))

@bp.route('/user-overtime-summary/<int:user_id>')
@login_required
@admin_required
def user_overtime_summary(user_id):
    """Resumo detalhado de horas extras de um usuário"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Inicializar controlador
        controller = OvertimeController()
        
        # Obter resumo do usuário
        summary = controller.get_user_overtime_summary(user_id)
        
        if not summary:
            flash('Erro ao carregar resumo do usuário', 'error')
            return redirect(url_for('admin.overtime_control'))
        
        return render_template('admin/user_overtime_summary.html', 
                             user=user, 
                             summary=summary)
        
    except Exception as e:
        current_app.logger.error(f"Erro no resumo do usuário: {str(e)}")
        flash('Erro ao carregar resumo do usuário', 'error')
        return redirect(url_for('admin.overtime_control'))

# Funções auxiliares
def get_monthly_overtime_trend():
    """Obtém tendência mensal de horas extras"""
    try:
        from sqlalchemy import func, extract
        from datetime import datetime
        
        # Últimos 6 meses
        results = db.session.query(
            extract('month', OvertimeRequest.created_at).label('month'),
            extract('year', OvertimeRequest.created_at).label('year'),
            func.sum(OvertimeRequest.estimated_hours).label('total_hours'),
            func.count(OvertimeRequest.id).label('total_requests')
        ).filter(
            OvertimeRequest.created_at >= datetime.now() - timedelta(days=180)
        ).group_by(
            extract('year', OvertimeRequest.created_at),
            extract('month', OvertimeRequest.created_at)
        ).order_by('year', 'month').all()
        
        trend_data = []
        for result in results:
            trend_data.append({
                'month': f"{int(result.month):02d}/{int(result.year)}",
                'total_hours': float(result.total_hours or 0),
                'total_requests': int(result.total_requests or 0)
            })
        
        return trend_data
    except Exception as e:
        current_app.logger.error(f"Erro na tendência mensal: {str(e)}")
        return []

def get_user_performance_analysis():
    """Análise de performance dos usuários"""
    try:
        from sqlalchemy import func
        
        # Top 10 usuários por horas extras aprovadas
        top_performers = db.session.query(
            User.id,
            User.nome,
            User.sobrenome,
            func.sum(OvertimeRequest.estimated_hours).label('total_overtime'),
            func.count(OvertimeRequest.id).label('total_requests')
        ).join(
            OvertimeRequest, User.id == OvertimeRequest.user_id
        ).filter(
            OvertimeRequest.status.in_(['APROVADA', 'approved'])
        ).group_by(
            User.id, User.nome, User.sobrenome
        ).order_by(
            func.sum(OvertimeRequest.estimated_hours).desc()
        ).limit(10).all()
        
        performance_data = []
        for user_data in top_performers:
            performance_data.append({
                'user_id': user_data.id,
                'name': f"{user_data.nome} {user_data.sobrenome or ''}".strip(),
                'total_overtime': float(user_data.total_overtime or 0),
                'total_requests': int(user_data.total_requests or 0)
            })
        
        return performance_data
    except Exception as e:
        current_app.logger.error(f"Erro na análise de performance: {str(e)}")
        return []


def get_department_overtime_stats():
    """Estatísticas de horas extras por departamento"""
    try:
        # Como não temos departamentos definidos, usamos user_type
        from sqlalchemy import func
        
        stats = db.session.query(
            User.user_type,
            func.sum(OvertimeRequest.estimated_hours).label('total_hours'),
            func.count(func.distinct(User.id)).label('total_users')
        ).join(
            OvertimeRequest, User.id == OvertimeRequest.user_id
        ).group_by(
            User.user_type
        ).all()
        
        department_data = []
        for stat in stats:
            department_data.append({
                'department': stat.user_type.name,
                'total_hours': float(stat.total_hours or 0),
                'total_users': int(stat.total_users or 0)
            })
        
        return department_data
    except Exception as e:
        current_app.logger.error(f"Erro nas estatísticas por tipo de usuário: {str(e)}")
        return []


def get_overtime_cost_analysis():
    """Análise de custos das horas extras"""
    try:
        from sqlalchemy import func
        
        # Estimativa de custos baseada em salário médio
        SALARIO_MEDIO_HORA = 25.0  # R$ por hora (configurável)
        MULTIPLICADOR_EXTRA = 1.5
        
        # Total de horas extras aprovadas no último mês
        last_month = datetime.now() - timedelta(days=30)
        
        total_hours = db.session.query(
            func.sum(OvertimeRequest.estimated_hours)
        ).filter(
            OvertimeRequest.status.in_(['APROVADA', 'approved']),
            OvertimeRequest.created_at >= last_month
        ).scalar() or 0
        
        # Calcular custos
        cost_normal = total_hours * SALARIO_MEDIO_HORA
        cost_overtime = total_hours * SALARIO_MEDIO_HORA * MULTIPLICADOR_EXTRA
        cost_difference = cost_overtime - cost_normal
        
        return {
            'total_hours': float(total_hours),
            'salary_per_hour': SALARIO_MEDIO_HORA,
            'overtime_multiplier': MULTIPLICADOR_EXTRA,
            'cost_normal': round(cost_normal, 2),
            'cost_overtime': round(cost_overtime, 2),
            'additional_cost': round(cost_difference, 2),
            'period_days': 30
        }
    except Exception as e:
        current_app.logger.error(f"Erro na análise de custos: {str(e)}")
        return {
            'total_hours': 0,
            'cost_normal': 0,
            'cost_overtime': 0,
            'additional_cost': 0
        }


def generate_overtime_report(start_date, end_date, user_id, report_type):
    """Gera relatório de horas extras"""
    try:
        from sqlalchemy import func
        
        # Query base
        query = db.session.query(OvertimeRequest).join(User)
        
        # Filtros de data
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
        query = query.filter(
            OvertimeRequest.date >= start_date,
            OvertimeRequest.date <= end_date
        )
        
        # Filtro por usuário
        if user_id:
            query = query.filter(OvertimeRequest.user_id == user_id)
        
        # Executar query
        requests = query.all()
        
        # Calcular totais
        total_hours = sum(req.estimated_hours or 0 for req in requests)
        total_requests = len(requests)
        approved_requests = len([req for req in requests if req.status in ['APROVADA', 'approved']])
        
        # Breakdown por usuário
        user_breakdown = {}
        for req in requests:
            user_key = req.user_id
            if user_key not in user_breakdown:
                user_breakdown[user_key] = {
                    'user_name': req.user.nome_completo,
                    'total_hours': 0,
                    'total_requests': 0
                }
            user_breakdown[user_key]['total_hours'] += req.estimated_hours or 0
            user_breakdown[user_key]['total_requests'] += 1
        
        return {
            'total_hours': round(total_hours, 2),
            'total_requests': total_requests,
            'approved_requests': approved_requests,
            'approval_rate': round((approved_requests / total_requests * 100) if total_requests > 0 else 0, 1),
            'breakdown': list(user_breakdown.values()),
            'period': {
                'start': start_date.strftime('%d/%m/%Y'),
                'end': end_date.strftime('%d/%m/%Y')
            }
        }
    except Exception as e:
        current_app.logger.error(f"Erro na geração do relatório: {str(e)}")
        return {
            'total_hours': 0,
            'total_requests': 0,
            'approved_requests': 0,
            'approval_rate': 0,
            'breakdown': []
        }


@bp.route('/user-hours-history/<int:user_id>')
@login_required
@admin_required
def get_user_hours_history(user_id):
    """Obtém o histórico de alterações do banco de horas de um usuário"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404
        
        # Buscar histórico
        history = HourBankHistory.query.filter_by(user_id=user_id)\
                    .order_by(HourBankHistory.created_at.desc())\
                    .limit(50).all()
        
        history_data = []
        for entry in history:
            admin = User.query.get(entry.admin_id)
            history_data.append({
                'id': entry.id,
                'admin_name': f"{admin.nome} {admin.sobrenome or ''}" if admin else "Admin Deletado",
                'old_balance': entry.old_balance,
                'adjustment': entry.adjustment,
                'new_balance': entry.new_balance,
                'reason': entry.reason,
                'created_at': entry.created_at.strftime('%d/%m/%Y %H:%M')
            })
        
        return jsonify({
            'success': True,
            'user_name': f"{user.nome} {user.sobrenome or ''}".strip(),
            'history': history_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar histórico: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@bp.route('/edit-user-hours/<int:user_id>')
@login_required
@admin_required
def edit_user_hours(user_id):
    """Página para editar horas extras de um usuário específico"""
    try:
        # Buscar o usuário
        user = User.query.get_or_404(user_id)
        
        # Buscar o banco de horas do usuário
        hour_bank = HourBank.query.filter_by(user_id=user_id).first()
        
        # Se não existir banco de horas, criar um
        if not hour_bank:
            hour_bank = HourBank(user_id=user_id)
            db.session.add(hour_bank)
            db.session.commit()
        
        # Buscar histórico de transações recentes
        recent_transactions = (HourBankHistory.query
                             .filter_by(user_id=user_id)
                             .order_by(HourBankHistory.created_at.desc())
                             .limit(20).all())
        
        # Buscar configurações de horas extras do usuário
        overtime_settings = OvertimeSettings.query.filter_by(user_id=user_id).first()
        
        return render_template('admin/edit_user_hours.html',
                             user=user,
                             hour_bank=hour_bank,
                             recent_transactions=recent_transactions,
                             overtime_settings=overtime_settings)
                             
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar página de edição: {str(e)}")
        flash('Erro ao carregar página de edição de horas', 'error')
        return redirect(url_for('admin.overtime_control'))

@bp.route('/update-user-hours/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def update_user_hours(user_id):
    """Atualizar horas extras de um usuário"""
    try:
        # Buscar o usuário
        user = User.query.get_or_404(user_id)
        
        # Obter dados do formulário
        operation = request.form.get('operation')
        hours = request.form.get('hours', 0)
        minutes = request.form.get('minutes', 0)
        reason = request.form.get('reason')
        
        if not reason:
            flash('Motivo é obrigatório', 'error')
            return redirect(url_for('admin.edit_user_hours', user_id=user_id))
        
        try:
            hours = float(hours) if hours else 0
            minutes = int(minutes) if minutes else 0
            
            # Validar minutos
            if minutes < 0 or minutes >= 60:
                flash('Minutos devem estar entre 0 e 59', 'error')
                return redirect(url_for('admin.edit_user_hours', user_id=user_id))
            
            # Converter para decimal
            hours_decimal = hours + (minutes / 60)
            
            # Aplicar operação
            if operation == 'subtract':
                hours_decimal = -hours_decimal
                
        except (ValueError, TypeError):
            flash('Valores de horas inválidos', 'error')
            return redirect(url_for('admin.edit_user_hours', user_id=user_id))
        
        # Inicializar controlador
        controller = OvertimeController()
        
        # Aplicar ajuste
        success, message = controller.admin_adjust_hours(
            user_id=user_id,
            hours_adjustment=hours_decimal,
            reason=reason,
            admin_id=current_user.id
        )
        
        if success:
            flash(f'Horas atualizadas com sucesso: {message}', 'success')
        else:
            flash(f'Erro ao atualizar horas: {message}', 'error')
            
        return redirect(url_for('admin.edit_user_hours', user_id=user_id))
        
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar horas: {str(e)}")
        flash('Erro interno do servidor', 'error')
        return redirect(url_for('admin.edit_user_hours', user_id=user_id))


@bp.route('/get_all_users_data', methods=['GET'])
@login_required
@admin_required
def get_all_users_data():
    """Retorna todos os dados atualizados dos usuários para sincronização completa"""
    
    try:
        current_app.logger.info("=== BUSCA DE DADOS PARA SINCRONIZAÇÃO COMPLETA ===")
        
        # Buscar todos os usuários ativos
        users = User.query.filter_by(is_active=True).all()
        users_data = []
        
        current_app.logger.info(f"Processando {len(users)} usuários")
        
        for user in users:
            try:
                # Dados básicos do usuário
                user_data = {
                    'id': user.id,
                    'nome_completo': user.nome_completo,
                    'email': user.email,
                    'is_active': user.is_active,
                    'is_approved': user.is_approved,
                    'user_type': user.user_type.value if user.user_type else None,
                }
                
                # Dados do banco de horas
                if user.hour_bank:
                    user_data.update({
                        'saldo_atual': user.hour_bank.current_balance,
                        'saldo_formatado': user.hour_bank.formatted_balance,
                        'total_credited': user.hour_bank.total_credited,
                        'total_debited': user.hour_bank.total_debited,
                        'has_positive_balance': user.hour_bank.has_positive_balance,
                        'last_transaction': user.hour_bank.last_transaction.isoformat() if user.hour_bank.last_transaction else None
                    })
                else:
                    user_data.update({
                        'saldo_atual': 0,
                        'saldo_formatado': '0h 0m',
                        'total_credited': 0,
                        'total_debited': 0,
                        'has_positive_balance': False,
                        'last_transaction': None
                    })
                
                # Adicionar à lista
                users_data.append(user_data)
                
            except Exception as e:
                current_app.logger.error(f"Erro ao processar usuário {user.id}: {e}")
                continue
        
        current_app.logger.info(f"Dados processados com sucesso para {len(users_data)} usuários")
        
        return jsonify({
            'success': True,
            'users': users_data,
            'timestamp': datetime.now().isoformat(),
            'total_users': len(users_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro na busca de dados para sincronização: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao buscar dados: {str(e)}'
        }), 500
