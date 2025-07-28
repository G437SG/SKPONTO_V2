from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.api import bp
from app.models import TimeRecord, Notification, User

@bp.route('/status')
def status():
    """Status da API"""
    return jsonify({
        'status': 'online',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })

@bp.route('/registro_ponto', methods=['POST'])
@login_required
def registro_ponto_api():
    """API para registro de ponto"""
    data = request.get_json()
    acao = data.get('acao')
    
    if acao not in ['entrada', 'saida']:
        return jsonify({'error': 'Ação inválida'}), 400
    
    from app.utils import get_current_date, get_current_time
    
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
    
    try:
        if acao == 'entrada':
            if registro.entrada is None:
                registro.entrada = agora
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Entrada registrada com sucesso!',
                    'entrada': agora.strftime('%H:%M'),
                    'data': hoje.isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Entrada já foi registrada hoje.'
                }), 400
        
        elif acao == 'saida':
            if registro.entrada is None:
                return jsonify({
                    'success': False,
                    'message': 'Você deve registrar a entrada primeiro.'
                }), 400
            elif registro.saida is None:
                registro.saida = agora
                registro.calcular_horas()
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Saída registrada com sucesso!',
                    'saida': agora.strftime('%H:%M'),
                    'horas_trabalhadas': registro.horas_trabalhadas,
                    'horas_extras': registro.horas_extras
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Saída já foi registrada hoje.'
                }), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@bp.route('/meus_registros')
@login_required
def meus_registros_api():
    """API para buscar registros do usuário"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    if per_page > 100:
        per_page = 100
    
    registros = TimeRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(TimeRecord.data.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'registros': [{
            'id': r.id,
            'data': r.data.isoformat(),
            'entrada': r.entrada.strftime('%H:%M') if r.entrada else None,
            'saida': r.saida.strftime('%H:%M') if r.saida else None,
            'horas_trabalhadas': r.horas_trabalhadas,
            'horas_extras': r.horas_extras,
            'observacoes': r.observacoes,
            'is_completo': r.is_completo
        } for r in registros.items],
        'pagination': {
            'page': registros.page,
            'pages': registros.pages,
            'per_page': registros.per_page,
            'total': registros.total,
            'has_next': registros.has_next,
            'has_prev': registros.has_prev
        }
    })

@bp.route('/notificacoes')
@login_required
def notificacoes_api():
    """API para buscar notificações do usuário"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    apenas_nao_lidas = request.args.get('apenas_nao_lidas', False, type=bool)
    
    if per_page > 100:
        per_page = 100
    
    query = Notification.query.filter_by(user_id=current_user.id)
    
    if apenas_nao_lidas:
        query = query.filter_by(lida=False)
    
    notificacoes = query.order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'notificacoes': [{
            'id': n.id,
            'titulo': n.titulo,
            'mensagem': n.mensagem,
            'tipo': n.tipo.value,
            'lida': n.lida,
            'created_at': n.created_at.isoformat(),
            'remetente': n.remetente.nome_completo if n.remetente else 'Sistema'
        } for n in notificacoes.items],
        'pagination': {
            'page': notificacoes.page,
            'pages': notificacoes.pages,
            'per_page': notificacoes.per_page,
            'total': notificacoes.total,
            'has_next': notificacoes.has_next,
            'has_prev': notificacoes.has_prev
        }
    })

@bp.route('/marcar_notificacao_lida/<int:id>', methods=['POST'])
@login_required
def marcar_notificacao_lida_api(id):
    """API para marcar notificação como lida"""
    notificacao = Notification.query.get_or_404(id)
    
    if notificacao.user_id != current_user.id:
        return jsonify({'error': 'Acesso negado'}), 403
    
    notificacao.lida = True
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Notificação marcada como lida'
    })

@bp.route('/estatisticas')
@login_required
def estatisticas_api():
    """API para estatísticas do usuário"""
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    
    # Buscar registros do mês
    registros_mes = TimeRecord.query.filter(
        TimeRecord.user_id == current_user.id,
        TimeRecord.data >= inicio_mes,
        TimeRecord.data <= hoje
    ).all()
    
    # Calcular estatísticas
    total_horas = sum(r.horas_trabalhadas for r in registros_mes)
    total_extras = sum(r.horas_extras for r in registros_mes)
    dias_trabalhados = len([r for r in registros_mes if r.is_completo])
    
    # Registro de hoje
    registro_hoje = TimeRecord.query.filter_by(
        user_id=current_user.id,
        data=hoje
    ).first()
    
    return jsonify({
        'mes_atual': {
            'total_horas': total_horas,
            'total_extras': total_extras,
            'dias_trabalhados': dias_trabalhados,
            'mes': hoje.month,
            'ano': hoje.year
        },
        'hoje': {
            'data': hoje.isoformat(),
            'entrada': registro_hoje.entrada.strftime('%H:%M') if registro_hoje and registro_hoje.entrada else None,
            'saida': registro_hoje.saida.strftime('%H:%M') if registro_hoje and registro_hoje.saida else None,
            'horas_trabalhadas': registro_hoje.horas_trabalhadas if registro_hoje else 0,
            'is_completo': registro_hoje.is_completo if registro_hoje else False
        },
        'notificacoes_nao_lidas': Notification.query.filter_by(
            user_id=current_user.id,
            lida=False
        ).count()
    })

@bp.route('/usuarios', methods=['GET'])
@login_required
def usuarios_api():
    """API para buscar usuários (apenas para admins)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Acesso negado'}), 403
    
    search = request.args.get('search', '')
    
    query = User.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                User.nome.contains(search),
                User.sobrenome.contains(search),
                User.email.contains(search)
            )
        )
    
    usuarios = query.order_by(User.nome, User.sobrenome).limit(50).all()
    
    return jsonify({
        'usuarios': [{
            'id': u.id,
            'nome_completo': u.nome_completo,
            'email': u.email,
            'user_type': u.user_type.value,
            'last_login': u.last_login.isoformat() if u.last_login else None
        } for u in usuarios]
    })

@bp.errorhandler(404)
def api_not_found(error):
    """Erro 404 para API"""
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@bp.errorhandler(500)
def api_internal_error(error):
    """Erro 500 para API"""
    return jsonify({'error': 'Erro interno do servidor'}), 500
