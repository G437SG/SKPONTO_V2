import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config

# Carregar variáveis de ambiente do arquivo .env
from dotenv import load_dotenv
load_dotenv()

# Imports opcionais para funcionalidades adicionais
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    HAS_LIMITER = True
except ImportError:
    HAS_LIMITER = False

try:
    from flask_compress import Compress
    HAS_COMPRESS = True
except ImportError:
    HAS_COMPRESS = False

# Importar sistema de erros
from app.error_handler import AdvancedErrorHandler

# Sistema de horas extras será importado dinamicamente

# Inicialização das extensões
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
error_handler = AdvancedErrorHandler()

# Inicializar extensões opcionais apenas se disponíveis
if HAS_LIMITER:
    limiter = Limiter(key_func=get_remote_address)
else:
    limiter = None

if HAS_COMPRESS:
    compress = Compress()
else:
    compress = None

def configure_extensions(app):
    """Configura as extensões Flask"""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Inicializar sistema de erros
    error_handler.init_app(app)
    
    # Inicializar extensões opcionais apenas se disponíveis
    if HAS_LIMITER and limiter:
        limiter.init_app(app)
    if HAS_COMPRESS and compress:
        compress.init_app(app)

def configure_login_manager(app):
    """Configura o Flask-Login"""
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'

def create_directories(app):
    """Cria diretórios necessários"""
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, 'backups'), exist_ok=True)

def register_blueprints(app):
    """Registra os blueprints da aplicação"""
    from app.main import bp as main_bp
    from app.auth import bp as auth_bp
    from app.admin import bp as admin_bp
    from app.api import bp as api_bp
    from app.errors import bp as errors_bp
    from app.files import bp as files_bp
    
    # Registrar blueprint do dashboard de erros
    from app.error_dashboard import error_dashboard
    
    # Registrar blueprint do dashboard de backup
    from app.admin.backup import bp as backup_bp
    
    # Registrar blueprint do sistema de debug
    from app.debug_blueprint import bp as debug_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)  # Sem prefixo para /login funcionar
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(errors_bp)
    app.register_blueprint(files_bp, url_prefix='/files')
    app.register_blueprint(error_dashboard)  # Dashboard de erros
    app.register_blueprint(backup_bp,
                           url_prefix='/admin/backup')  # Dashboard de backup
    app.register_blueprint(debug_bp,
                           url_prefix='/admin/debug')  # Sistema de debug


def register_cli_commands(app):
    """Registra comandos CLI personalizados"""
    from app.cli import register_cli_commands
    register_cli_commands(app)

def format_hours_decimal(hours_decimal):
    """Converte horas decimais para formato legível"""
    # Separar horas e minutos
    hours = int(hours_decimal)
    minutes = int((hours_decimal - hours) * 60)
    
    # Formatar resultado
    result = []
    if hours > 0:
        result.append(f'{hours}h')
    if minutes > 0:
        result.append(f'{minutes}min')
    
    # Se não há horas nem minutos válidos, retornar apenas minutos
    if not result:
        # Para valores muito pequenos, mostrar em minutos
        total_minutes = int(hours_decimal * 60)
        if total_minutes > 0:
            return f'{total_minutes}min'
        else:
            return '0min'
    
    return ' '.join(result)

def configure_template_filters(app):
    """Configura filtros personalizados do Jinja2"""
    @app.template_filter('datetime')
    def datetime_filter(value, format='%d/%m/%Y %H:%M'):
        if value is None:
            return ''
        from app.utils import format_datetime_br
        return format_datetime_br(value)
    
    @app.template_filter('date')
    def date_filter(value, format='%d/%m/%Y'):
        if value is None:
            return ''
        from app.utils import format_date_br
        return format_date_br(value)
    
    @app.template_filter('time')
    def time_filter(value, format='%H:%M'):
        if value is None:
            return ''
        from app.utils import format_time_br
        return format_time_br(value)
    
    @app.template_filter('format_hours')
    def format_hours_filter(value):
        """Formata horas decimais para formato legível (ex: 1.5 -> '1h 30min')"""
        if value is None or value == 0:
            return '0min'
        
        # Converter para float se necessário
        try:
            hours_decimal = float(value)
        except (ValueError, TypeError):
            return str(value)
        
        return format_hours_decimal(hours_decimal)

def configure_template_context(app):
    """Configura contexto global dos templates"""
    @app.context_processor
    def inject_moment():
        from datetime import datetime
        return {
            'moment': datetime.now,
            'datetime': datetime
        }

def configure_context_processors(app):
    """Configura processadores de contexto"""
    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return {'current_user': current_user}

def configure_security_headers(app):
    """Configura headers de segurança"""
    @app.after_request
    def set_security_headers(response):
        # Headers de segurança básicos
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # HTTPS em produção
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # CSP básico
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        
        return response

def create_app(config_name=None):
    """Factory para criar a aplicação Flask"""
    app = Flask(__name__)
    
    # Configuração
    config_name = config_name or os.environ.get('FLASK_CONFIG', 'default')
    app.config.from_object(config[config_name])
    
    # Sistema de armazenamento local
    print("📂 Usando sistema de armazenamento local")
    print("   Database URI: " + str(app.config['SQLALCHEMY_DATABASE_URI']))
    
    # Configurar componentes
    configure_extensions(app)
    configure_login_manager(app)
    create_directories(app)
    register_blueprints(app)
    register_cli_commands(app)
    # Configurar filtros e contexto dos templates
    configure_template_filters(app)
    configure_template_context(app)
    configure_context_processors(app)
    # Configurar headers de segurança
    configure_security_headers(app)

    # Configurar sistema de debug
    try:
        from app.debug_system import DebugLogger
        debug_logger = DebugLogger()
        app.debug_logger = debug_logger
        app.logger.info("Sistema de debug inicializado com sucesso")
    except Exception as e:
        app.logger.warning(f"Erro ao inicializar sistema de debug: {str(e)}")

    # Configurar armazenamento local
    with app.app_context():
        try:
            from app.local_storage_manager import LocalStorageManager
            LocalStorageManager()  # Inicializa o sistema de armazenamento
            app.logger.info("Sistema de armazenamento local configurado com sucesso")
        except Exception as e:
            app.logger.warning(f"Aviso ao configurar armazenamento local: {str(e)}")
    
    # Configurar agendador de backup
    try:
        from backup_scheduler import init_scheduler
        init_scheduler(app)
        app.logger.info("Agendador de backup inicializado")
    except Exception as e:
        app.logger.warning(f"Aviso ao inicializar agendador de backup: {str(e)}")
    
    # Configurar sistema de horas extras
    try:
        from app.overtime_controller import OvertimeController
        overtime_controller = OvertimeController()
        app.logger.info("Sistema de horas extras inicializado com sucesso")
    except ImportError as e:
        app.logger.warning(f"Sistema de horas extras não encontrado: {str(e)}")
    except Exception as e:
        app.logger.warning(f"Erro ao inicializar sistema de horas extras: {str(e)}")
    
    # Configurar filtros personalizados de template
    try:
        from app.template_filters import init_filters
        init_filters(app)
        app.logger.info("Filtros de template inicializados")
    except Exception as e:
        app.logger.warning(f"Erro ao inicializar filtros de template: {str(e)}")
    
    return app

# User loader para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from app.models import User, UserType
    from app.constants import ADMIN_EMAIL
    user = User.query.get(int(user_id))
    # Ensure hardcoded admin is always recognized
    if user and user.email == ADMIN_EMAIL:
        user.user_type = UserType.ADMIN
        user.is_active = True
    return user
