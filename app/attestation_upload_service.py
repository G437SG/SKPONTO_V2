# -*- coding: utf-8 -*-
"""
Serviço de Upload de Atestados - Sistema Local
Substitui o sistema Dropbox por armazenamento local
"""

import os
import logging
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from datetime import datetime
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from flask import current_app

from app.models import User, MedicalAttestation, db
from app.constants import ALLOWED_DOCUMENT_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS
from app.local_attestation_service import LocalAttestationService

logger = logging.getLogger(__name__)

class AttestationUploadService:
    """Serviço para upload e gerenciamento de atestados médicos usando sistema local"""
    
    def __init__(self):
        self.local_service = LocalAttestationService()
        self.allowed_extensions = ALLOWED_DOCUMENT_EXTENSIONS | ALLOWED_IMAGE_EXTENSIONS
    
    def is_allowed_file(self, filename: str) -> bool:
        """Verifica se o arquivo tem extensão permitida"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_and_upload_attestation(self, 
                                  file: FileStorage, 
                                  attestation: MedicalAttestation, 
                                  user: User) -> Tuple[bool, str]:
        """
        Salva arquivo localmente
        
        Args:
            file: Arquivo enviado
            attestation: Objeto MedicalAttestation
            user: Usuário que fez o upload
            
        Returns:
            Tuple[bool, str]: (sucesso, caminho_local_ou_erro)
        """
        try:
            if not file or not file.filename or not self.is_allowed_file(file.filename):
                return False, "Arquivo inválido ou extensão não permitida"
            
            # Salvar arquivo localmente
            success, message = self.local_service.upload_attestation(
                file_data=file,
                user_id=user.id,
                attestation_id=attestation.id,
                original_filename=file.filename or "unknown"
            )
            
            if success:
                # Atualizar caminho e nome do arquivo no banco de dados
                attestation.local_path = message  # message contém o caminho
                attestation.arquivo = file.filename  # Preservar nome original
                db.session.commit()
                
                logger.info(f"Atestado salvo localmente: {message}")
                return True, message
            else:
                logger.error(f"Erro ao salvar atestado: {message}")
                return False, message
                
        except Exception as e:
            logger.error(f"Erro no upload de atestado: {str(e)}")
            return False, f"Erro interno: {str(e)}"
    
    def delete_attestation_file(self, attestation: MedicalAttestation) -> Tuple[bool, str]:
        """
        Remove arquivo de atestado do sistema local
        
        Args:
            attestation: Objeto MedicalAttestation
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            if not attestation.local_path:
                return True, "Nenhum arquivo para remover"
            
            success, message = self.local_service.delete_attestation(
                user_id=attestation.user_id,
                attestation_id=attestation.id
            )
            
            if success:
                # Limpar caminho no banco de dados
                attestation.local_path = None
                db.session.commit()
                
                logger.info(f"Atestado removido: {attestation.id}")
                return True, "Arquivo removido com sucesso"
            else:
                logger.error(f"Erro ao remover atestado: {message}")
                return False, message
                
        except Exception as e:
            logger.error(f"Erro ao remover atestado: {str(e)}")
            return False, f"Erro interno: {str(e)}"
    
    def get_attestation_file_path(self, attestation: MedicalAttestation) -> Optional[str]:
        """
        Retorna o caminho local do arquivo de atestado
        
        Args:
            attestation: Objeto MedicalAttestation
            
        Returns:
            Optional[str]: Caminho local do arquivo ou None
        """
        if not attestation.local_path:
            return None
            
        local_path = Path(attestation.local_path)
        if local_path.exists():
            return str(local_path)
        
        logger.warning(f"Arquivo de atestado não encontrado: {attestation.local_path}")
        return None
    
    def list_user_attestations(self, user_id: int) -> List[Dict]:
        """
        Lista atestados do usuário
        
        Args:
            user_id: ID do usuário
            
        Returns:
            List[Dict]: Lista de arquivos de atestado
        """
        try:
            result = self.local_service.get_user_attestations(user_id)
            return result.get('attestations', [])
        except Exception as e:
            logger.error(f"Erro ao listar atestados: {str(e)}")
            return []
    
    def cleanup_orphaned_files(self) -> Tuple[int, int]:
        """
        Remove arquivos órfãos do sistema local
        
        Returns:
            Tuple[int, int]: (arquivos_removidos, arquivos_total)
        """
        try:
            result = self.local_service.cleanup_orphaned_files()
            
            if result['success']:
                logger.info(f"Limpeza concluída: {result['removed_count']} arquivos removidos")
                return result['removed_count'], result['total_files']
            else:
                logger.error(f"Erro na limpeza: {result['error']}")
                return 0, 0
                
        except Exception as e:
            logger.error(f"Erro na limpeza de arquivos órfãos: {str(e)}")
            return 0, 0
    
    def get_storage_stats(self) -> Dict:
        """
        Retorna estatísticas de armazenamento
        
        Returns:
            Dict: Estatísticas de uso de armazenamento
        """
        try:
            result = self.local_service.get_storage_statistics()
            return result
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {
                'total_files': 0,
                'total_size': 0,
                'users_with_attestations': 0,
                'oldest_file': None,
                'newest_file': None
            }
    
    def migrate_from_old_system(self, user_id: int) -> Dict:
        """
        Migra dados de sistemas antigos para o local
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Dict: Resultado da migração
        """
        try:
            # Buscar atestados do usuário que ainda têm referências antigas
            attestations = MedicalAttestation.query.filter_by(
                user_id=user_id
            ).filter(
                MedicalAttestation.local_path.is_(None)
            ).all()
            
            migrated_count = 0
            errors = []
            
            for attestation in attestations:
                try:
                    # Tentar encontrar arquivo no sistema antigo
                    if attestation.arquivo:
                        # Procurar em possíveis localizações antigas
                        old_paths = [
                            Path(current_app.root_path).parent / 'uploads' / attestation.arquivo,
                            Path(current_app.root_path).parent / 'temp' / attestation.arquivo,
                            Path(current_app.root_path).parent / 'shared_storage' / attestation.arquivo
                        ]
                        
                        for old_path in old_paths:
                            if old_path.exists():
                                # Migrar para sistema local
                                new_path = self.local_service.storage_dirs['attestations'] / f"user_{user_id}" / attestation.arquivo
                                new_path.parent.mkdir(parents=True, exist_ok=True)
                                
                                # Copiar arquivo
                                import shutil
                                shutil.copy2(old_path, new_path)
                                
                                # Atualizar banco de dados
                                attestation.local_path = str(new_path)
                                db.session.commit()
                                
                                migrated_count += 1
                                logger.info(f"Atestado migrado: {attestation.id}")
                                break
                                
                except Exception as e:
                    errors.append(f"Erro ao migrar atestado {attestation.id}: {str(e)}")
                    continue
            
            return {
                'success': True,
                'migrated_count': migrated_count,
                'errors': errors,
                'message': f"Migração concluída: {migrated_count} atestados migrados"
            }
            
        except Exception as e:
            logger.error(f"Erro na migração: {str(e)}")
            return {
                'success': False,
                'migrated_count': 0,
                'errors': [str(e)],
                'message': f"Erro na migração: {str(e)}"
            }
    
    def upload_attestation_file(self, file_path: str, user_id: int, attestation_id: int) -> Tuple[bool, str]:
        """
        Faz upload de um arquivo de atestado a partir de um caminho
        
        Args:
            file_path: Caminho do arquivo
            user_id: ID do usuário
            attestation_id: ID do atestado
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            if not os.path.exists(file_path):
                return False, "Arquivo não encontrado"
            
            filename = os.path.basename(file_path)
            
            # Simular FileStorage para usar o método existente
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            success, message = self.local_service.upload_attestation(
                file_data=file_data,
                user_id=user_id,
                attestation_id=attestation_id,
                original_filename=filename
            )
            
            return success, message
            
        except Exception as e:
            logger.error(f"Erro no upload de arquivo: {str(e)}")
            return False, f"Erro interno: {str(e)}"

    def get_local_statistics(self) -> Dict:
        """
        Retorna estatísticas dos atestados armazenados localmente
        """
        try:
            stats = {
                'total_attestations': 0,
                'total_users': 0,
                'total_files_size': 0,
                'files_by_type': {},
                'recent_uploads': 0,
                'storage_used': '0 MB'
            }
            
            # Buscar todas as atestações do banco
            attestations = MedicalAttestation.query.all()
            stats['total_attestations'] = len(attestations)
            
            # Contar usuários únicos com atestações
            users_with_attestations = set()
            
            # Analisar arquivos locais
            for attestation in attestations:
                if attestation.user_id:
                    users_with_attestations.add(attestation.user_id)
                
                # Tentar obter caminho do arquivo
                file_path = self.get_attestation_file_path(attestation)
                if file_path and os.path.exists(file_path):
                    try:
                        file_size = os.path.getsize(file_path)
                        stats['total_files_size'] += file_size
                        
                        # Analisar extensão do arquivo
                        ext = Path(file_path).suffix.lower()
                        if ext in stats['files_by_type']:
                            stats['files_by_type'][ext] += 1
                        else:
                            stats['files_by_type'][ext] = 1
                            
                        # Contar uploads recentes (últimos 30 dias)
                        if attestation.upload_date:
                            now = datetime.now()
                            days_diff = now - attestation.upload_date
                            if days_diff.days <= 30:
                                stats['recent_uploads'] += 1
                                
                    except OSError:
                        continue
            
            stats['total_users'] = len(users_with_attestations)
            
            # Formatar tamanho total
            if stats['total_files_size'] > 0:
                size = stats['total_files_size']
                if size >= 1024 * 1024 * 1024:  # GB
                    gb_size = size / (1024 * 1024 * 1024)
                    stats['storage_used'] = f"{gb_size:.1f} GB"
                elif size >= 1024 * 1024:  # MB
                    mb_size = size / (1024 * 1024)
                    stats['storage_used'] = f"{mb_size:.1f} MB"
                else:  # KB
                    stats['storage_used'] = f"{size / 1024:.1f} KB"
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas locais: {str(e)}")
            return {
                'total_attestations': 0,
                'total_users': 0,
                'total_files_size': 0,
                'files_by_type': {},
                'recent_uploads': 0,
                'storage_used': '0 MB',
                'error': str(e)
            }

    def get_users_with_attestations(self) -> List[Dict]:
        """
        Retorna lista de usuários que têm atestações com informações detalhadas
        """
        try:
            users_data = []
            
            # Buscar usuários com atestações
            users_with_attestations = db.session.query(User).join(
                MedicalAttestation, User.id == MedicalAttestation.user_id
            ).distinct().all()
            
            for user in users_with_attestations:
                user_attestations = MedicalAttestation.query.filter_by(
                    user_id=user.id).all()
                
                user_info = {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'total_attestations': len(user_attestations),
                    'files_count': 0,
                    'total_size': 0,
                    'last_upload': None,
                    'files': []
                }
                
                # Analisar arquivos do usuário
                for attestation in user_attestations:
                    file_path = self.get_attestation_file_path(attestation)
                    filename = (attestation.file_path or 
                                'Arquivo não encontrado')
                    upload_date = None
                    if attestation.upload_date:
                        upload_date = attestation.upload_date.isoformat()
                        
                    file_info = {
                        'id': attestation.id,
                        'filename': filename,
                        'upload_date': upload_date,
                        'size': 0,
                        'exists': False
                    }
                    
                    if file_path and os.path.exists(file_path):
                        try:
                            file_size = os.path.getsize(file_path)
                            file_info['size'] = file_size
                            file_info['exists'] = True
                            user_info['files_count'] += 1
                            user_info['total_size'] += file_size
                            
                            # Atualizar último upload
                            if attestation.upload_date:
                                if not user_info['last_upload'] or attestation.upload_date > datetime.fromisoformat(user_info['last_upload']):
                                    user_info['last_upload'] = attestation.upload_date.isoformat()
                                    
                        except OSError:
                            pass
                    
                    user_info['files'].append(file_info)
                
                users_data.append(user_info)
            
            # Ordenar por quantidade de atestações (decrescente)
            users_data.sort(key=lambda x: x['total_attestations'], reverse=True)
            
            return users_data
            
        except Exception as e:
            logger.error(f"Erro ao obter usuários com atestações: {str(e)}")
            return []

    def get_download_link(self, attestation: MedicalAttestation) -> Tuple[bool, str]:
        """
        Gera link de download para um atestado médico
        
        Args:
            attestation: Objeto MedicalAttestation
            
        Returns:
            Tuple[bool, str]: (sucesso, url_download_ou_erro)
        """
        try:
            # Verificar se o atestado tem arquivo associado
            if not attestation.local_path:
                return False, "Atestado não possui arquivo associado"
            
            # Verificar se o arquivo existe fisicamente
            file_path = self.get_attestation_file_path(attestation)
            if not file_path or not os.path.exists(file_path):
                return False, "Arquivo não encontrado no sistema"
            
            # Para sistema local, retornar a URL da rota de download de atestados
            from flask import url_for
            
            # Usar a rota de download que já existe e funciona
            download_url = url_for('main.download_atestado', id=attestation.id)
            
            return True, download_url
            
        except Exception as e:
            logger.error(f"Erro ao gerar link de download para atestado {attestation.id}: {str(e)}")
            return False, f"Erro interno: {str(e)}"
