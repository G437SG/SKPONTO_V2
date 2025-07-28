#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitário para conversão de tempo no formato HORAS:MINUTOS
Sistema padronizado para todas as operações de tempo
"""

class TimeFormatter:
    """Classe utilitária para formatação de tempo em horas e minutos"""
    
    @staticmethod
    def decimal_to_hours_minutes(decimal_hours):
        """
        Converte horas decimais para formato H:MM
        
        Args:
            decimal_hours (float): Horas em formato decimal (ex: 2.5 = 2h30min)
            
        Returns:
            str: Tempo formatado como "H:MM" (ex: "2:30")
        """
        if decimal_hours is None:
            return "0:00"
        
        # Lidar com valores negativos
        is_negative = decimal_hours < 0
        abs_hours = abs(decimal_hours)
        
        # Separar horas e minutos
        hours = int(abs_hours)
        minutes = int((abs_hours - hours) * 60)
        
        # Formatação (sem zero à esquerda para horas)
        sign = "-" if is_negative else ""
        return f"{sign}{hours}:{minutes:02d}"
    
    @staticmethod
    def hours_minutes_to_decimal(hours_str, minutes_str=None):
        """
        Converte formato HH:MM ou separado (H, M) para decimal
        
        Args:
            hours_str (str|int): Horas ou string no formato "HH:MM"
            minutes_str (str|int, optional): Minutos (se hours_str for apenas horas)
            
        Returns:
            float: Horas em formato decimal
        """
        # Se for uma string no formato HH:MM
        if isinstance(hours_str, str) and ":" in hours_str:
            parts = hours_str.replace("-", "").split(":")
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            is_negative = hours_str.startswith("-")
        else:
            # Se for valores separados
            hours = int(hours_str) if hours_str else 0
            minutes = int(minutes_str) if minutes_str else 0
            is_negative = hours < 0
            hours = abs(hours)
        
        decimal = hours + (minutes / 60.0)
        return -decimal if is_negative else decimal
    
    @staticmethod
    def format_duration(decimal_hours, show_sign=True, short_format=False):
        """
        Formata duração para exibição amigável
        
        Args:
            decimal_hours (float): Horas em decimal
            show_sign (bool): Mostrar sinal + ou -
            short_format (bool): Formato curto (2h30) vs longo (2 horas e 30 minutos)
            
        Returns:
            str: Duração formatada
        """
        if decimal_hours is None:
            return "0h00min" if short_format else "0 horas"
        
        # Converter string para float se necessário
        if isinstance(decimal_hours, str):
            try:
                decimal_hours = float(decimal_hours)
            except (ValueError, TypeError):
                return "0h00min" if short_format else "0 horas"
        
        is_negative = decimal_hours < 0
        abs_hours = abs(decimal_hours)
        
        hours = int(abs_hours)
        minutes = int((abs_hours - hours) * 60)
        
        # Formato curto: 2h30min
        if short_format:
            sign = "-" if is_negative else ("+" if show_sign and decimal_hours > 0 else "")
            if minutes == 0:
                return f"{sign}{hours}h"
            elif hours == 0:
                return f"{sign}{minutes}min"
            else:
                return f"{sign}{hours}h{minutes:02d}min"
        
        # Formato longo: 2 horas e 30 minutos
        sign = "menos " if is_negative else ("mais " if show_sign and decimal_hours > 0 else "")
        
        if hours == 0 and minutes == 0:
            return "0 horas"
        elif hours == 0:
            return f"{sign}{minutes} minuto{'s' if minutes != 1 else ''}"
        elif minutes == 0:
            return f"{sign}{hours} hora{'s' if hours != 1 else ''}"
        else:
            return f"{sign}{hours} hora{'s' if hours != 1 else ''} e {minutes} minuto{'s' if minutes != 1 else ''}"
    
    @staticmethod
    def validate_time_input(hours, minutes):
        """
        Valida entrada de tempo
        
        Args:
            hours (str|int): Horas
            minutes (str|int): Minutos
            
        Returns:
            tuple: (is_valid, error_message, decimal_hours)
        """
        try:
            h = int(hours) if hours else 0
            m = int(minutes) if minutes else 0
            
            if m < 0 or m >= 60:
                return False, "Minutos devem estar entre 0 e 59", 0
            
            if abs(h) > 999:
                return False, "Horas não podem exceder 999", 0
            
            decimal = TimeFormatter.hours_minutes_to_decimal(h, m)
            return True, "", decimal
            
        except (ValueError, TypeError):
            return False, "Valores inválidos para horas ou minutos", 0

# Função de conveniência para uso direto
def format_hours(decimal_hours, format_type="short"):
    """
    Função de conveniência para formatação rápida
    
    Args:
        decimal_hours (float): Horas em decimal
        format_type (str): "short", "long", "time" (HH:MM)
        
    Returns:
        str: Tempo formatado
    """
    formatter = TimeFormatter()
    
    if format_type == "time":
        return formatter.decimal_to_hours_minutes(decimal_hours)
    elif format_type == "long":
        return formatter.format_duration(decimal_hours, show_sign=False, short_format=False)
    else:  # short
        return formatter.format_duration(decimal_hours, show_sign=False, short_format=True)
