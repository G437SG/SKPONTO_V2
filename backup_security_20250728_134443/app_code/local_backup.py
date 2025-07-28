# -*- coding: utf-8 -*-
"""
Sistema de Backup Local para SKPONTO
Gerencia backups automáticos e manuais usando armazenamento local
"""

import os
import shutil
import tempfile
import json
import logging
import zipfile
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any, List
from pathlib import Path
from flask import current_app
from app import db
from app.models import BackupHistory, BackupStatus, BackupType, SystemStatus
from app.constants import (
    BACKUP_STATUS_PENDING, BACKUP_STATUS_IN_PROGRESS,
    BACKUP_STATUS_COMPLETED, BACKUP_STATUS_FAILED, SYSTEM_STATUS_ACTIVE,
    SYSTEM_STATUS_ERROR, SECURITY_ACTION_UPLOAD_ATTESTATION,
    SECURITY_ACTION_DELETE_ATTESTATION
)
from app.utils import get_current_datetime, log_security_event

logger = logging.getLogger(__name__)

class LocalBackupManager:
    """Gerenciador de backups locais"""
    
    def __init__(self):
        self.base_path = None
        self.backup_path = None
        self.database_path = None
        self.attestations_path = None
        self.logs_path = None
        self.uploads_path = None
        
        self.max_backups = 30
        self.backup_schedule = 'daily'
        
        # Inicializar apenas se estivermos em contexto de aplicação
        if current_app:
            self._initialize_paths()
    
    def _initialize_paths(self):
        """Inicializa os caminhos baseado no contexto da aplicação"""
        if not current_app:
            return
            
        self.base_path = Path(current_app.root_path).parent / 'storage'
        self.backup_path = self.base_path / 'backups'
        self.database_path = self.base_path / 'database'
        self.attestations_path = self.base_path / 'attestations'
        self.logs_path = self.base_path / 'logs'
        self.uploads_path = self.base_path / 'uploads'
        
        # Criar diretórios se não existirem
        self._ensure_directories()
        
        # Configurações
        self.max_backups = current_app.config.get('BACKUP_RETENTION_DAYS', 30)
        self.backup_schedule = current_app.config.get('BACKUP_SCHEDULE', 'daily')
    
    def _ensure_directories(self):
        """Garante que todos os diretórios necessários existem"""
        if not self.base_path:
            return
            
        for path in [self.backup_path, self.database_path, self.attestations_path, 
                    self.logs_path, self.uploads_path]:
            if path:
                path.mkdir(parents=True, exist_ok=True)
    
    def _ensure_initialized(self):
        """Garante que os caminhos foram inicializados"""
        if not self.base_path:
            self._initialize_paths()
    
    def create_backup(self, backup_type: BackupType = BackupType.MANUAL, 
                     description: Optional[str] = None) -> Tuple[bool, str]:
        """
        Cria um backup completo do sistema
        
        Args:
            backup_type: Tipo do backup (MANUAL, SCHEDULED, AUTO)
            description: Descrição do backup
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        self._ensure_initialized()
        
        if not self.backup_path:
            return False, "Sistema de backup não inicializado"
        
        try:
            # Registrar início do backup
            backup_record = BackupHistory(
                filename=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                backup_type=backup_type,
                status=BackupStatus.PENDENTE,
                started_at=get_current_datetime(),
                file_size=0
            )
            db.session.add(backup_record)
            db.session.commit()
            
            # Atualizar status para em progresso
            backup_record.status = BackupStatus.EM_PROGRESSO
            backup_record.started_at = get_current_datetime()
            db.session.commit()
            
            # Criar nome do arquivo de backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"skponto_backup_{timestamp}.zip"
            backup_file_path = self.backup_path / backup_filename
            
            # Criar backup ZIP
            file_count, total_size = self._create_backup_zip(backup_file_path)
            
            # Atualizar registro do backup
            backup_record.status = BackupStatus.CONCLUIDO
            backup_record.completed_at = get_current_datetime()
            backup_record.local_path = str(backup_file_path)
            backup_record.file_size = total_size
            backup_record.filename = backup_filename
            db.session.commit()
            
            # Limpar backups antigos
            self._cleanup_old_backups()
            
            logger.info(f"Backup criado com sucesso: {backup_filename}")
            return True, f"Backup criado com sucesso: {backup_filename}"
            
        except Exception as e:
            logger.error(f"Erro ao criar backup: {str(e)}")
            if 'backup_record' in locals():
                backup_record.status = BackupStatus.FALHOU
                backup_record.error_message = str(e)
                backup_record.completed_at = get_current_datetime()
                db.session.commit()
            return False, f"Erro ao criar backup: {str(e)}"
    
    def _create_backup_zip(self, backup_file_path: Path) -> Tuple[int, int]:
        """
        Cria o arquivo ZIP com todos os arquivos do backup
        
        Returns:
            Tuple[int, int]: (número de arquivos, tamanho total)
        """
        file_count = 0
        total_size = 0
        
        with zipfile.ZipFile(backup_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Incluir banco de dados
            db_count, db_size = self._add_database_files_to_zip(zipf)
            file_count += db_count
            total_size += db_size
            
            # Incluir atestados
            att_count, att_size = self._add_directory_to_zip(zipf, self.attestations_path, "attestations")
            file_count += att_count
            total_size += att_size
            
            # Incluir uploads
            up_count, up_size = self._add_directory_to_zip(zipf, self.uploads_path, "uploads")
            file_count += up_count
            total_size += up_size
            
            # Incluir logs importantes
            log_count, log_size = self._add_logs_to_zip(zipf)
            file_count += log_count
            total_size += log_size
            
            # Incluir arquivos de configuração
            config_count, config_size = self._add_config_files_to_zip(zipf)
            file_count += config_count
            total_size += config_size
        
        return file_count, total_size
    
    def _add_database_files_to_zip(self, zipf: zipfile.ZipFile) -> Tuple[int, int]:
        """Adiciona arquivos de banco de dados ao ZIP"""
        file_count = 0
        total_size = 0
        
        db_files = self._get_database_files()
        for db_file in db_files:
            if db_file.exists():
                zipf.write(db_file, f"database/{db_file.name}")
                file_count += 1
                total_size += db_file.stat().st_size
        
        return file_count, total_size
    
    def _add_directory_to_zip(self, zipf: zipfile.ZipFile, source_path: Path, 
                             zip_prefix: str) -> Tuple[int, int]:
        """Adiciona diretório completo ao ZIP"""
        file_count = 0
        total_size = 0
        
        if source_path.exists():
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(source_path)
                    zipf.write(file_path, f"{zip_prefix}/{rel_path}")
                    file_count += 1
                    total_size += file_path.stat().st_size
        
        return file_count, total_size
    
    def _add_logs_to_zip(self, zipf: zipfile.ZipFile) -> Tuple[int, int]:
        """Adiciona logs importantes ao ZIP"""
        file_count = 0
        total_size = 0
        
        if self.logs_path.exists():
            for log_file in self.logs_path.rglob('*.log'):
                if log_file.is_file():
                    rel_path = log_file.relative_to(self.logs_path)
                    zipf.write(log_file, f"logs/{rel_path}")
                    file_count += 1
                    total_size += log_file.stat().st_size
        
        return file_count, total_size
    
    def _add_config_files_to_zip(self, zipf: zipfile.ZipFile) -> Tuple[int, int]:
        """Adiciona arquivos de configuração ao ZIP"""
        file_count = 0
        total_size = 0
        
        config_files = ['config.py', '.env', 'requirements.txt']
        base_project_path = Path(current_app.root_path).parent
        
        for config_file in config_files:
            config_path = base_project_path / config_file
            if config_path.exists():
                zipf.write(config_path, f"config/{config_file}")
                file_count += 1
                total_size += config_path.stat().st_size
        
        return file_count, total_size
    
    def _get_database_files(self) -> List[Path]:
        """Retorna lista de arquivos de banco de dados"""
        db_files = []
        
        # Arquivo principal do banco
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        if db_uri and 'sqlite' in db_uri:
            db_file = db_uri.replace('sqlite:///', '')
            db_path = Path(db_file)
            if db_path.exists():
                db_files.append(db_path)
        
        # Arquivos na pasta storage/database
        if self.database_path.exists():
            for db_file in self.database_path.glob('*.db'):
                db_files.append(db_file)
        
        # Arquivos na pasta instance
        instance_path = Path(current_app.root_path).parent / 'instance'
        if instance_path.exists():
            for db_file in instance_path.glob('*.db'):
                db_files.append(db_file)
        
        return db_files
    
    def _cleanup_old_backups(self):
        """Remove backups antigos baseado na configuração de retenção"""
        try:
            if not self.backup_path.exists():
                return
            
            # Listar todos os backups
            backup_files = list(self.backup_path.glob('skponto_backup_*.zip'))
            
            # Ordenar por data de modificação (mais recente primeiro)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Manter apenas os N backups mais recentes
            if len(backup_files) > self.max_backups:
                files_to_remove = backup_files[self.max_backups:]
                for file_to_remove in files_to_remove:
                    file_to_remove.unlink()
                    logger.info(f"Backup antigo removido: {file_to_remove.name}")
            
            # Limpar registros do banco de dados
            cutoff_date = datetime.now() - timedelta(days=self.max_backups)
            old_backups = BackupHistory.query.filter(
                BackupHistory.started_at < cutoff_date
            ).all()
            
            for old_backup in old_backups:
                db.session.delete(old_backup)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao limpar backups antigos: {str(e)}")
    
    def restore_backup(self, backup_file_path: str) -> Tuple[bool, str]:
        """
        Restaura um backup do sistema
        
        Args:
            backup_file_path: Caminho para o arquivo de backup
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            backup_path = Path(backup_file_path)
            if not backup_path.exists():
                return False, "Arquivo de backup não encontrado"
            
            # Criar diretório temporário para extração
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extrair backup
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_path)
                
                # Restaurar banco de dados
                db_backup_path = temp_path / 'database'
                if db_backup_path.exists():
                    for db_file in db_backup_path.glob('*.db'):
                        dest_path = self.database_path / db_file.name
                        shutil.copy2(db_file, dest_path)
                
                # Restaurar atestados
                attestations_backup_path = temp_path / 'attestations'
                if attestations_backup_path.exists():
                    if self.attestations_path.exists():
                        shutil.rmtree(self.attestations_path)
                    shutil.copytree(attestations_backup_path, self.attestations_path)
                
                # Restaurar uploads
                uploads_backup_path = temp_path / 'uploads'
                if uploads_backup_path.exists():
                    if self.uploads_path.exists():
                        shutil.rmtree(self.uploads_path)
                    shutil.copytree(uploads_backup_path, self.uploads_path)
            
            logger.info(f"Backup restaurado com sucesso: {backup_file_path}")
            return True, "Backup restaurado com sucesso"
            
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {str(e)}")
            return False, f"Erro ao restaurar backup: {str(e)}"
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Lista todos os backups disponíveis"""
        backups = []
        
        try:
            # Buscar backups no banco de dados
            backup_records = BackupHistory.query.order_by(
                BackupHistory.started_at.desc()
            ).all()
            
            for backup in backup_records:
                backup_info = {
                    'id': backup.id,
                    'type': backup.backup_type.value,
                    'status': backup.status.value,
                    'filename': backup.filename,
                    'started_at': backup.started_at.isoformat() if backup.started_at else None,
                    'completed_at': backup.completed_at.isoformat() if backup.completed_at else None,
                    'file_size': backup.file_size,
                    'file_path': backup.local_path,
                    'error_message': backup.error_message
                }
                
                # Verificar se o arquivo ainda existe
                if backup.local_path:
                    backup_info['file_exists'] = Path(backup.local_path).exists()
                else:
                    backup_info['file_exists'] = False
                
                backups.append(backup_info)
            
        except Exception as e:
            logger.error(f"Erro ao listar backups: {str(e)}")
        
        return backups
    
    def save_attestation(self, file_path: str, user_id: int, 
                        attestation_id: int) -> Tuple[bool, str]:
        """
        Salva um atestado médico no armazenamento local
        
        Args:
            file_path: Caminho do arquivo original
            user_id: ID do usuário
            attestation_id: ID do atestado
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem/caminho)
        """
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                return False, "Arquivo de atestado não encontrado"
            
            # Criar estrutura de diretórios por usuário
            user_dir = self.attestations_path / f"user_{user_id}"
            user_dir.mkdir(exist_ok=True)
            
            # Nome do arquivo com ID do atestado
            file_extension = source_path.suffix
            dest_filename = f"attestation_{attestation_id}{file_extension}"
            dest_path = user_dir / dest_filename
            
            # Copiar arquivo
            shutil.copy2(source_path, dest_path)
            
            # Log de segurança
            log_security_event(
                user_id, 
                SECURITY_ACTION_UPLOAD_ATTESTATION,
                f"Atestado salvo: {dest_filename}"
            )
            
            logger.info(f"Atestado salvo: {dest_path}")
            return True, str(dest_path)
            
        except Exception as e:
            logger.error(f"Erro ao salvar atestado: {str(e)}")
            return False, f"Erro ao salvar atestado: {str(e)}"
    
    def delete_attestation(self, user_id: int, attestation_id: int) -> Tuple[bool, str]:
        """
        Remove um atestado médico do armazenamento local
        
        Args:
            user_id: ID do usuário
            attestation_id: ID do atestado
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            user_dir = self.attestations_path / f"user_{user_id}"
            if not user_dir.exists():
                return False, "Diretório do usuário não encontrado"
            
            # Procurar arquivo do atestado
            attestation_files = list(user_dir.glob(f"attestation_{attestation_id}.*"))
            if not attestation_files:
                return False, "Arquivo de atestado não encontrado"
            
            # Remover arquivo
            for file_path in attestation_files:
                file_path.unlink()
            
            # Log de segurança
            log_security_event(
                user_id,
                SECURITY_ACTION_DELETE_ATTESTATION,
                f"Atestado removido: attestation_{attestation_id}"
            )
            
            logger.info(f"Atestado removido: attestation_{attestation_id}")
            return True, "Atestado removido com sucesso"
            
        except Exception as e:
            logger.error(f"Erro ao remover atestado: {str(e)}")
            return False, f"Erro ao remover atestado: {str(e)}"
    
    def get_attestation_path(self, user_id: int, attestation_id: int) -> Optional[str]:
        """
        Retorna o caminho do arquivo de atestado
        
        Args:
            user_id: ID do usuário
            attestation_id: ID do atestado
            
        Returns:
            Optional[str]: Caminho do arquivo ou None se não encontrado
        """
        try:
            user_dir = self.attestations_path / f"user_{user_id}"
            if not user_dir.exists():
                return None
            
            # Procurar arquivo do atestado
            attestation_files = list(user_dir.glob(f"attestation_{attestation_id}.*"))
            if attestation_files:
                return str(attestation_files[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar atestado: {str(e)}")
            return None
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do armazenamento local"""
        stats = {
            'total_size': 0,
            'backup_count': 0,
            'backup_size': 0,
            'attestation_count': 0,
            'attestation_size': 0,
            'upload_count': 0,
            'upload_size': 0,
            'database_size': 0
        }
        
        try:
            # Estatísticas de backups
            if self.backup_path.exists():
                backup_files = list(self.backup_path.glob('*.zip'))
                stats['backup_count'] = len(backup_files)
                stats['backup_size'] = sum(f.stat().st_size for f in backup_files)
            
            # Estatísticas de atestados
            if self.attestations_path.exists():
                attestation_files = list(self.attestations_path.rglob('*'))
                attestation_files = [f for f in attestation_files if f.is_file()]
                stats['attestation_count'] = len(attestation_files)
                stats['attestation_size'] = sum(f.stat().st_size for f in attestation_files)
            
            # Estatísticas de uploads
            if self.uploads_path.exists():
                upload_files = list(self.uploads_path.rglob('*'))
                upload_files = [f for f in upload_files if f.is_file()]
                stats['upload_count'] = len(upload_files)
                stats['upload_size'] = sum(f.stat().st_size for f in upload_files)
            
            # Estatísticas do banco de dados
            db_files = self._get_database_files()
            stats['database_size'] = sum(f.stat().st_size for f in db_files if f.exists())
            
            # Tamanho total
            stats['total_size'] = (stats['backup_size'] + stats['attestation_size'] + 
                                 stats['upload_size'] + stats['database_size'])
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {str(e)}")
        
        return stats

# Função para obter instância do gerenciador
def get_local_backup_manager():
    """Retorna uma instância do gerenciador de backup local"""
    return LocalBackupManager()
