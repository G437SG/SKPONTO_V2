#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para configurar sistema de logging em produção
"""

import os
import logging
import logging.config
from datetime import datetime
from typing import Dict, Any

def setup_production_logging():
    """Configura logging completo para produção"""
    
    # Criar diretório de logs
    os.makedirs('logs', exist_ok=True)
    
    # Configuração completa de logging
    logging_config: Dict[str, Any] = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "file": "%(filename)s", "line": %(lineno)d, "function": "%(funcName)s", "message": "%(message)s"}',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': 'logs/errors.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'debug_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': 'logs/debug.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 3,
                'encoding': 'utf8'
            },
            'auth_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filename': 'logs/auth.log',
                'maxBytes': 5242880,  # 5MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'security_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'WARNING',
                'formatter': 'detailed',
                'filename': 'logs/security.log',
                'maxBytes': 5242880,  # 5MB
                'backupCount': 10,
                'encoding': 'utf8'
            },
            'performance_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filename': 'logs/performance.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            '': {  # Root logger
                'level': 'DEBUG',
                'handlers': ['console', 'error_file', 'debug_file']
            },
            'app.auth': {
                'level': 'INFO',
                'handlers': ['auth_file'],
                'propagate': True
            },
            'app.security': {
                'level': 'WARNING',
                'handlers': ['security_file'],
                'propagate': True
            },
            'app.performance': {
                'level': 'INFO',
                'handlers': ['performance_file'],
                'propagate': False
            },
            'werkzeug': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'sqlalchemy.engine': {
                'level': 'WARNING',
                'handlers': ['debug_file'],
                'propagate': False
            }
        }
    }
    
    # Aplicar configuração
    logging.config.dictConfig(logging_config)
    
    # Criar loggers específicos
    auth_logger = logging.getLogger('app.auth')
    security_logger = logging.getLogger('app.security')
    performance_logger = logging.getLogger('app.performance')
    
    # Log de inicialização
    logging.info("Sistema de logging configurado para produção")
    auth_logger.info("Logger de autenticação inicializado")
    security_logger.warning("Logger de segurança inicializado")
    performance_logger.info("Logger de performance inicializado")
    
    return {
        'auth': auth_logger,
        'security': security_logger,
        'performance': performance_logger
    }

# Classe para logging de performance
class PerformanceLogger:
    """Logger específico para métricas de performance"""
    
    def __init__(self):
        self.logger = logging.getLogger('app.performance')
    
    def log_request(self, method, url, duration, status_code, user_id=None):
        """Log de requisição com métricas"""
        self.logger.info({
            'type': 'request',
            'method': method,
            'url': url,
            'duration': duration,
            'status_code': status_code,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_database_query(self, query, duration, result_count=None):
        """Log de consulta ao banco"""
        self.logger.info({
            'type': 'database_query',
            'query': query[:100] + '...' if len(query) > 100 else query,
            'duration': duration,
            'result_count': result_count,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_error(self, error_type, error_message, location, user_id=None):
        """Log de erro com contexto"""
        self.logger.error({
            'type': 'error',
            'error_type': error_type,
            'error_message': error_message,
            'location': location,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })

# Classe para logging de segurança
class SecurityLogger:
    """Logger específico para eventos de segurança"""
    
    def __init__(self):
        self.logger = logging.getLogger('app.security')
    
    def log_login_attempt(self, email, success, ip_address, user_agent):
        """Log de tentativa de login"""
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, {
            'type': 'login_attempt',
            'email': email,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_access_denied(self, url, user_id, reason):
        """Log de acesso negado"""
        self.logger.warning({
            'type': 'access_denied',
            'url': url,
            'user_id': user_id,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_suspicious_activity(self, activity_type, details, user_id=None, ip_address=None):
        """Log de atividade suspeita"""
        self.logger.warning({
            'type': 'suspicious_activity',
            'activity_type': activity_type,
            'details': details,
            'user_id': user_id,
            'ip_address': ip_address,
            'timestamp': datetime.now().isoformat()
        })

# Instâncias globais
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()

if __name__ == "__main__":
    # Configurar logging se executado diretamente
    loggers = setup_production_logging()
    print("Sistema de logging configurado com sucesso!")
    print(f"Loggers disponíveis: {list(loggers.keys())}")
    
    # Teste básico
    performance_logger.log_request("GET", "/test", 0.5, 200)
    security_logger.log_login_attempt("test@test.com", True, "127.0.0.1", "Test Agent")
    
    print("Logs de teste criados em logs/")
    print("Arquivos de log disponíveis:")
    for file in os.listdir('logs'):
        print(f"  - logs/{file}")
