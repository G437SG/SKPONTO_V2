# -*- coding: utf-8 -*-
"""
SKPONTO - Gerenciador de Pasta Compartilhada
Sistema que gerencia automaticamente a estrutura de pastas compartilhadas
(local, Google Drive, OneDrive, etc.)
"""

import os
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from urllib.parse import urlparse, parse_qs

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SharedFolderManager:
    """Gerenciador de pasta compartilhada universal"""
    
    def __init__(self, shared_link: str = None):
        self.shared_link = shared_link
        self.provider = None
        self.local_base_path = None
        self.folder_structure = {
            'database': 'database',
            'backups': 'backups',
            'uploads': 'uploads',
            'atestados': 'uploads/atestados',
            'profiles': 'uploads/profiles',
            'logs': 'logs',
            'reports': 'reports',
            'temp': 'temp',
            'exports': 'exports'
        }
        
        if shared_link:
            self._detect_provider()
            # Não criar pasta automaticamente - apenas quando explicitamente solicitado
    
    def _detect_provider(self) -> str:
        """Detecta o provedor da pasta compartilhada"""
        if not self.shared_link:
            return None
        
        url_lower = self.shared_link.lower()
        
        if 'local.com' in url_lower:
            self.provider = 'local'
        elif 'drive.google.com' in url_lower:
            self.provider = 'google_drive'
        elif 'onedrive.live.com' in url_lower or '1drv.ms' in url_lower:
            self.provider = 'onedrive'
        elif 'mega.nz' in url_lower:
            self.provider = 'mega'
        elif 'box.com' in url_lower:
            self.provider = 'box'
        else:
            self.provider = 'generic'
        
        logger.info(f"Provedor detectado: {self.provider}")
        return self.provider
    
    def _setup_local_path(self):
        """Configura o caminho local baseado no provedor"""
        # Criar pasta local para sincronização
        app_root = Path(__file__).parent.parent
        self.local_base_path = app_root / 'shared_storage' / 'SKPONTO_Data'
        
        # Garantir que a pasta existe
        self.local_base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Pasta local configurada: {self.local_base_path}")
    
    def create_folder_structure(self) -> Dict[str, str]:
        """Cria a estrutura completa de pastas"""
        if not self.local_base_path:
            if not self.shared_link:
                raise ValueError("Shared link necessário para configurar pasta base")
            self._setup_local_path()
        
        created_folders = {}
        
        for folder_name, folder_path in self.folder_structure.items():
            full_path = self.local_base_path / folder_path
            
            try:
                full_path.mkdir(parents=True, exist_ok=True)
                created_folders[folder_name] = str(full_path)
                logger.info(f"Pasta criada: {folder_name} -> {full_path}")
            except Exception as e:
                logger.error(f"Erro ao criar pasta {folder_name}: {e}")
                raise
        
        # Criar arquivo de configuração
        self._create_config_file(created_folders)
        
        # Criar arquivo README
        self._create_readme_file()
        
        return created_folders
    
    def _create_config_file(self, folders: Dict[str, str]):
        """Cria arquivo de configuração com os caminhos das pastas"""
        config_content = f"""# SKPONTO - Configuração de Pastas Compartilhadas
# Gerado automaticamente em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Informações da Pasta Compartilhada
SHARED_LINK={self.shared_link}
PROVIDER={self.provider}
LOCAL_BASE_PATH={self.local_base_path}

# Caminhos das Pastas
"""
        
        for folder_name, folder_path in folders.items():
            config_content += f"{folder_name.upper()}_PATH={folder_path}\n"
        
        config_file = self.local_base_path / 'skponto_config.txt'
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        logger.info(f"Arquivo de configuração criado: {config_file}")
    
    def _create_readme_file(self):
        """Cria arquivo README com instruções"""
        readme_content = f"""# SKPONTO - Sistema de Controle de Ponto
## Estrutura de Pastas Compartilhadas

**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Provedor:** {self.provider.upper() if self.provider else 'N/A'}
**Link:** {self.shared_link}

### Estrutura de Pastas:

📁 **database/** - Banco de dados SQLite
   - skponto.db - Banco principal
   - skponto.db.backup_* - Backups automáticos

📁 **backups/** - Backups completos do sistema
   - skponto_backup_YYYYMMDD_HHMMSS.zip

📁 **uploads/** - Arquivos enviados pelos usuários
   - 📁 **atestados/** - Atestados médicos
   - 📁 **profiles/** - Fotos de perfil

📁 **logs/** - Logs do sistema
   - security.log - Logs de segurança
   - application.log - Logs da aplicação
   - backup.log - Logs de backup

📁 **reports/** - Relatórios gerados
   - Relatórios em PDF e Excel

📁 **temp/** - Arquivos temporários
   - Processamento de uploads
   - Arquivos temporários

📁 **exports/** - Exportações de dados
   - Dados exportados pelos usuários

### Instruções de Uso:

1. **Backup Manual:**
   - Os backups são criados automaticamente na pasta `backups/`
   - Faça upload dos arquivos .zip para a pasta compartilhada

2. **Sincronização:**
   - Esta pasta local sincroniza com a pasta compartilhada
   - Todos os dados são armazenados localmente e enviados quando necessário

3. **Segurança:**
   - Mantenha o link da pasta compartilhada seguro
   - Faça backups regulares
   - Monitore os logs de segurança

### Suporte:
- Para problemas técnicos, consulte os logs
- Para configurações, edite o arquivo `skponto_config.txt`
"""
        
        readme_file = self.local_base_path / 'README.md'
        
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"Arquivo README criado: {readme_file}")
    
    def get_folder_paths(self) -> Dict[str, str]:
        """Retorna os caminhos de todas as pastas"""
        if not self.local_base_path:
            return {}
        
        paths = {}
        for folder_name, folder_path in self.folder_structure.items():
            full_path = self.local_base_path / folder_path
            paths[folder_name] = str(full_path)
        
        return paths
    
    def get_database_path(self) -> str:
        """Retorna o caminho do banco de dados"""
        if not self.local_base_path:
            if not self.shared_link:
                return None
            self._setup_local_path()
        
        db_path = self.local_base_path / 'database' / 'skponto.db'
        return str(db_path)
    
    def get_uploads_path(self) -> str:
        """Retorna o caminho da pasta de uploads"""
        if not self.local_base_path:
            return None
        
        uploads_path = self.local_base_path / 'uploads'
        return str(uploads_path)
    
    def get_backups_path(self) -> str:
        """Retorna o caminho da pasta de backups"""
        if not self.local_base_path:
            return None
        
        backups_path = self.local_base_path / 'backups'
        return str(backups_path)
    
    def get_logs_path(self) -> str:
        """Retorna o caminho da pasta de logs"""
        if not self.local_base_path:
            return None
        
        logs_path = self.local_base_path / 'logs'
        return str(logs_path)
    
    def validate_shared_link(self, link: str) -> Tuple[bool, str]:
        """Valida se o link compartilhado é válido"""
        if not link:
            return False, "Link não fornecido"
        
        # Verificar se é uma URL válida
        try:
            parsed = urlparse(link)
            if not parsed.scheme or not parsed.netloc:
                return False, "Link inválido - deve ser uma URL completa"
        except Exception:
            return False, "Link inválido - formato incorreto"
        
        # Verificar provedores suportados
        supported_providers = [
            'local.com', 'drive.google.com', 'onedrive.live.com', 
            '1drv.ms', 'mega.nz', 'box.com'
        ]
        
        url_lower = link.lower()
        is_supported = any(provider in url_lower for provider in supported_providers)
        
        if not is_supported:
            return False, f"Provedor não suportado. Suportados: {', '.join(supported_providers)}"
        
        return True, "Link válido"
    
    def create_backup_instructions(self, backup_file: str) -> str:
        """Cria instruções detalhadas para upload manual"""
        instructions = f"""
# SKPONTO - Instruções de Upload Manual
## Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Arquivo de Backup: {backup_file}

### Instruções Passo a Passo:

#### 1. **Localizar o Arquivo:**
   - Arquivo: `{backup_file}`
   - Localização: `{self.local_base_path / 'backups'}`

#### 2. **Acessar a Pasta Compartilhada:**
   - Link: {self.shared_link}
   - Provedor: {self.provider.upper() if self.provider else 'N/A'}

#### 3. **Estrutura de Pastas na Nuvem:**
   - Criar pasta `SKPONTO_Data` (se não existir)
   - Dentro dela, criar pasta `backups`
   - Estrutura final: `SKPONTO_Data/backups/`

#### 4. **Fazer Upload:**
   - Arraste o arquivo `{backup_file}` para a pasta `backups/`
   - Aguarde o upload completar
   - Verifique se o arquivo foi enviado corretamente

#### 5. **Verificação:**
   - Confirme que o arquivo está na pasta compartilhada
   - Tamanho do arquivo deve ser consistente
   - Data/hora do upload deve estar correta

### Dicas:
- **Internet:** Certifique-se de ter uma conexão estável
- **Espaço:** Verifique se há espaço suficiente na nuvem
- **Backup:** Mantenha uma cópia local até confirmar o upload
- **Organização:** Mantenha apenas os últimos 10 backups na nuvem

### Estrutura Completa Recomendada:
```
SKPONTO_Data/
├── database/
│   └── skponto.db
├── backups/
│   ├── {backup_file}
│   └── ...outros backups...
├── uploads/
│   ├── atestados/
│   └── profiles/
├── logs/
├── reports/
├── temp/
└── exports/
```

### Problemas Comuns:
- **Upload lento:** Aguarde, pode demorar com arquivos grandes
- **Erro de espaço:** Libere espaço na conta da nuvem
- **Pasta não encontrada:** Crie a estrutura manualmente
- **Permissões:** Certifique-se de ter acesso de escrita

### Próximos Passos:
1. Faça o upload seguindo as instruções acima
2. Verifique se o arquivo foi enviado corretamente
3. Mantenha este arquivo para referência futura
4. Para backups automáticos, configure a sincronização

---
**SKPONTO Sistema de Controle de Ponto**
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Salvar instruções em arquivo
        instructions_file = self.local_base_path / 'temp' / f'upload_instructions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        instructions_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(instructions)
        
        logger.info(f"Instruções de upload criadas: {instructions_file}")
        
        return str(instructions_file)
    
    def cleanup_old_files(self, days_to_keep: int = 30):
        """Limpa arquivos antigos das pastas temporárias"""
        if not self.local_base_path:
            return
        
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Limpar pasta temp
        temp_path = self.local_base_path / 'temp'
        if temp_path.exists():
            for file_path in temp_path.glob('*'):
                try:
                    file_stat = file_path.stat()
                    file_date = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    if file_date < cutoff_date:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                        logger.info(f"Arquivo antigo removido: {file_path}")
                except Exception as e:
                    logger.error(f"Erro ao remover arquivo {file_path}: {e}")
    
    def get_storage_stats(self) -> Dict[str, dict]:
        """Retorna estatísticas de armazenamento das pastas"""
        if not self.local_base_path:
            return {}
        
        stats = {}
        
        for folder_name, folder_path in self.folder_structure.items():
            full_path = self.local_base_path / folder_path
            
            if full_path.exists():
                file_count = 0
                total_size = 0
                
                try:
                    for file_path in full_path.rglob('*'):
                        if file_path.is_file():
                            file_count += 1
                            total_size += file_path.stat().st_size
                    
                    stats[folder_name] = {
                        'path': str(full_path),
                        'file_count': file_count,
                        'total_size': total_size,
                        'size_mb': round(total_size / (1024 * 1024), 2),
                        'exists': True
                    }
                except Exception as e:
                    stats[folder_name] = {
                        'path': str(full_path),
                        'error': str(e),
                        'exists': False
                    }
            else:
                stats[folder_name] = {
                    'path': str(full_path),
                    'exists': False
                }
        
        return stats

# Função de conveniência para uso em outras partes do sistema
def get_shared_folder_manager(shared_link: str = None) -> SharedFolderManager:
    """Retorna uma instância do gerenciador de pasta compartilhada"""
    return SharedFolderManager(shared_link)

# Função para validar link compartilhado
def validate_shared_link(link: str) -> Tuple[bool, str]:
    """Valida um link compartilhado"""
    manager = SharedFolderManager()
    return manager.validate_shared_link(link)
