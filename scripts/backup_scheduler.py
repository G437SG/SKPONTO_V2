# -*- coding: utf-8 -*-
"""
Serviço de Backup Automático para SKPONTO
Sistema de agendamento e execução de backups automáticos
"""

import os
import time
import logging
from threading import Thread, Event
from datetime import datetime, timedelta
from typing import Optional

from flask import current_app
from app import create_app
from app.models import BackupHistory, BackupType, BackupStatus
from app.local_backup import LocalBackupManager
from app.utils import log_security_event

logger = logging.getLogger(__name__)

class BackupScheduler:
    """Agendador de backups automáticos"""
    
    def __init__(self):
        self.app = None
        self.backup_thread = None
        self.stop_event = Event()
        self.is_running = False
        
    def init_app(self, app):
        """Inicializa o agendador com a aplicação Flask"""
        self.app = app
        
    def start(self):
        """Inicia o agendador de backup automático"""
        if self.is_running:
            logger.warning("Agendador de backup já está executando")
            return
            
        logger.info("Iniciando agendador de backup automático")
        self.stop_event.clear()
        self.is_running = True
        
        # Iniciar thread de backup
        self.backup_thread = Thread(target=self._backup_loop, daemon=True)
        self.backup_thread.start()
        
    def stop(self):
        """Para o agendador de backup automático"""
        if not self.is_running:
            return
            
        logger.info("Parando agendador de backup automático")
        self.stop_event.set()
        self.is_running = False
        
        if self.backup_thread and self.backup_thread.is_alive():
            self.backup_thread.join(timeout=5)
            
    def _backup_loop(self):
        """Loop principal do agendador"""
        while not self.stop_event.is_set():
            try:
                with self.app.app_context():
                    self._check_and_run_backup()
                    
                # Verificar a cada hora
                self.stop_event.wait(3600)  # 1 hora
                
            except Exception as e:
                logger.error(f"Erro no loop de backup: {e}")
                self.stop_event.wait(300)  # 5 minutos em caso de erro
                
    def _check_and_run_backup(self):
        """Verifica se é necessário executar backup e executa se necessário"""
        try:
            # Verificar se backup automático está habilitado
            if not current_app.config.get('AUTO_BACKUP_ENABLED', False):
                return
                
            frequency_hours = current_app.config.get('BACKUP_FREQUENCY_HOURS', 24)
            
            # Verificar último backup automático
            last_backup = BackupHistory.query.filter_by(
                backup_type=BackupType.AUTOMATICO
            ).order_by(BackupHistory.started_at.desc()).first()
            
            now = datetime.now()
            should_backup = False
            
            if not last_backup:
                # Primeiro backup automático
                should_backup = True
                logger.info("Executando primeiro backup automático")
            else:
                # Verificar se já passou o tempo configurado
                time_since_last = now - last_backup.started_at
                if time_since_last.total_seconds() >= (frequency_hours * 3600):
                    should_backup = True
                    logger.info(f"Tempo desde último backup: {time_since_last}, executando backup automático")
                    
            if should_backup:
                self._execute_automatic_backup()
                
        except Exception as e:
            logger.error(f"Erro ao verificar necessidade de backup: {e}")
            
    def _execute_automatic_backup(self):
        """Executa um backup automático"""
        try:
            backup_manager = LocalBackupManager()
            
            # Criar backup automático
            success, message = backup_manager.create_backup(
                backup_type=BackupType.AUTOMATICO
            )
            
            if success:
                logger.info(f"Backup automático executado com sucesso: {message}")
                
                # Log de segurança
                log_security_event(
                    user_id=None,
                    action='automatic_backup_success',
                    details=f"Backup automático criado: {message}"
                )
            else:
                logger.error(f"Falha no backup automático: {message}")
                
                # Log de segurança
                log_security_event(
                    user_id=None,
                    action='automatic_backup_failed',
                    details=f"Erro no backup automático: {message}"
                )
                
        except Exception as e:
            logger.error(f"Erro ao executar backup automático: {e}")
            
    def run_manual_backup(self, user_id: int) -> Optional[int]:
        """Executa um backup manual"""
        try:
            backup_manager = LocalBackupManager()
            
            success, message = backup_manager.create_backup(
                backup_type=BackupType.MANUAL
            )
            
            if success:
                logger.info(f"Backup manual executado com sucesso por usuário {user_id}")
                
                # Log de segurança
                log_security_event(
                    user_id=user_id,
                    action='manual_backup_success',
                    details=f"Backup manual criado: {message}"
                )
                
                return 1  # ID fictício para compatibilidade
            else:
                logger.error(f"Falha no backup manual: {message}")
                
                # Log de segurança
                log_security_event(
                    user_id=user_id,
                    action='manual_backup_failed',
                    details=f"Erro no backup manual: {message}"
                )
                
                return None
                
        except Exception as e:
            logger.error(f"Erro ao executar backup manual: {e}")
            return None
            
    def get_status(self) -> dict:
        """Retorna status do agendador"""
        try:
            if self.app:
                with self.app.app_context():
                    auto_backup_enabled = current_app.config.get('AUTO_BACKUP_ENABLED', False)
                    frequency_hours = current_app.config.get('BACKUP_FREQUENCY_HOURS', 24)
                    
                    # Último backup automático
                    last_backup = None
                    next_backup = None
                    
                    last_backup_obj = BackupHistory.query.filter_by(
                        backup_type=BackupType.AUTOMATICO
                    ).order_by(BackupHistory.started_at.desc()).first()
                    
                    if last_backup_obj:
                        last_backup = last_backup_obj.started_at
                        next_backup = last_backup + timedelta(hours=frequency_hours)
                    elif auto_backup_enabled:
                        # Se não há backup anterior, próximo será em breve
                        next_backup = datetime.now() + timedelta(minutes=5)
                    
                    return {
                        'is_running': self.is_running,
                        'auto_backup_enabled': auto_backup_enabled,
                        'frequency_hours': frequency_hours,
                        'last_backup': last_backup,
                        'next_backup': next_backup
                    }
            else:
                return {
                    'is_running': self.is_running,
                    'auto_backup_enabled': False,
                    'frequency_hours': 24,
                    'last_backup': None,
                    'next_backup': None
                }
                
        except Exception as e:
            logger.error(f"Erro ao obter status do agendador: {e}")
            return {
                'is_running': self.is_running,
                'auto_backup_enabled': False,
                'frequency_hours': 24,
                'last_backup': None,
                'next_backup': None,
                'error': str(e)
            }

# Instância global do agendador
backup_scheduler = BackupScheduler()

def init_scheduler(app):
    """Inicializa o agendador com a aplicação"""
    backup_scheduler.init_app(app)
    
    # Iniciar automaticamente se configurado
    if app.config.get('AUTO_BACKUP_ENABLED', False):
        backup_scheduler.start()
        logger.info("Agendador de backup automático iniciado")
    else:
        logger.info("Backup automático desabilitado")
