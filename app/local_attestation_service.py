# -*- coding: utf-8 -*-
"""
Sistema de Atestados Local para SKPONTO
Substitui o antigo sistema externo por armazenamento local
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Dict, Any, List
from werkzeug.utils import secure_filename
from flask import current_app
from app.utils import log_security_event
from app.constants import SECURITY_ACTION_UPLOAD_ATTESTATION, SECURITY_ACTION_DELETE_ATTESTATION

logger = logging.getLogger(__name__)

# Constantes
ATTESTATION_FILE_PATTERN = "*attestation_*"

class LocalAttestationService:
    """Serviço local para gerenciar atestados médicos"""
    
    def __init__(self):
        self.base_path = Path(current_app.root_path).parent / 'storage' / 'attestations'
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Configurações
        self.allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {
            'pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx'
        })
        self.max_file_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    
    def upload_attestation(self, file_data, user_id: int, attestation_id: int,
                          original_filename: str, attestation_type: Optional[str] = None) -> Tuple[bool, str]:
        """
        Faz upload de um atestado médico
        
        Args:
            file_data: Dados do arquivo (werkzeug.FileStorage ou bytes)
            user_id: ID do usuário
            attestation_id: ID do atestado
            original_filename: Nome original do arquivo
            attestation_type: Tipo do atestado (MEDICO, ODONTOLOGICO, etc.)
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem/caminho)
        """
        try:
            # Validar arquivo
            if not self._is_valid_file(file_data, original_filename):
                return False, "Arquivo inválido ou tipo não permitido"
            
            # Criar estrutura de diretórios
            user_dir = self._get_user_directory(user_id)
            year_month = datetime.now().strftime('%Y-%m')
            attestation_dir = user_dir / year_month
            attestation_dir.mkdir(parents=True, exist_ok=True)
            
            # Gerar nome do arquivo
            filename = self._generate_filename(attestation_id, original_filename, attestation_type)
            file_path = attestation_dir / filename
            
            # Salvar arquivo
            if hasattr(file_data, 'save'):
                # É um FileStorage
                file_data.save(str(file_path))
            else:
                # É bytes
                with open(file_path, 'wb') as f:
                    f.write(file_data)
            
            # Verificar se foi salvo corretamente
            if not file_path.exists():
                return False, "Erro ao salvar arquivo"
            
            # Obter tamanho do arquivo
            file_size = file_path.stat().st_size
            
            # Log de segurança
            log_security_event(
                user_id,
                SECURITY_ACTION_UPLOAD_ATTESTATION,
                f"Atestado enviado: {filename} ({file_size} bytes)"
            )
            
            logger.info(f"Atestado salvo: {file_path} ({file_size} bytes)")
            return True, str(file_path)
            
        except Exception as e:
            logger.error(f"Erro ao fazer upload de atestado: {str(e)}")
            return False, f"Erro ao fazer upload: {str(e)}"
    
    def delete_attestation(self, user_id: int, attestation_id: int) -> Tuple[bool, str]:
        """
        Remove um atestado do armazenamento local
        
        Args:
            user_id: ID do usuário
            attestation_id: ID do atestado
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            user_dir = self._get_user_directory(user_id)
            if not user_dir.exists():
                return False, "Diretório do usuário não encontrado"
            
            # Procurar arquivo do atestado em todas as pastas do usuário
            attestation_files = list(user_dir.rglob(f"*attestation_{attestation_id}_*"))
            
            if not attestation_files:
                return False, "Arquivo de atestado não encontrado"
            
            # Remover arquivo(s)
            for file_path in attestation_files:
                file_path.unlink()
                logger.info(f"Atestado removido: {file_path}")
            
            # Log de segurança
            log_security_event(
                user_id,
                SECURITY_ACTION_DELETE_ATTESTATION,
                f"Atestado removido: attestation_{attestation_id}"
            )
            
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
            user_dir = self._get_user_directory(user_id)
            if not user_dir.exists():
                return None
            
            # Procurar arquivo do atestado em todas as pastas do usuário
            attestation_files = list(user_dir.rglob(f"*attestation_{attestation_id}_*"))
            
            if attestation_files:
                return str(attestation_files[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar atestado: {str(e)}")
            return None
    
    def list_user_attestations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Lista todos os atestados de um usuário
        
        Args:
            user_id: ID do usuário
            
        Returns:
            List[Dict]: Lista de informações dos atestados
        """
        attestations = []
        
        try:
            user_dir = self._get_user_directory(user_id)
            if not user_dir.exists():
                return attestations
            
            # Buscar todos os arquivos de atestado
            attestation_files = list(user_dir.rglob(ATTESTATION_FILE_PATTERN))
            
            for file_path in attestation_files:
                try:
                    attestation_info = self._extract_file_info(file_path)
                    if attestation_info:
                        attestations.append(attestation_info)
                except Exception as e:
                    logger.error(f"Erro ao processar arquivo {file_path}: {str(e)}")
                    continue
            
            # Ordenar por data de criação (mais recente primeiro)
            attestations.sort(key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"Erro ao listar atestados do usuário: {str(e)}")
        
        return attestations
    
    def get_attestation_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retorna estatísticas dos atestados
        
        Args:
            user_id: ID do usuário (se None, retorna estatísticas globais)
            
        Returns:
            Dict: Estatísticas dos atestados
        """
        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_type': {},
            'by_month': {},
            'by_user': {}
        }
        
        try:
            if user_id:
                # Estatísticas específicas do usuário
                user_dir = self._get_user_directory(user_id)
                if user_dir.exists():
                    attestation_files = list(user_dir.rglob("*attestation_*"))
                else:
                    attestation_files = []
            else:
                # Estatísticas globais
                attestation_files = list(self.base_path.rglob(ATTESTATION_FILE_PATTERN))
            
            # Processar cada arquivo
            for file_path in attestation_files:
                if file_path.is_file():
                    file_info = self._extract_file_info(file_path)
                    if file_info:
                        stats['total_files'] += 1
                        stats['total_size'] += file_info['file_size']
                        
                        # Estatísticas por tipo
                        file_type = file_info.get('type', 'UNKNOWN')
                        stats['by_type'][file_type] = stats['by_type'].get(file_type, 0) + 1
                        
                        # Estatísticas por mês
                        month = file_info['created_at'].strftime('%Y-%m')
                        stats['by_month'][month] = stats['by_month'].get(month, 0) + 1
                        
                        # Estatísticas por usuário (apenas para stats globais)
                        if not user_id:
                            user_folder = file_path.parent.parent.name  # user_X
                            stats['by_user'][user_folder] = stats['by_user'].get(user_folder, 0) + 1
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {str(e)}")
        
        return stats
    
    def _is_valid_file(self, file_data, filename: str) -> bool:
        """Valida se o arquivo é válido"""
        if not filename or not file_data:
            return False
        
        # Verificar extensão
        if not ('.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions):
            return False
        
        # Verificar tamanho
        if hasattr(file_data, 'seek'):
            # É um FileStorage
            file_data.seek(0, 2)  # Ir para o final
            file_size = file_data.tell()
            file_data.seek(0)  # Voltar ao início
        else:
            # É bytes
            file_size = len(file_data)
        
        return file_size <= self.max_file_size
    
    def _get_user_directory(self, user_id: int) -> Path:
        """Retorna o diretório do usuário"""
        return self.base_path / f"user_{user_id}"
    
    def _generate_filename(self, attestation_id: int, original_filename: str, 
                          attestation_type: Optional[str] = None) -> str:
        """Gera nome único para o arquivo"""
        secure_name = secure_filename(original_filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if attestation_type:
            return f"{attestation_type}_attestation_{attestation_id}_{timestamp}_{secure_name}"
        else:
            return f"attestation_{attestation_id}_{timestamp}_{secure_name}"
    
    def _extract_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extrai informações do arquivo de atestado"""
        try:
            filename = file_path.name
            file_stats = file_path.stat()
            
            # Tentar extrair informações do nome do arquivo
            parts = filename.split('_')
            attestation_id = None
            attestation_type = None
            
            # Diferentes formatos de nome
            if len(parts) >= 3:
                if parts[0] in ['MEDICO', 'ODONTOLOGICO', 'PSICOLOGICO', 'OUTROS']:
                    attestation_type = parts[0]
                    if parts[1] == 'attestation' and parts[2].isdigit():
                        attestation_id = int(parts[2])
                elif parts[0] == 'attestation' and parts[1].isdigit():
                    attestation_id = int(parts[1])
            
            return {
                'attestation_id': attestation_id,
                'type': attestation_type,
                'filename': filename,
                'file_path': str(file_path),
                'file_size': file_stats.st_size,
                'created_at': datetime.fromtimestamp(file_stats.st_ctime),
                'modified_at': datetime.fromtimestamp(file_stats.st_mtime)
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair informações do arquivo {file_path}: {str(e)}")
            return None
    
    def migrate_old_attestations(self, old_path: str) -> Dict[str, Any]:
        """
        Migra atestados do sistema antigo
        
        Args:
            old_path: Caminho do sistema antigo
            
        Returns:
            Dict: Resultado da migração
        """
        result = {
            'success': False,
            'message': '',
            'migrated_files': 0,
            'total_size': 0,
            'errors': []
        }
        
        try:
            old_path_obj = Path(old_path)
            if not old_path_obj.exists():
                result['message'] = "Caminho antigo não encontrado"
                return result
            
            migrated_files = 0
            total_size = 0
            
            # Procurar por arquivos de atestado
            for file_path in old_path_obj.rglob('*'):
                if self._is_attestation_file(file_path):
                    # Organizar por data de migração
                    migration_date = datetime.now().strftime('%Y-%m')
                    dest_dir = self.base_path / 'migrated' / migration_date
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    
                    dest_path = dest_dir / file_path.name
                    if not dest_path.exists():
                        import shutil
                        shutil.copy2(file_path, dest_path)
                        migrated_files += 1
                        total_size += file_path.stat().st_size
                        logger.info(f"Atestado migrado: {file_path} -> {dest_path}")
            
            result['migrated_files'] = migrated_files
            result['total_size'] = total_size
            
            if migrated_files > 0:
                result['success'] = True
                result['message'] = f"Migração concluída: {migrated_files} arquivos migrados"
            else:
                result['message'] = "Nenhum arquivo encontrado para migração"
            
        except Exception as e:
            logger.error(f"Erro na migração: {str(e)}")
            result['errors'].append(str(e))
            result['message'] = f"Erro na migração: {str(e)}"
        
        return result
    
    def _is_attestation_file(self, file_path: Path) -> bool:
        """Verifica se o arquivo é um atestado"""
        if not file_path.is_file():
            return False
        
        if file_path.suffix.lower() not in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx']:
            return False
        
        filename = file_path.name.lower()
        return 'atestado' in filename or 'attestation' in filename

# Função para obter instância do serviço
def get_local_attestation_service():
    """Retorna uma instância do serviço de atestados local"""
    return LocalAttestationService()
