import os
import secrets
from datetime import timedelta

class Config:
    """Configuração base da aplicação"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Environment configuration
    ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Database configuration
    base_dir = os.path.abspath(os.path.dirname(__file__))
    storage_dir = os.path.join(base_dir, 'storage', 'database')
    
    # Criar diretório se não existir
    os.makedirs(storage_dir, exist_ok=True)
    
    # FORÇAR PostgreSQL em produção
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Definir PostgreSQL como padrão
        database_url = 'postgresql://skponto_user:ho8BpKkpG7dBMP7qGygnSP9G5vQd3FzF@dpg-d1rq11vgi27c73cm8oj0-a.oregon-postgres.render.com/skponto_production'
        os.environ['DATABASE_URL'] = database_url
        print("🔧 CONFIGURADO DATABASE_URL padrão para PostgreSQL")
    
    SQLALCHEMY_DATABASE_URI = database_url
    print(f"🗄️ POSTGRESQL MODE - URI: {database_url[:50]}...")
    print("🚀 USANDO POSTGRESQL PARA PRODUÇÃO")
    
    # Fix for PostgreSQL URL format
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
        print(f"🔧 URL PostgreSQL corrigida: {SQLALCHEMY_DATABASE_URI[:60]}...")
    
    # Driver selection based on Python version and availability
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgresql://'):
        import sys
        try:
            # Try psycopg2 for compatibility
            import psycopg2
            if '+psycopg2' not in SQLALCHEMY_DATABASE_URI:
                SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgresql://', 'postgresql+psycopg2://', 1)
                print(f"✅ Driver psycopg2 configurado")
        except ImportError:
            try:
                # Fallback to psycopg3 if available
                import psycopg
                if '+psycopg' not in SQLALCHEMY_DATABASE_URI:
                    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgresql://', 'postgresql+psycopg://', 1)
                    print(f"✅ Driver psycopg3 configurado")
            except ImportError:
                print("⚠️ Nenhum driver PostgreSQL encontrado!")
                # Se não há drivers, usar SQLite como fallback apenas em desenvolvimento
                if ENV == 'development':
                    db_path = os.path.join(storage_dir, "skponto.db")
                    SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
                    print(f"⚠️ FALLBACK para SQLite: {SQLALCHEMY_DATABASE_URI}")
                else:
                    raise ImportError("Driver PostgreSQL necessário para produção!")
                    print(f"🐍 Python {sys.version_info.major}.{sys.version_info.minor} - Usando psycopg3")
            else:
                # Use psycopg2 for older Python versions
                import psycopg2
                print(f"🐍 Python {sys.version_info.major}.{sys.version_info.minor} - Usando psycopg2")
        except ImportError as e:
            print(f"⚠️ Driver import warning: {e}")
            # Let SQLAlchemy use default driver
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # Security
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'True').lower() == 'true'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # Upload settings - Configuração LOCAL
    UPLOAD_FOLDER = os.path.join(base_dir, 'storage', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx'}
    
    # Configurações de armazenamento local
    STORAGE_BASE_PATH = os.path.join(base_dir, 'storage')
    ATTESTATIONS_PATH = os.path.join(STORAGE_BASE_PATH, 'attestations')
    BACKUPS_PATH = os.path.join(STORAGE_BASE_PATH, 'backups')
    LOGS_PATH = os.path.join(STORAGE_BASE_PATH, 'logs')
    
    # Criar diretórios de armazenamento
    for storage_path in [ATTESTATIONS_PATH, BACKUPS_PATH, LOGS_PATH]:
        os.makedirs(storage_path, exist_ok=True)
    
    # Timezone
    TIMEZONE = os.environ.get('TIMEZONE', 'America/Sao_Paulo')
    
    # Sistema de backup local
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    BACKUP_SCHEDULE = os.environ.get('BACKUP_SCHEDULE', 'daily')
    LOCAL_BACKUP_ENABLED = True
    
    # Configurações de backup automático
    AUTO_BACKUP_ENABLED = os.environ.get('AUTO_BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_FREQUENCY_HOURS = int(os.environ.get('BACKUP_FREQUENCY_HOURS', 24))
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # GitHub Integration (opcional)
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
    GITHUB_BACKUP_REPO = os.environ.get('GITHUB_BACKUP_REPO')

class ProductionConfig(Config):
    """Configuração de produção"""
    DEBUG = False
    TESTING = False
    
    # Force HTTPS in production
    SESSION_COOKIE_SECURE = True
    
    # Production database optimizations
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }

class DevelopmentConfig(Config):
    """Configuração de desenvolvimento"""
    DEBUG = True
    # Usar o mesmo banco unificado em desenvolvimento
    # SQLALCHEMY_DATABASE_URI = herdado da classe Config

class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Banco em memória para testes
    WTF_CSRF_ENABLED = False  # Desabilitar CSRF para testes
    SERVER_NAME = 'localhost.localdomain'
    SECRET_KEY = 'test-secret-key'
    UPLOAD_FOLDER = 'test_uploads'
    
    # Configurações de segurança para testes
    SESSION_COOKIE_SECURE = False
    LOGIN_DISABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
