#!/usr/bin/env python3
"""
Sistema de Debug Avançado - SKPONTO V2
Captura e exibe erros detalhados em tempo real
"""

import logging
import traceback
import sys
from datetime import datetime
from functools import wraps
from flask import request, jsonify, current_app, g
import json
import os

class DebugLogger:
    """Logger especializado para debug de erros"""
    
    def __init__(self):
        self.setup_logger()
        self.errors = []  # Cache em memória dos últimos erros
        self.max_errors = 100  # Máximo de erros em cache
    
    def setup_logger(self):
        """Configura o logger de debug"""
        self.logger = logging.getLogger('skponto_debug')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove handlers existentes
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Handler para arquivo
        file_handler = logging.FileHandler('storage/logs/debug_errors.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)
        
        # Formatter detalhado
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_error(self, error, context=None):
        """Log detalhado de erro"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'request_info': self._get_request_info() if request else None
        }
        
        # Adicionar ao cache
        self.errors.append(error_data)
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)
        
        # Log para arquivo
        self.logger.error(
            f"ERROR: {error_data['error_type']} - {error_data['error_message']}\n"
            f"Context: {json.dumps(error_data['context'], default=str)}\n"
            f"Request: {json.dumps(error_data['request_info'], default=str)}\n"
            f"Traceback:\n{error_data['traceback']}"
        )
        
        return error_data
    
    def _get_request_info(self):
        """Obtém informações da requisição atual"""
        try:
            return {
                'method': request.method,
                'url': request.url,
                'endpoint': request.endpoint,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'headers': dict(request.headers),
                'args': dict(request.args),
                'form': dict(request.form) if request.method == 'POST' else None,
                'json': request.get_json() if request.is_json else None
            }
        except Exception as e:
            return {'error': f'Could not get request info: {str(e)}'}
    
    def get_recent_errors(self, limit=20):
        """Retorna erros recentes"""
        return self.errors[-limit:] if self.errors else []
    
    def clear_errors(self):
        """Limpa o cache de erros"""
        self.errors.clear()

# Instância global do debug logger
debug_logger = DebugLogger()

def debug_route(func):
    """Decorator para debug de rotas"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        route_name = func.__name__
        start_time = datetime.now()
        
        try:
            # Log início da execução
            debug_logger.logger.debug(f"Starting route: {route_name}")
            
            # Executar a função
            result = func(*args, **kwargs)
            
            # Log sucesso
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            debug_logger.logger.debug(f"Route {route_name} completed in {duration:.3f}s")
            
            return result
            
        except Exception as e:
            # Log erro detalhado
            context = {
                'route_name': route_name,
                'args': args,
                'kwargs': kwargs,
                'duration': (datetime.now() - start_time).total_seconds()
            }
            
            error_data = debug_logger.log_error(e, context)
            
            # Retornar erro formatado para desenvolvimento
            if current_app.config.get('DEBUG') or current_app.config.get('TESTING'):
                return jsonify({
                    'error': True,
                    'debug_info': error_data,
                    'message': 'Erro interno do servidor - veja debug_info para detalhes'
                }), 500
            else:
                # Em produção, retornar erro genérico
                return jsonify({
                    'error': True,
                    'message': 'Erro interno do servidor'
                }), 500
    
    return wrapper

def debug_function(func):
    """Decorator para debug de funções"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        function_name = f"{func.__module__}.{func.__name__}"
        
        try:
            debug_logger.logger.debug(f"Executing function: {function_name}")
            result = func(*args, **kwargs)
            debug_logger.logger.debug(f"Function {function_name} completed successfully")
            return result
            
        except Exception as e:
            context = {
                'function_name': function_name,
                'args': [str(arg) for arg in args],
                'kwargs': {k: str(v) for k, v in kwargs.items()}
            }
            
            debug_logger.log_error(e, context)
            raise  # Re-raise para não quebrar o fluxo
    
    return wrapper

class DebugContext:
    """Context manager para debug"""
    
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.now()
        debug_logger.logger.debug(f"Starting operation: {self.operation_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is not None:
            context = {
                'operation_name': self.operation_name,
                'duration': duration
            }
            debug_logger.log_error(exc_val, context)
        else:
            debug_logger.logger.debug(f"Operation {self.operation_name} completed in {duration:.3f}s")

def setup_debug_logging(app):
    """Configura logging de debug para a aplicação"""
    
    # Criar diretório de logs se não existir
    log_dir = os.path.join(app.instance_path, '..', 'storage', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Handler global para erros não tratados
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log do erro
        context = {
            'app_name': app.name,
            'config': app.config.get('ENV', 'unknown')
        }
        
        error_data = debug_logger.log_error(e, context)
        
        # Em desenvolvimento, mostrar detalhes
        if app.config.get('DEBUG') or app.config.get('TESTING'):
            return jsonify({
                'error': True,
                'debug_info': error_data,
                'message': 'Erro interno do servidor - veja debug_info para detalhes'
            }), 500
        
        # Em produção, erro genérico
        return jsonify({
            'error': True,
            'message': 'Erro interno do servidor'
        }), 500
    
    # Before request - log início
    @app.before_request
    def log_request_start():
        g.start_time = datetime.now()
        if app.config.get('DEBUG'):
            debug_logger.logger.debug(f"Request started: {request.method} {request.url}")
    
    # After request - log fim
    @app.after_request
    def log_request_end(response):
        if hasattr(g, 'start_time'):
            duration = (datetime.now() - g.start_time).total_seconds()
            if app.config.get('DEBUG'):
                debug_logger.logger.debug(
                    f"Request completed: {request.method} {request.url} "
                    f"Status: {response.status_code} Duration: {duration:.3f}s"
                )
        return response

# Funções utilitárias para uso direto
def log_debug(message, context=None):
    """Log de debug simples"""
    debug_logger.logger.debug(f"{message} - Context: {context}")

def log_info(message, context=None):
    """Log de informação"""
    debug_logger.logger.info(f"{message} - Context: {context}")

def log_warning(message, context=None):
    """Log de warning"""
    debug_logger.logger.warning(f"{message} - Context: {context}")

def log_error(error, context=None):
    """Log de erro"""
    return debug_logger.log_error(error, context)

def get_debug_stats():
    """Estatísticas de debug"""
    return {
        'total_errors': len(debug_logger.errors),
        'recent_errors': len([e for e in debug_logger.errors 
                             if (datetime.now() - datetime.fromisoformat(e['timestamp'])).seconds < 3600]),
        'error_types': {}
    }
