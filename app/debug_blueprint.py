"""
Blueprint para Dashboard de Debug - SKPONTO V2
Interface web para visualizar erros e logs em tempo real
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from app.models import UserType
from app.decorators import admin_required
from app.debug_system import debug_logger, get_debug_stats
from datetime import datetime, timedelta
import json
import os

# Criar blueprint
bp = Blueprint('debug', __name__, url_prefix='/admin/debug')

@bp.route('/')
@login_required
@admin_required
def debug_dashboard():
    """Dashboard principal de debug"""
    try:
        stats = get_debug_stats()
        recent_errors = debug_logger.get_recent_errors(limit=10)
        
        return render_template('admin/debug/dashboard.html',
                             stats=stats,
                             recent_errors=recent_errors)
    except Exception as e:
        current_app.logger.error(f"Erro no dashboard de debug: {str(e)}")
        return f"Erro interno: {str(e)}", 500

@bp.route('/api/errors')
@login_required
@admin_required
def api_errors():
    """API para obter lista de erros"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        errors = debug_logger.get_recent_errors(limit=limit, offset=offset)
        
        return jsonify({
            'success': True,
            'errors': errors,
            'total': len(debug_logger.errors)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/errors/clear', methods=['POST'])
@login_required
@admin_required
def clear_errors():
    """Limpar todos os erros"""
    try:
        debug_logger.clear_errors()
        current_app.logger.info(f"Erros limpos por {current_user.name}")
        
        return jsonify({'success': True, 'message': 'Erros limpos com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """API para obter estatísticas"""
    try:
        stats = get_debug_stats()
        
        # Estatísticas por hora (últimas 24h)
        hourly_stats = {}
        now = datetime.now()
        for i in range(24):
            hour = (now - timedelta(hours=i)).strftime('%H:00')
            hourly_stats[hour] = 0
        
        # Contar erros por hora
        for error in debug_logger.errors:
            try:
                error_time = datetime.fromisoformat(error['timestamp'].replace('Z', '+00:00'))
                hour_key = error_time.strftime('%H:00')
                if hour_key in hourly_stats:
                    hourly_stats[hour_key] += 1
            except:
                continue
        
        # Tipos de erro
        error_types = {}
        for error in debug_logger.errors:
            error_type = error.get('error_type', 'Unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return jsonify({
            'success': True,
            'total_errors': stats['total_errors'],
            'recent_errors': stats['recent_errors'],
            'error_types': error_types,
            'hourly_stats': hourly_stats,
            'system_status': 'online'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/test-error')
@login_required
@admin_required
def test_error():
    """Gerar erro de teste"""
    try:
        # Gerar erro proposital para teste
        test_exception = Exception("Erro de teste gerado para validar o sistema de debug")
        debug_logger.log_error(
            test_exception,
            context={
                'test': True,
                'user': current_user.name,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        current_app.logger.info(f"Erro de teste gerado por {current_user.name}")
        
        return jsonify({
            'success': True,
            'message': 'Erro de teste gerado com sucesso'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/logs')
@login_required
@admin_required
def debug_logs():
    """Página de logs"""
    return render_template('admin/debug/logs.html')

@bp.route('/api/logs')
@login_required
@admin_required
def api_logs():
    """API para obter logs"""
    try:
        # Parâmetros de filtro
        level = request.args.get('level', '')
        date_from = request.args.get('from', '')
        date_to = request.args.get('to', '')
        search = request.args.get('search', '')
        
        # Ler logs do arquivo
        logs = []
        log_file = debug_logger.log_file
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Aplicar filtros
                        if level and log_entry.get('level', '') != level:
                            continue
                        if search and search.lower() not in log_entry.get('message', '').lower():
                            continue
                        
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        
        # Ordenar por timestamp (mais recente primeiro)
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'logs': logs[:1000]  # Limitar a 1000 entradas
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/realtime')
@login_required
@admin_required
def debug_realtime():
    """Página de monitoramento em tempo real"""
    return render_template('admin/debug/realtime.html')

@bp.route('/api/realtime')
@login_required
@admin_required
def api_realtime():
    """API para dados em tempo real"""
    try:
        # Simular métricas do sistema
        metrics = {
            'cpu_percent': 15.2,
            'memory_percent': 45.8,
            'active_connections': 12,
            'response_time': 85
        }
        
        # Contar erros e requisições recentes (última hora)
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        recent_errors = 0
        recent_requests = 0
        
        for error in debug_logger.errors:
            try:
                error_time = datetime.fromisoformat(error['timestamp'].replace('Z', '+00:00'))
                if error_time > one_hour_ago:
                    recent_errors += 1
            except:
                continue
        
        # Simular contagem de requisições
        recent_requests = recent_errors * 10  # Estimativa
        
        # Eventos recentes
        recent_events = []
        for error in debug_logger.get_recent_errors(limit=5):
            recent_events.append({
                'timestamp': error['timestamp'],
                'level': 'ERROR',
                'message': error['error_message']
            })
        
        return jsonify({
            'success': True,
            'errors_count': recent_errors,
            'requests_count': recent_requests,
            'metrics': metrics,
            'recent_events': recent_events,
            'new_errors': []  # Para notificações
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def init_debug_blueprint(app):
    """Inicializar blueprint de debug"""
    app.register_blueprint(bp)
