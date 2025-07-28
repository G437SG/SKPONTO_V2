# -*- coding: utf-8 -*-
"""
Gerenciador de Armazenamento Local para SKPONTO
Centraliza todas as operações de armazenamento local
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from flask import current_app
from app.local_backup import get_local_backup_manager
from app.local_upload_service import get_local_upload_service

logger = logging.getLogger(__name__)

class LocalStorageManager:
    """Gerenciador centralizado de armazenamento local"""
    
    def __init__(self):
        self.base_path = Path(current_app.root_path).parent / 'storage'
        self.backup_manager = get_local_backup_manager()
        self.upload_service = get_local_upload_service()
        
        # Inicializar estrutura
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Inicializa a estrutura de armazenamento local"""
        try:
            # Criar diretórios principais
            directories = [
                'database',
                'backups', 
                'attestations',
                'uploads',
                'logs',
                'temp'
            ]
            
            for directory in directories:
                dir_path = self.base_path / directory
                dir_path.mkdir(parents=True, exist_ok=True)
                
                # Criar arquivo .gitkeep para manter a estrutura no Git
                gitkeep_file = dir_path / '.gitkeep'
                if not gitkeep_file.exists():
                    gitkeep_file.touch()
            
            logger.info("Estrutura de armazenamento local inicializada")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar armazenamento local: {str(e)}")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Retorna informações detalhadas sobre o armazenamento"""
        info = {
            'base_path': str(self.base_path),
            'total_size': 0,
            'directories': {},
            'last_backup': None,
            'backup_count': 0,
            'status': 'healthy'
        }
        
        try:
            # Verificar cada diretório
            for directory in ['database', 'backups', 'attestations', 'uploads', 'logs']:
                dir_path = self.base_path / directory
                if dir_path.exists():
                    # Calcular tamanho do diretório
                    dir_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                    file_count = len([f for f in dir_path.rglob('*') if f.is_file()])
                    
                    info['directories'][directory] = {
                        'path': str(dir_path),
                        'size': dir_size,
                        'file_count': file_count,
                        'exists': True
                    }
                    
                    info['total_size'] += dir_size
                else:
                    info['directories'][directory] = {
                        'path': str(dir_path),
                        'size': 0,
                        'file_count': 0,
                        'exists': False
                    }
            
            # Informações de backup
            backups = self.backup_manager.list_backups()
            info['backup_count'] = len(backups)
            if backups:
                info['last_backup'] = backups[0].get('created_at')
            
            # Status geral
            missing_dirs = [d for d, data in info['directories'].items() if not data['exists']]
            if missing_dirs:
                info['status'] = 'warning'
                info['issues'] = f"Diretórios ausentes: {', '.join(missing_dirs)}"
            
        except Exception as e:
            logger.error(f"Erro ao obter informações de armazenamento: {str(e)}")
            info['status'] = 'error'
            info['error'] = str(e)
        
        return info
    
    def migrate_from_external_storage(self, external_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Migra dados de armazenamento externo para armazenamento local
        
        Args:
            external_path: Caminho opcional para dados externos
            
        Returns:
            Dict com resultado da migração
        """
        result = {
            'success': False,
            'message': '',
            'migrated_files': 0,
            'total_size': 0,
            'errors': []
        }
        
        try:
            search_paths = self._get_external_search_paths(external_path)
            migrated_files = 0
            total_size = 0
            
            for search_path in search_paths:
                if not search_path.exists():
                    continue
                
                # Migrar diferentes tipos de arquivos
                db_files, db_size = self._migrate_database_files(search_path)
                backup_files, backup_size = self._migrate_backup_files(search_path)
                att_files, att_size = self._migrate_attestation_files(search_path)
                
                migrated_files += db_files + backup_files + att_files
                total_size += db_size + backup_size + att_size
            
            result['migrated_files'] = migrated_files
            result['total_size'] = total_size
            
            if migrated_files > 0:
                result['success'] = True
                result['message'] = f"Migração concluída: {migrated_files} arquivos migrados ({total_size / (1024*1024):.1f} MB)"
            else:
                result['message'] = "Nenhum arquivo externo encontrado para migração"
            
        except Exception as e:
            logger.error(f"Erro na migração de arquivos externos: {str(e)}")
            result['errors'].append(str(e))
            result['message'] = f"Erro na migração: {str(e)}"
        
        return result
    
    def _get_external_search_paths(self, external_path: Optional[str]) -> list:
        """Retorna lista de caminhos para procurar dados externos"""
        search_paths = [
            Path(current_app.root_path).parent / 'shared_storage',
            Path(current_app.root_path).parent / 'temp',
            Path(current_app.root_path).parent / 'instance'
        ]
        
        if external_path:
            search_paths.insert(0, Path(external_path))
        
        return search_paths
    
    def _migrate_database_files(self, search_path: Path) -> tuple:
        """Migra arquivos de banco de dados"""
        migrated_files = 0
        total_size = 0
        
        for db_file in search_path.rglob('*.db'):
            if 'skponto' in db_file.name.lower():
                dest_path = self.base_path / 'database' / db_file.name
                if not dest_path.exists():
                    shutil.copy2(db_file, dest_path)
                    migrated_files += 1
                    total_size += db_file.stat().st_size
                    logger.info(f"Banco migrado: {db_file} -> {dest_path}")
        
        return migrated_files, total_size
    
    def _migrate_backup_files(self, search_path: Path) -> tuple:
        """Migra arquivos de backup"""
        migrated_files = 0
        total_size = 0
        
        for backup_file in search_path.rglob('*.zip'):
            if 'backup' in backup_file.name.lower():
                dest_path = self.base_path / 'backups' / backup_file.name
                if not dest_path.exists():
                    shutil.copy2(backup_file, dest_path)
                    migrated_files += 1
                    total_size += backup_file.stat().st_size
                    logger.info(f"Backup migrado: {backup_file} -> {dest_path}")
        
        return migrated_files, total_size
    
    def _migrate_attestation_files(self, search_path: Path) -> tuple:
        """Migra arquivos de atestados"""
        migrated_files = 0
        total_size = 0
        
        attestation_exts = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx']
        
        for ext in attestation_exts:
            for att_file in search_path.rglob(f'*{ext}'):
                if 'atestado' in att_file.name.lower() or 'attestation' in att_file.name.lower():
                    # Organizar por data
                    date_dir = self.base_path / 'attestations' / 'migrated' / datetime.now().strftime('%Y-%m')
                    date_dir.mkdir(parents=True, exist_ok=True)
                    
                    dest_path = date_dir / att_file.name
                    if not dest_path.exists():
                        shutil.copy2(att_file, dest_path)
                        migrated_files += 1
                        total_size += att_file.stat().st_size
                        logger.info(f"Atestado migrado: {att_file} -> {dest_path}")
        
        return migrated_files, total_size
    
    def cleanup_old_files(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Remove arquivos antigos para liberar espaço
        
        Args:
            days_old: Idade em dias para considerar arquivos antigos
            
        Returns:
            Dict com resultado da limpeza
        """
        result = {
            'success': False,
            'message': '',
            'files_removed': 0,
            'space_freed': 0,
            'errors': []
        }
        
        try:
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
            files_removed = 0
            space_freed = 0
            
            # Limpar arquivos temporários
            temp_path = self.base_path / 'temp'
            if temp_path.exists():
                for temp_file in temp_path.rglob('*'):
                    if temp_file.is_file() and temp_file.stat().st_mtime < cutoff_time:
                        file_size = temp_file.stat().st_size
                        temp_file.unlink()
                        files_removed += 1
                        space_freed += file_size
                        logger.info(f"Arquivo temporário removido: {temp_file}")
            
            # Limpar logs antigos
            logs_path = self.base_path / 'logs'
            if logs_path.exists():
                for log_file in logs_path.rglob('*.log'):
                    if log_file.is_file() and log_file.stat().st_mtime < cutoff_time:
                        file_size = log_file.stat().st_size
                        log_file.unlink()
                        files_removed += 1
                        space_freed += file_size
                        logger.info(f"Log antigo removido: {log_file}")
            
            # Limpar backups antigos (manter apenas os configurados)
            self.backup_manager._cleanup_old_backups()
            
            result['files_removed'] = files_removed
            result['space_freed'] = space_freed
            result['success'] = True
            result['message'] = f"Limpeza concluída: {files_removed} arquivos removidos, {space_freed / (1024*1024):.1f} MB liberados"
            
        except Exception as e:
            logger.error(f"Erro na limpeza de arquivos: {str(e)}")
            result['errors'].append(str(e))
            result['message'] = f"Erro na limpeza: {str(e)}"
        
        return result
    
    def create_storage_report(self) -> Dict[str, Any]:
        """Cria relatório detalhado do armazenamento"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'storage_info': self.get_storage_info(),
            'backup_stats': self.backup_manager.get_storage_stats(),
            'upload_stats': self.upload_service.get_storage_usage(),
            'recommendations': []
        }
        
        try:
            # Adicionar recomendações baseadas no uso
            storage_info = report['storage_info']
            total_size_mb = storage_info['total_size'] / (1024 * 1024)
            
            if total_size_mb > 500:
                report['recommendations'].append({
                    'type': 'warning',
                    'message': f'Armazenamento grande ({total_size_mb:.1f} MB). Considere fazer limpeza.'
                })
            
            if storage_info['backup_count'] == 0:
                report['recommendations'].append({
                    'type': 'error',
                    'message': 'Nenhum backup encontrado. Crie um backup do sistema.'
                })
            
            if storage_info['backup_count'] > 50:
                report['recommendations'].append({
                    'type': 'info',
                    'message': f'Muitos backups ({storage_info["backup_count"]}). Considere ajustar a retenção.'
                })
            
        except Exception as e:
            logger.error(f"Erro ao criar relatório: {str(e)}")
            report['error'] = str(e)
        
        return report
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verifica a integridade do armazenamento local"""
        result = {
            'success': True,
            'message': 'Integridade verificada com sucesso',
            'checks': {},
            'errors': []
        }
        
        try:
            # Verificar estrutura de diretórios
            required_dirs = ['database', 'backups', 'attestations', 'uploads', 'logs']
            for directory in required_dirs:
                dir_path = self.base_path / directory
                result['checks'][f'directory_{directory}'] = {
                    'exists': dir_path.exists(),
                    'writable': os.access(dir_path, os.W_OK) if dir_path.exists() else False
                }
                
                if not dir_path.exists():
                    result['errors'].append(f"Diretório ausente: {directory}")
                    result['success'] = False
                elif not os.access(dir_path, os.W_OK):
                    result['errors'].append(f"Diretório sem permissão de escrita: {directory}")
                    result['success'] = False
            
            # Verificar banco de dados
            db_path = self.base_path / 'database'
            if db_path.exists():
                db_files = list(db_path.glob('*.db'))
                result['checks']['database_files'] = {
                    'count': len(db_files),
                    'total_size': sum(f.stat().st_size for f in db_files)
                }
                
                if len(db_files) == 0:
                    result['errors'].append("Nenhum arquivo de banco de dados encontrado")
                    result['success'] = False
            
            # Verificar backups
            backup_files = list((self.base_path / 'backups').glob('*.zip'))
            result['checks']['backup_files'] = {
                'count': len(backup_files),
                'latest': max(backup_files, key=lambda f: f.stat().st_mtime).name if backup_files else None
            }
            
            if not result['success']:
                result['message'] = f"Problemas encontrados: {len(result['errors'])} erros"
            
        except Exception as e:
            logger.error(f"Erro na verificação de integridade: {str(e)}")
            result['success'] = False
            result['errors'].append(str(e))
            result['message'] = f"Erro na verificação: {str(e)}"
        
        return result

# Função para obter instância do gerenciador
def get_local_storage_manager():
    """Retorna uma instância do gerenciador de armazenamento local"""
    return LocalStorageManager()
