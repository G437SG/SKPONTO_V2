#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decoradores específicos para monitoramento de rotas críticas
"""

import functools
import logging
from datetime import datetime
from flask import request, jsonify
from app.error_handler import debug_log, ErrorContext

def monitor_auth_route(route_name):
    """Decorator específico para rotas de autenticação"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            with ErrorContext(f"auth_{route_name}") as ctx:
                ctx.add_context("route", route_name)
                ctx.add_context("method", request.method)
                ctx.add_context("ip", request.remote_addr)
                ctx.add_context("user_agent", request.user_agent.string)
                
                try:
                    debug_log(f"Iniciando rota de autenticação: {route_name}")
                    result = func(*args, **kwargs)
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    debug_log(f"Rota {route_name} concluída em {duration:.2f}s")
                    return result
                    
                except Exception as e:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    logging.error(f"""
ERRO NA ROTA DE AUTENTICAÇÃO:
- Rota: {route_name}
- Duração: {duration:.2f}s
- Método: {request.method}
- IP: {request.remote_addr}
- Erro: {str(e)}
- Tipo: {type(e).__name__}
""")
                    raise
                    
        return wrapper
    return decorator

def monitor_main_route(route_name):
    """Decorator específico para rotas principais"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            with ErrorContext(f"main_{route_name}") as ctx:
                ctx.add_context("route", route_name)
                ctx.add_context("method", request.method)
                ctx.add_context("authenticated", hasattr(request, 'user'))
                
                try:
                    debug_log(f"Iniciando rota principal: {route_name}")
                    result = func(*args, **kwargs)
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    debug_log(f"Rota {route_name} concluída em {duration:.2f}s")
                    return result
                    
                except Exception as e:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    logging.error(f"""
ERRO NA ROTA PRINCIPAL:
- Rota: {route_name}
- Duração: {duration:.2f}s
- Método: {request.method}
- Autenticado: {hasattr(request, 'user')}
- Erro: {str(e)}
- Tipo: {type(e).__name__}
""")
                    raise
                    
        return wrapper
    return decorator

def monitor_api_route(route_name):
    """Decorator específico para rotas de API"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            with ErrorContext(f"api_{route_name}") as ctx:
                ctx.add_context("route", route_name)
                ctx.add_context("method", request.method)
                ctx.add_context("content_type", request.content_type)
                
                try:
                    debug_log(f"Iniciando rota de API: {route_name}")
                    result = func(*args, **kwargs)
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    debug_log(f"API {route_name} concluída em {duration:.2f}s")
                    return result
                    
                except Exception as e:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    logging.error(f"""
ERRO NA API:
- Rota: {route_name}
- Duração: {duration:.2f}s
- Método: {request.method}
- Content-Type: {request.content_type}
- Erro: {str(e)}
- Tipo: {type(e).__name__}
""")
                    
                    # Retornar erro JSON para APIs
                    return jsonify({
                        'error': True,
                        'message': 'Erro interno da API',
                        'type': type(e).__name__,
                        'route': route_name,
                        'timestamp': datetime.now().isoformat()
                    }), 500
                    
        return wrapper
    return decorator
