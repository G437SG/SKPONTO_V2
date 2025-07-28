#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard de monitoramento de erros do SKPONTO
"""

import os
import json
import glob
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from app.decorators import admin_required

# Blueprint para dashboard de erros
error_dashboard = Blueprint('error_dashboard', __name__, url_prefix='/admin/errors')

@error_dashboard.route('/')
@login_required
@admin_required
def dashboard():
    """Dashboard principal de erros"""
    
    try:
        # Obter estatísticas de erros
        error_stats = get_error_statistics()
        recent_errors = get_recent_errors(limit=10)
        error_trends = get_error_trends()
        
        return render_template('admin/error_dashboard.html',
                             error_stats=error_stats,
                             recent_errors=recent_errors,
                             error_trends=error_trends)
    except Exception as e:
        current_app.logger.error(f"Erro no dashboard de erros: {str(e)}")
        return "Erro ao carregar dashboard", 500

@error_dashboard.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """API para estatísticas de erros"""
    
    try:
        stats = get_error_statistics()
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f"Erro na API de estatísticas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@error_dashboard.route('/api/recent/<int:hours>')
@login_required
@admin_required
def api_recent_errors(hours=24):
    """API para erros recentes"""
    
    try:
        errors = get_recent_errors(hours=hours)
        return jsonify(errors)
    except Exception as e:
        current_app.logger.error(f"Erro na API de erros recentes: {str(e)}")
        return jsonify({'error': str(e)}), 500

@error_dashboard.route('/api/clear-logs')
@login_required
@admin_required
def clear_logs():
    """Limpa logs antigos"""
    
    try:
        cleared = clear_old_logs()
        return jsonify({'success': True, 'cleared': cleared})
    except Exception as e:
        current_app.logger.error(f"Erro ao limpar logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_error_statistics():
    """Obtém estatísticas de erros"""
    
    stats = {
        'total_errors': 0,
        'errors_24h': 0,
        'errors_7d': 0,
        'error_types': {},
        'top_errors': [],
        'error_rate': 0
    }
    
    try:
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            return stats
        
        error_log_file = os.path.join(log_dir, 'skponto_errors.log')
        if not os.path.exists(error_log_file):
            return stats
        
        now = datetime.now()
        
        with open(error_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            if 'ERROR' in line:
                stats['total_errors'] += 1
                
                # Extrair timestamp
                try:
                    timestamp_str = line.split(' - ')[0]
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    
                    # Contar erros recentes
                    if now - timestamp <= timedelta(hours=24):
                        stats['errors_24h'] += 1
                    
                    if now - timestamp <= timedelta(days=7):
                        stats['errors_7d'] += 1
                    
                    # Contar tipos de erro
                    if 'KeyError' in line:
                        stats['error_types']['KeyError'] = stats['error_types'].get('KeyError', 0) + 1
                    elif 'ValueError' in line:
                        stats['error_types']['ValueError'] = stats['error_types'].get('ValueError', 0) + 1
                    elif 'AttributeError' in line:
                        stats['error_types']['AttributeError'] = stats['error_types'].get('AttributeError', 0) + 1
                    elif 'TypeError' in line:
                        stats['error_types']['TypeError'] = stats['error_types'].get('TypeError', 0) + 1
                    else:
                        stats['error_types']['Other'] = stats['error_types'].get('Other', 0) + 1
                        
                except Exception:
                    continue
        
        # Calcular taxa de erro (erros por hora nas últimas 24h)
        if stats['errors_24h'] > 0:
            stats['error_rate'] = round(stats['errors_24h'] / 24, 2)
        
        # Top erros
        stats['top_errors'] = sorted(stats['error_types'].items(), key=lambda x: x[1], reverse=True)[:5]
        
    except Exception as e:
        current_app.logger.error(f"Erro ao calcular estatísticas: {str(e)}")
    
    return stats

def get_recent_errors(limit=50, hours=24):
    """Obtém erros recentes"""
    
    errors = []
    
    try:
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            return errors
        
        error_log_file = os.path.join(log_dir, 'skponto_errors.log')
        if not os.path.exists(error_log_file):
            return errors
        
        now = datetime.now()
        cutoff_time = now - timedelta(hours=hours)
        
        with open(error_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_error = None
        
        for line in lines:
            if 'ERROR' in line and '===' in line:
                # Início de um novo erro
                if current_error and len(errors) < limit:
                    errors.append(current_error)
                
                try:
                    timestamp_str = line.split(' - ')[0]
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    
                    if timestamp >= cutoff_time:
                        current_error = {
                            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'content': line.strip(),
                            'details': []
                        }
                    else:
                        current_error = None
                        
                except Exception:
                    current_error = None
                    
            elif current_error and line.strip():
                current_error['details'].append(line.strip())
        
        # Adicionar último erro se existir
        if current_error and len(errors) < limit:
            errors.append(current_error)
        
        # Ordenar por timestamp (mais recente primeiro)
        errors.reverse()
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter erros recentes: {str(e)}")
    
    return errors

def get_error_trends():
    """Obtém tendências de erros por hora"""
    
    trends = {}
    
    try:
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            return trends
        
        error_log_file = os.path.join(log_dir, 'skponto_errors.log')
        if not os.path.exists(error_log_file):
            return trends
        
        now = datetime.now()
        
        # Inicializar últimas 24 horas
        for i in range(24):
            hour = (now - timedelta(hours=i)).strftime('%Y-%m-%d %H:00')
            trends[hour] = 0
        
        with open(error_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            if 'ERROR' in line:
                try:
                    timestamp_str = line.split(' - ')[0]
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    
                    # Agrupar por hora
                    hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                    
                    if hour_key in trends:
                        trends[hour_key] += 1
                        
                except Exception:
                    continue
        
        # Converter para lista ordenada
        sorted_trends = []
        for hour in sorted(trends.keys()):
            sorted_trends.append({
                'hour': hour,
                'count': trends[hour]
            })
        
        return sorted_trends
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter tendências: {str(e)}")
    
    return []

def clear_old_logs(days=30):
    """Limpa logs antigos"""
    
    cleared = 0
    
    try:
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            return cleared
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Procurar arquivos de log antigos
        for log_file in glob.glob(os.path.join(log_dir, '*.log.*')):
            try:
                file_stat = os.stat(log_file)
                file_date = datetime.fromtimestamp(file_stat.st_mtime)
                
                if file_date < cutoff_date:
                    os.remove(log_file)
                    cleared += 1
                    
            except Exception as e:
                current_app.logger.error(f"Erro ao remover log {log_file}: {str(e)}")
                continue
        
    except Exception as e:
        current_app.logger.error(f"Erro ao limpar logs: {str(e)}")
    
    return cleared
