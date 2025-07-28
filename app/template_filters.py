#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filtros Jinja2 personalizados para formatação de tempo
"""

from markupsafe import Markup
from app.time_formatter import TimeFormatter

def init_filters(app):
    """Registra filtros personalizados no Jinja2"""
    
    @app.template_filter('format_hours')
    def format_hours_filter(decimal_hours, format_type='short'):
        """
        Filtro para formatação de horas
        Uso: {{ 2.5|format_hours('time') }} → "2:30"
              {{ 2.5|format_hours('short') }} → "2h30min"  
              {{ 2.5|format_hours('long') }} → "2 horas e 30 minutos"
        """
        if decimal_hours is None:
            return "0h"
        
        formatter = TimeFormatter()
        
        if format_type == "time":
            return formatter.decimal_to_hours_minutes(decimal_hours)
        elif format_type == "long":
            return formatter.format_duration(decimal_hours, show_sign=False, short_format=False)
        else:  # short
            return formatter.format_duration(decimal_hours, show_sign=False, short_format=True)
    
    @app.template_filter('format_hours_signed')
    def format_hours_signed_filter(decimal_hours, format_type='short'):
        """
        Filtro para formatação de horas com sinal
        Uso: {{ 2.5|format_hours_signed('short') }} → "+2h30min"
        """
        if decimal_hours is None:
            return "0h"
        
        formatter = TimeFormatter()
        
        if format_type == "time":
            sign = "+" if decimal_hours > 0 else ""
            return sign + formatter.decimal_to_hours_minutes(decimal_hours)
        elif format_type == "long":
            return formatter.format_duration(decimal_hours, show_sign=True, short_format=False)
        else:  # short
            return formatter.format_duration(decimal_hours, show_sign=True, short_format=True)
    
    @app.template_filter('format_time_badge')
    def format_time_badge_filter(decimal_hours):
        """
        Filtro para formatação de horas em badges (com classes CSS)
        Uso: {{ 2.5|format_time_badge|safe }}
        """
        if decimal_hours is None:
            return '<span class="badge badge-secondary">0h</span>'
        
        formatter = TimeFormatter()
        formatted = formatter.format_duration(decimal_hours, show_sign=False, short_format=True)
        
        # Determinar classe CSS baseada no valor
        if decimal_hours > 0:
            css_class = "badge-success"
        elif decimal_hours < 0:
            css_class = "badge-danger"
        else:
            css_class = "badge-secondary"
        
        return Markup(f'<span class="badge {css_class}">{formatted}</span>')
