#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de tratamento de erros avançado para SKPONTO
Configuração completa de logging e debugging
"""

import os
import sys
import logging
import traceback
import functools
from typing import Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, render_template

class AdvancedErrorHandler:
    """Classe para tratamento avançado de erros"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Inicializa o sistema de erros na aplicação"""
        self.app = app
        self.setup_logging()
        self.setup_error_handlers()
        self.setup_exception_tracking()
    
    def setup_logging(self):
        """Configura logging avançado"""
        if not self.app:
            return
            
        # Criar diretório de logs
        os.makedirs('logs', exist_ok=True)
        
        # Configurar formatação detalhada
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
        )
        
        # Handler para arquivo com rotação
        file_handler = RotatingFileHandler(
            'logs/skponto_errors.log', 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.ERROR)
        
        # Handler para debug
        debug_handler = RotatingFileHandler(
            'logs/skponto_debug.log', 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3
        )
        debug_handler.setFormatter(detailed_formatter)
        debug_handler.setLevel(logging.DEBUG)
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(detailed_formatter)
        console_handler.setLevel(logging.INFO)
        
        # Configurar logger principal
        self.app.logger.setLevel(logging.DEBUG)
        self.app.logger.addHandler(file_handler)
        self.app.logger.addHandler(debug_handler)
        self.app.logger.addHandler(console_handler)
        
        # Configurar logger do SQLAlchemy
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.engine').addHandler(debug_handler)
    
    def setup_error_handlers(self):
        """Configura handlers de erro específicos"""
        if not self.app:
            return
            
        @self.app.errorhandler(400)
        def handle_400(error):
            return self.handle_error(error, 400, "Requisição Inválida")
        
        @self.app.errorhandler(401)
        def handle_401(error):
            return self.handle_error(error, 401, "Não Autorizado")
        
        @self.app.errorhandler(403)
        def handle_403(error):
            return self.handle_error(error, 403, "Acesso Negado")
        
        @self.app.errorhandler(404)
        def handle_404(error):
            return self.handle_error(error, 404, "Página Não Encontrada")
        
        @self.app.errorhandler(500)
        def handle_500(error):
            return self.handle_error(error, 500, "Erro Interno do Servidor")
        
        @self.app.errorhandler(Exception)
        def handle_exception(error):
            return self.handle_error(error, 500, "Erro Não Tratado")
    
    def handle_error(self, error, code, message):
        """Trata erros com logging detalhado"""
        if not self.app:
            return "Error handler not configured", 500
            
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{code}"
        
        # Obter informações detalhadas do erro
        error_info = self.get_error_info(error)
        
        # Log detalhado
        self.app.logger.error(f"""
=== ERRO {error_id} ===
Código: {code}
Mensagem: {message}
Tipo: {error_info['type']}
Descrição: {error_info['description']}
Arquivo: {error_info['file']}
Linha: {error_info['line']}
Função: {error_info['function']}
URL: {error_info['url']}
Método: {error_info['method']}
IP: {error_info['ip']}
User-Agent: {error_info['user_agent']}
Traceback:
{error_info['traceback']}
========================
""")
        
        # Retornar resposta apropriada
        if request.is_json:
            return jsonify({
                'error': True,
                'code': code,
                'message': message,
                'error_id': error_id,
                'type': error_info['type'],
                'debug': error_info if self.app.debug else None
            }), code
        else:
            return render_template('errors/error.html', 
                                 error_code=code,
                                 error_message=message,
                                 error_id=error_id,
                                 error_info=error_info if self.app.debug else None), code
    
    def get_error_info(self, error):
        """Extrai informações detalhadas do erro"""
        tb = traceback.extract_tb(error.__traceback__ if hasattr(error, '__traceback__') else sys.exc_info()[2])
        
        # Informações básicas
        error_type = type(error).__name__
        error_description = str(error)
        
        # Informações do traceback
        if tb:
            last_frame = tb[-1]
            error_file = last_frame.filename
            error_line = last_frame.lineno
            error_function = last_frame.name
        else:
            error_file = "Desconhecido"
            error_line = 0
            error_function = "Desconhecido"
        
        # Informações da requisição
        try:
            url = request.url
            method = request.method
            ip = request.remote_addr
            user_agent = request.user_agent.string
        except Exception:
            url = "N/A"
            method = "N/A"
            ip = "N/A"
            user_agent = "N/A"
        
        # Traceback completo
        full_traceback = traceback.format_exception(type(error), error, error.__traceback__)
        
        return {
            'type': error_type,
            'description': error_description,
            'file': error_file,
            'line': error_line,
            'function': error_function,
            'url': url,
            'method': method,
            'ip': ip,
            'user_agent': user_agent,
            'traceback': ''.join(full_traceback)
        }
    
    def setup_exception_tracking(self):
        """Configura rastreamento de exceções"""
        if not self.app:
            return
            
        # Decorator para rastrear exceções em funções
        def track_exceptions(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if self.app:
                        self.app.logger.error(f"Exceção em {func.__name__}: {str(e)}")
                        self.app.logger.error(f"Traceback: {traceback.format_exc()}")
                    raise
            return wrapper
        
        # Disponibilizar decorator globalmente
        if hasattr(self.app, 'extensions'):
            self.app.extensions = getattr(self.app, 'extensions', {})
            self.app.extensions['track_exceptions'] = track_exceptions
        
        # Hook para todas as views
        @self.app.before_request
        def before_request():
            if self.app:
                self.app.logger.debug(f"Requisição: {request.method} {request.url}")
        
        @self.app.after_request
        def after_request(response):
            if self.app:
                self.app.logger.debug(f"Resposta: {response.status_code} para {request.url}")
            return response

# Função para inicializar o sistema de erros
def init_error_system(app):
    """Inicializa o sistema de erros na aplicação"""
    error_handler = AdvancedErrorHandler(app)
    return error_handler

# Decorator para funções que devem ser monitoradas
def monitor_function(func):
    """Decorator para monitorar funções específicas"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Log de sucesso
            logging.info(f"Função {func.__name__} executada com sucesso em {duration:.2f}s")
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Log detalhado de erro
            logging.error(f"""
Erro na função {func.__name__}:
- Duração: {duration:.2f}s
- Tipo: {type(e).__name__}
- Mensagem: {str(e)}
- Arquivo: {func.__code__.co_filename}
- Linha: {func.__code__.co_firstlineno}
- Args: {args}
- Kwargs: {kwargs}
- Traceback: {traceback.format_exc()}
""")
            raise
    
    return wrapper

# Função para log de debug customizado
def debug_log(message, level=logging.DEBUG, extra_info=None):
    """Função para logging customizado com informações extras"""
    frame = sys._getframe(1)
    
    log_message = f"[{frame.f_code.co_filename}:{frame.f_lineno}] {frame.f_code.co_name}() - {message}"
    
    if extra_info:
        log_message += f"\nInfo extra: {extra_info}"
    
    logging.log(level, log_message)

# Classe para contexto de erro
class ErrorContext:
    """Classe para manter contexto de erro"""
    
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.start_time: Optional[datetime] = None
        self.context_data = {}
    
    def __enter__(self):
        self.start_time = datetime.now()
        debug_log(f"Iniciando operação: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
        else:
            duration = 0.0
        
        if exc_type is None:
            debug_log(f"Operação {self.operation_name} concluída em {duration:.2f}s")
        else:
            logging.error(f"""
Erro na operação {self.operation_name}:
- Duração: {duration:.2f}s
- Tipo: {exc_type.__name__}
- Mensagem: {str(exc_val)}
- Contexto: {self.context_data}
- Traceback: {''.join(traceback.format_exception(exc_type, exc_val, exc_tb))}
""")
        
        return False  # Não suprimir a exceção
    
    def add_context(self, key, value):
        """Adiciona informação ao contexto"""
        self.context_data[key] = value
