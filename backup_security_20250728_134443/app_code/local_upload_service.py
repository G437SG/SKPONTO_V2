# -*- coding: utf-8 -*-
"""
Serviço de Upload Local para SKPONTO
Gerencia uploads de arquivos usando armazenamento local
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Tuple, Optional, List
from werkzeug.utils import secure_filename
from flask import current_app
from app.utils import log_security_event
from app.constants import SECURITY_ACTION_UPLOAD_ATTESTATION

logger = logging.getLogger(__name__)

class LocalUploadService:
    """Serviço de upload local para atestados e arquivos"""
    
    def __init__(self):
        self.base_path = Path(current_app.root_path).parent / 'storage'
        self.attestations_path = self.base_path / 'attestations'
        self.uploads_path = self.base_path / 'uploads'
        self.temp_path = self.base_path / 'temp'
        
        # Criar diretórios se não existirem
        self._ensure_directories()
        
        # Configurações
        self.allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {
            'pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx'
        })
        self.max_file_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    
    def _ensure_directories(self):
        """Garante que todos os diretórios necessários existem"""
        for path in [self.attestations_path, self.uploads_path, self.temp_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def _allowed_file(self, filename: str) -> bool:
        """Verifica se a extensão do arquivo é permitida"""
        return ('.' in filename and 
                filename.rsplit('.', 1)[1].lower() in self.allowed_extensions)
    
    def _get_file_size(self, file_path: Path) -> int:
        """Retorna o tamanho do arquivo em bytes"""
        return file_path.stat().st_size if file_path.exists() else 0
    
    def upload_attestation(self, file_data, user_id: int, attestation_id: int,
                          original_filename: str) -> Tuple[bool, str]:
        """
        Faz upload de um atestado médico
        
        Args:
            file_data: Dados do arquivo (werkzeug.FileStorage)
            user_id: ID do usuário
            attestation_id: ID do atestado
            original_filename: Nome original do arquivo
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem/caminho)
        """
        try:
            # Validar arquivo
            if not original_filename or not self._allowed_file(original_filename):
                return False, "Tipo de arquivo não permitido"
            
            # Criar estrutura de diretórios por usuário
            user_dir = self.attestations_path / f"user_{user_id}"
            user_dir.mkdir(exist_ok=True)
            
            # Gerar nome seguro do arquivo
            secure_name = secure_filename(original_filename)
            final_filename = f"attestation_{attestation_id}_{secure_name}"
            final_path = user_dir / final_filename
            
            # Verificar tamanho do arquivo
            file_data.seek(0, 2)  # Ir para o final
            file_size = file_data.tell()
            file_data.seek(0)  # Voltar ao início
            
            if file_size > self.max_file_size:
                return False, f"Arquivo muito grande. Máximo: {self.max_file_size / (1024*1024):.1f}MB"
            
            # Salvar arquivo
            file_data.save(str(final_path))
            
            # Verificar se foi salvo corretamente
            if not final_path.exists():
                return False, "Erro ao salvar arquivo"
            
            # Log de segurança
            log_security_event(
                user_id,
                SECURITY_ACTION_UPLOAD_ATTESTATION,
                f"Atestado enviado: {final_filename} ({file_size} bytes)"
            )
            
            logger.info(f"Atestado enviado: {final_path} ({file_size} bytes)")
            return True, str(final_path)
            
        except Exception as e:
            logger.error(f"Erro ao fazer upload de atestado: {str(e)}")
            return False, f"Erro ao fazer upload: {str(e)}"
    
    def upload_general_file(self, file_data, user_id: int, 
                           original_filename: str, category: str = "general") -> Tuple[bool, str]:
        """
        Faz upload de um arquivo geral
        
        Args:
            file_data: Dados do arquivo (werkzeug.FileStorage)
            user_id: ID do usuário
            original_filename: Nome original do arquivo
            category: Categoria do arquivo (general, profile, etc.)
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem/caminho)
        """
        try:
            # Validar arquivo
            if not original_filename or not self._allowed_file(original_filename):
                return False, "Tipo de arquivo não permitido"
            
            # Criar estrutura de diretórios
            category_dir = self.uploads_path / category / f"user_{user_id}"
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # Gerar nome seguro do arquivo
            secure_name = secure_filename(original_filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_filename = f"{timestamp}_{secure_name}"
            final_path = category_dir / final_filename
            
            # Verificar tamanho do arquivo
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)
            
            if file_size > self.max_file_size:
                return False, f"Arquivo muito grande. Máximo: {self.max_file_size / (1024*1024):.1f}MB"
            
            # Salvar arquivo
            file_data.save(str(final_path))
            
            # Verificar se foi salvo corretamente
            if not final_path.exists():
                return False, "Erro ao salvar arquivo"
            
            logger.info(f"Arquivo enviado: {final_path} ({file_size} bytes)")
            return True, str(final_path)
            
        except Exception as e:
            logger.error(f"Erro ao fazer upload de arquivo: {str(e)}")
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
            user_dir = self.attestations_path / f"user_{user_id}"
            if not user_dir.exists():
                return False, "Diretório do usuário não encontrado"
            
            # Procurar arquivo do atestado
            attestation_files = list(user_dir.glob(f"attestation_{attestation_id}_*"))
            if not attestation_files:
                return False, "Arquivo de atestado não encontrado"
            
            # Remover arquivo(s)
            for file_path in attestation_files:
                file_path.unlink()
                logger.info(f"Atestado removido: {file_path}")
            
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
            attestation_files = list(user_dir.glob(f"attestation_{attestation_id}_*"))
            if attestation_files:
                return str(attestation_files[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar atestado: {str(e)}")
            return None
    
    def list_user_attestations(self, user_id: int) -> List[dict]:
        """
        Lista todos os atestados de um usuário
        
        Args:
            user_id: ID do usuário
            
        Returns:
            List[dict]: Lista de informações dos atestados
        """
        attestations = []
        
        try:
            user_dir = self.attestations_path / f"user_{user_id}"
            if not user_dir.exists():
                return attestations
            
            # Buscar todos os arquivos de atestado
            attestation_files = list(user_dir.glob("attestation_*"))
            
            for file_path in attestation_files:
                try:
                    # Extrair ID do atestado do nome do arquivo
                    filename = file_path.name
                    parts = filename.split('_')
                    if len(parts) >= 2:
                        attestation_id = int(parts[1])
                    else:
                        continue
                    
                    file_stats = file_path.stat()
                    attestation_info = {
                        'attestation_id': attestation_id,
                        'filename': filename,
                        'file_path': str(file_path),
                        'file_size': file_stats.st_size,
                        'created_at': datetime.fromtimestamp(file_stats.st_ctime),
                        'modified_at': datetime.fromtimestamp(file_stats.st_mtime)
                    }
                    
                    attestations.append(attestation_info)
                    
                except (ValueError, IndexError):
                    # Pular arquivos com nomes inválidos
                    continue
            
            # Ordenar por data de criação (mais recente primeiro)
            attestations.sort(key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"Erro ao listar atestados do usuário: {str(e)}")
        
        return attestations
    
    def get_storage_usage(self, user_id: Optional[int] = None) -> dict:
        """
        Retorna estatísticas de uso do armazenamento
        
        Args:
            user_id: ID do usuário (se None, retorna estatísticas globais)
            
        Returns:
            dict: Estatísticas de uso
        """
        stats = {
            'total_files': 0,
            'total_size': 0,
            'attestations_count': 0,
            'attestations_size': 0,
            'uploads_count': 0,
            'uploads_size': 0
        }
        
        try:
            if user_id:
                # Estatísticas específicas do usuário
                user_att_dir = self.attestations_path / f"user_{user_id}"
                if user_att_dir.exists():
                    att_files = list(user_att_dir.glob("*"))
                    stats['attestations_count'] = len(att_files)
                    stats['attestations_size'] = sum(f.stat().st_size for f in att_files if f.is_file())
                
                user_upload_dir = self.uploads_path / "general" / f"user_{user_id}"
                if user_upload_dir.exists():
                    upload_files = list(user_upload_dir.glob("*"))
                    stats['uploads_count'] = len(upload_files)
                    stats['uploads_size'] = sum(f.stat().st_size for f in upload_files if f.is_file())
            else:
                # Estatísticas globais
                if self.attestations_path.exists():
                    att_files = list(self.attestations_path.rglob("*"))
                    att_files = [f for f in att_files if f.is_file()]
                    stats['attestations_count'] = len(att_files)
                    stats['attestations_size'] = sum(f.stat().st_size for f in att_files)
                
                if self.uploads_path.exists():
                    upload_files = list(self.uploads_path.rglob("*"))
                    upload_files = [f for f in upload_files if f.is_file()]
                    stats['uploads_count'] = len(upload_files)
                    stats['uploads_size'] = sum(f.stat().st_size for f in upload_files)
            
            stats['total_files'] = stats['attestations_count'] + stats['uploads_count']
            stats['total_size'] = stats['attestations_size'] + stats['uploads_size']
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas de uso: {str(e)}")
        
        return stats
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Remove arquivos temporários antigos
        
        Args:
            max_age_hours: Idade máxima em horas para manter arquivos temporários
        """
        try:
            if not self.temp_path.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            
            for temp_file in self.temp_path.rglob("*"):
                if temp_file.is_file() and temp_file.stat().st_ctime < cutoff_time:
                    temp_file.unlink()
                    logger.info(f"Arquivo temporário removido: {temp_file}")
            
        except Exception as e:
            logger.error(f"Erro ao limpar arquivos temporários: {str(e)}")

# Importar datetime após as outras importações
from datetime import datetime

# Função para obter instância do serviço
def get_local_upload_service():
    """Retorna uma instância do serviço de upload local"""
    return LocalUploadService()
