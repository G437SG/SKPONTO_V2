import os
import uuid
from datetime import datetime, date, time
import pytz
from flask import current_app, request
from werkzeug.utils import secure_filename
import io
from app import db
from app.models import SecurityLog

# Import opcional para processamento de imagens
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def get_brazil_timezone():
    """Retorna o timezone do Brasil"""
    return pytz.timezone(current_app.config.get('TIMEZONE', 'America/Sao_Paulo'))

def get_current_datetime():
    """Retorna datetime atual no timezone do Brasil"""
    return datetime.now(get_brazil_timezone())

def get_current_time():
    """Retorna time atual no timezone do Brasil"""
    return get_current_datetime().time()

def get_current_date():
    """Retorna data atual no timezone do Brasil"""
    return get_current_datetime().date()

def localize_datetime(dt):
    """Localiza um datetime para o timezone do Brasil"""
    if dt is None:
        return None
    
    tz = get_brazil_timezone()
    
    # Se o datetime já tem timezone, converte para o timezone do Brasil
    if dt.tzinfo is not None:
        return dt.astimezone(tz)
    
    # Se não tem timezone, assume que é UTC e converte
    utc_dt = pytz.UTC.localize(dt)
    return utc_dt.astimezone(tz)

def format_datetime_br(dt):
    """Formata datetime para o padrão brasileiro"""
    if dt is None:
        return ""
    
    # Garantir que está no timezone correto
    local_dt = localize_datetime(dt)
    return local_dt.strftime("%d/%m/%Y %H:%M:%S")

def format_date_br(dt):
    """Formata data para o padrão brasileiro"""
    if dt is None:
        return ""
    
    if isinstance(dt, datetime):
        local_dt = localize_datetime(dt)
        return local_dt.strftime("%d/%m/%Y")
    
    return dt.strftime("%d/%m/%Y")

def format_time_br(tm):
    """Formata hora para o padrão brasileiro"""
    if tm is None:
        return ""
    
    if isinstance(tm, datetime):
        local_dt = localize_datetime(tm)
        return local_dt.strftime("%H:%M")
    
    return tm.strftime("%H:%M")

def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file, subfolder=''):
    """Salva arquivo enviado usando a pasta compartilhada configurada"""
    try:
        if not file:
            raise ValueError("Nenhum arquivo foi selecionado")
        
        if not file.filename:
            raise ValueError("Nome do arquivo está vazio")
        
        if not allowed_file(file.filename):
            allowed_exts = current_app.config.get('ALLOWED_EXTENSIONS', ['pdf', 'jpg', 'png', 'jpeg'])
            raise ValueError(f"Tipo de arquivo não permitido. Extensões aceitas: {', '.join(allowed_exts)}")
        
        # Verificar tamanho do arquivo
        file.seek(0, 2)  # Ir para o final do arquivo
        size = file.tell()
        file.seek(0)  # Voltar ao início
        
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        if size > max_size:
            raise ValueError(f"Arquivo muito grande. Tamanho máximo: {max_size // (1024*1024)}MB")
        
        if size == 0:
            raise ValueError("Arquivo está vazio")
        
        # Gerar nome único
        filename = secure_filename(file.filename)
        if not filename:
            raise ValueError("Nome do arquivo inválido")
        
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Usar pasta compartilhada se configurada
        try:
            from app.shared_folder_config import get_upload_path
            upload_path = get_upload_path(subfolder)
        except:
            # Fallback para pasta padrão
            upload_path = current_app.config['UPLOAD_FOLDER']
            if subfolder:
                upload_path = os.path.join(upload_path, subfolder)
                os.makedirs(upload_path, exist_ok=True)
        
        filepath = os.path.join(upload_path, unique_filename)
        
        # Se for imagem, otimizar (se PIL disponível)
        if ext.lower() in ['.jpg', '.jpeg', '.png'] and HAS_PIL:
            optimize_image(file, filepath)
        else:
            file.save(filepath)
        
        # Verificar se o arquivo foi salvo corretamente
        if not os.path.exists(filepath):
            raise ValueError("Falha ao salvar o arquivo no servidor")
        
        return os.path.join(subfolder, unique_filename) if subfolder else unique_filename
        
    except Exception as e:
        current_app.logger.error(f"Erro ao salvar arquivo: {str(e)}")
        raise ValueError(f"Erro ao processar arquivo: {str(e)}")
    
    return None

def optimize_image(file, filepath, max_size=(800, 800), quality=85):
    """Otimiza imagem reduzindo tamanho e qualidade"""
    if not HAS_PIL:
        # Se PIL não estiver disponível, salvar arquivo original
        file.seek(0)
        file.save(filepath)
        return
    
    try:
        image = Image.open(file.stream)
        
        # Converter para RGB se necessário
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Redimensionar mantendo proporção
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Salvar com qualidade otimizada
        image.save(filepath, optimize=True, quality=quality)
    except Exception as e:
        # Se falhar na otimização, salvar arquivo original
        file.seek(0)
        file.save(filepath)

def log_security_event(action, details=None, user_id=None, success=True):
    """Registra evento de segurança"""
    try:
        log = SecurityLog(
            user_id=user_id,
            acao=action,
            detalhes=details,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent', '')[:500] if request else None,
            sucesso=success
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # Log de segurança não deve quebrar a aplicação
        current_app.logger.error(f"Erro ao registrar log de segurança: {e}")

def format_cpf(cpf):
    """Formata CPF para exibição"""
    import re
    numbers = re.sub(r'[^0-9]', '', cpf)
    return f"{numbers[:3]}.{numbers[3:6]}.{numbers[6:9]}-{numbers[9:]}"

def calculate_work_hours(entrada, saida, data=None, expected_hours=8.0):
    """Calcula horas trabalhadas entre entrada e saída"""
    if not entrada or not saida:
        return 0.0, 0.0
    
    # Se não tem data, assume hoje
    if data is None:
        data = date.today()
    
    # Converter para datetime
    if isinstance(entrada, time):
        entrada_dt = datetime.combine(data, entrada)
    else:
        entrada_dt = entrada
    
    if isinstance(saida, time):
        saida_dt = datetime.combine(data, saida)
    else:
        saida_dt = saida
    
    # Se saída é menor que entrada, assume que é no dia seguinte
    if saida_dt <= entrada_dt:
        from datetime import timedelta
        saida_dt += timedelta(days=1)
    
    # Calcular diferença em horas
    diferenca = saida_dt - entrada_dt
    total_horas = diferenca.total_seconds() / 3600
    
    # Calcular horas normais e extras baseado nas horas esperadas
    horas_normais = min(total_horas, expected_hours)
    horas_extras = max(0.0, total_horas - expected_hours)
    
    return horas_normais, horas_extras

def format_hours(hours):
    """Formata horas em formato HH:MM"""
    if not hours:
        return "00:00"
    
    hours_int = int(hours)
    minutes = int((hours - hours_int) * 60)
    return f"{hours_int:02d}:{minutes:02d}"

def get_month_name(month):
    """Retorna nome do mês em português"""
    months = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    return months.get(month, '')

def get_weekday_name(weekday):
    """Retorna nome do dia da semana em português"""
    weekdays = {
        0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
        3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
    }
    return weekdays.get(weekday, '')

def create_notification(user_id, titulo, mensagem, tipo='info', sender_id=None):
    """Cria uma notificação para um usuário"""
    from app.models import Notification, NotificationType
    
    try:
        notification = Notification(
            user_id=user_id,
            sender_id=sender_id,
            titulo=titulo,
            mensagem=mensagem,
            tipo=NotificationType(tipo)
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    except Exception as e:
        current_app.logger.error(f"Erro ao criar notificação: {e}")
        return None

def send_notification_to_admins(titulo, mensagem, tipo='info'):
    """Envia notificação para todos os administradores"""
    from app.models import User, UserType
    
    admins = User.query.filter_by(user_type=UserType.ADMIN, is_active=True).all()
    for admin in admins:
        create_notification(admin.id, titulo, mensagem, tipo)

def create_admin_notification(titulo, mensagem, notification_type='info'):
    """Cria notificação para todos os administradores"""
    return send_notification_to_admins(titulo, mensagem, notification_type)

def validate_date_range(start_date, end_date):
    """Valida intervalo de datas"""
    if start_date > end_date:
        return False, "Data de início deve ser anterior à data de fim."
    
    if (end_date - start_date).days > 365:
        return False, "Intervalo não pode ser maior que 365 dias."
    
    return True, ""

def paginate_query(query, page, per_page=20):
    """Adiciona paginação a uma query"""
    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

def compress_file(filepath, max_size_mb=5):
    """Comprime arquivo se necessário"""
    if not os.path.exists(filepath):
        return False
    
    file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
    
    if file_size <= max_size_mb:
        return True
    
    # Se for imagem, recomprimir (se PIL disponível)
    if filepath.lower().endswith(('.jpg', '.jpeg', '.png')) and HAS_PIL:
        try:
            with Image.open(filepath) as img:
                # Reduzir qualidade
                quality = 70 if file_size > 10 else 80
                img.save(filepath, optimize=True, quality=quality)
                return True
        except Exception:
            return False
    
    return False

def backup_database():
    """Cria backup do banco de dados"""
    import shutil
    
    try:
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        backup_dir = os.path.join(current_app.instance_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = get_current_datetime().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        shutil.copy2(db_path, backup_path)
        
        # Log do backup
        log_security_event('BACKUP_CREATED', f'Backup criado: {backup_filename}')
        
        return True, backup_path
    except Exception as e:
        current_app.logger.error(f"Erro ao criar backup: {e}")
        return False, str(e)

def backup_to_github():
    """Cria backup completo e faz upload para GitHub"""
    import subprocess
    import shutil
    import tempfile
    import json
    
    try:
        # Criar diretório temporário para o backup
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = os.path.join(temp_dir, 'skponto_backup')
            os.makedirs(backup_dir, exist_ok=True)
            
            # 1. Backup do banco de dados
            db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            backup_db_path = os.path.join(backup_dir, 'database.db')
            shutil.copy2(db_path, backup_db_path)
            
            # 2. Backup dos uploads
            upload_folder = current_app.config['UPLOAD_FOLDER']
            if os.path.exists(upload_folder):
                backup_uploads_path = os.path.join(backup_dir, 'uploads')
                shutil.copytree(upload_folder, backup_uploads_path)
            
            # 3. Backup das configurações (sem dados sensíveis)
            config_backup = {
                'timestamp': get_current_datetime().isoformat(),
                'version': '1.0',
                'timezone': current_app.config.get('TIMEZONE'),
                'allowed_extensions': list(current_app.config.get('ALLOWED_EXTENSIONS', [])),
                'max_content_length': current_app.config.get('MAX_CONTENT_LENGTH')
            }
            
            config_path = os.path.join(backup_dir, 'config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_backup, f, indent=2, ensure_ascii=False)
            
            # 4. Criar arquivo ZIP do backup
            timestamp = get_current_datetime().strftime('%Y%m%d_%H%M%S')
            zip_filename = f'skponto_backup_{timestamp}.zip'
            zip_path = os.path.join(temp_dir, zip_filename)
            
            shutil.make_archive(zip_path.replace('.zip', ''), 'zip', backup_dir)
            
            # 5. Fazer upload para GitHub (se configurado)
            github_success = False
            github_message = "GitHub não configurado"
            
            github_token = os.environ.get('GITHUB_TOKEN')
            github_repo = os.environ.get('GITHUB_BACKUP_REPO')  # formato: usuario/repo
            
            if github_token and github_repo:
                try:
                    github_success = upload_to_github(zip_path, zip_filename, github_token, github_repo)
                    github_message = "Upload para GitHub realizado com sucesso!" if github_success else "Erro no upload para GitHub"
                except Exception as e:
                    github_message = f"Erro no upload para GitHub: {str(e)}"
            
            # Log do backup
            log_details = f'Backup completo criado: {zip_filename}'
            if github_success:
                log_details += ' (Enviado para GitHub)'
            
            log_security_event('BACKUP_COMPLETE', log_details)
            
            return True, {
                'filename': zip_filename,
                'github_success': github_success,
                'github_message': github_message,
                'local_path': zip_path
            }
            
    except Exception as e:
        current_app.logger.error(f"Erro ao criar backup completo: {e}")
        return False, str(e)

def upload_to_github(file_path, filename, token, repo):
    """Faz upload de arquivo para repositório GitHub"""
    import requests
    import base64
    
    try:
        # Ler o arquivo
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Codificar em base64
        content_encoded = base64.b64encode(file_content).decode('utf-8')
        
        # Preparar dados para a API do GitHub
        url = f"https://api.github.com/repos/{repo}/contents/backups/{filename}"
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        data = {
            'message': f'Backup automático SKPONTO - {get_current_datetime().strftime("%d/%m/%Y %H:%M")}',
            'content': content_encoded,
            'branch': 'main'  # ou 'master' dependendo do repositório
        }
        
        # Verificar se o arquivo já existe
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # Arquivo existe, incluir SHA para atualização
            data['sha'] = response.json()['sha']
        
        # Fazer upload
        response = requests.put(url, json=data, headers=headers)
        
        if response.status_code in [200, 201]:
            return True
        else:
            current_app.logger.error(f"Erro no upload para GitHub: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Erro no upload para GitHub: {e}")
        return False

def setup_github_backup_schedule():
    """Configura backup automático para GitHub"""
    # Esta função pode ser expandida para usar APScheduler ou similar
    # Por enquanto, retorna instruções para configuração manual
    return {
        'env_vars': {
            'GITHUB_TOKEN': 'Token de acesso pessoal do GitHub',
            'GITHUB_BACKUP_REPO': 'usuario/repositorio (ex: joao/skponto-backups)'
        },
        'instructions': [
            '1. Crie um repositório privado no GitHub para armazenar os backups',
            '2. Gere um token de acesso pessoal com permissões de escrita no repositório',
            '3. Configure as variáveis de ambiente GITHUB_TOKEN e GITHUB_BACKUP_REPO',
            '4. Execute backup manual para testar a configuração'
        ]
    }

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida"""
    if not filename:
        return False
    
    allowed_extensions = {
        # Documentos
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'odt',
        # Imagens
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'tiff',
        # Arquivos compactados
        'zip', 'rar', '7z', 'tar', 'gz', 'bz2',
        # Vídeos
        'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv',
        # Áudios
        'mp3', 'wav', 'ogg', 'flac', 'aac',
        # Outros
        'csv', 'json', 'xml', 'log'
    }
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_size(file_path):
    """Retorna o tamanho do arquivo em bytes"""
    try:
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return 0
    except Exception:
        return 0

def format_file_size(size_bytes):
    """Formatar tamanho de arquivo em formato legível"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def get_file_type_icon(filename):
    """Retorna classe CSS do ícone baseado na extensão do arquivo"""
    if not filename:
        return 'fas fa-file text-muted'
    
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    icon_mapping = {
        # Documentos
        'pdf': 'fas fa-file-pdf text-danger',
        'doc': 'fas fa-file-word text-primary',
        'docx': 'fas fa-file-word text-primary',
        'xls': 'fas fa-file-excel text-success',
        'xlsx': 'fas fa-file-excel text-success',
        'ppt': 'fas fa-file-powerpoint text-warning',
        'pptx': 'fas fa-file-powerpoint text-warning',
        'txt': 'fas fa-file-alt text-info',
        'rtf': 'fas fa-file-alt text-info',
        'csv': 'fas fa-file-csv text-success',
        
        # Imagens
        'jpg': 'fas fa-image text-primary',
        'jpeg': 'fas fa-image text-primary',
        'png': 'fas fa-image text-primary',
        'gif': 'fas fa-image text-primary',
        'bmp': 'fas fa-image text-primary',
        'svg': 'fas fa-image text-primary',
        'webp': 'fas fa-image text-primary',
        
        # Arquivos compactados
        'zip': 'fas fa-file-archive text-warning',
        'rar': 'fas fa-file-archive text-warning',
        '7z': 'fas fa-file-archive text-warning',
        'tar': 'fas fa-file-archive text-warning',
        'gz': 'fas fa-file-archive text-warning',
        
        # Vídeos
        'mp4': 'fas fa-film text-secondary',
        'avi': 'fas fa-film text-secondary',
        'mov': 'fas fa-film text-secondary',
        'wmv': 'fas fa-film text-secondary',
        'flv': 'fas fa-film text-secondary',
        'webm': 'fas fa-film text-secondary',
        
        # Áudios
        'mp3': 'fas fa-music text-success',
        'wav': 'fas fa-music text-success',
        'ogg': 'fas fa-music text-success',
        'flac': 'fas fa-music text-success',
        'aac': 'fas fa-music text-success',
        
        # Outros
        'json': 'fas fa-code text-info',
        'xml': 'fas fa-code text-info',
        'log': 'fas fa-file-alt text-muted'
    }
    
    return icon_mapping.get(extension, 'fas fa-file text-muted')

def sanitize_filename(filename):
    """Sanitiza nome de arquivo removendo caracteres perigosos"""
    if not filename:
        return None
    
    # Remove caracteres perigosos
    filename = secure_filename(filename)
    
    # Remove espaços extras e caracteres especiais
    filename = filename.replace(' ', '_')
    filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
    
    # Limita o tamanho do nome
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext
    
    return filename

def create_thumbnail(image_path, thumbnail_path, size=(150, 150)):
    """Cria thumbnail de uma imagem"""
    if not HAS_PIL:
        return False
    
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.LANCZOS)
            img.save(thumbnail_path, optimize=True, quality=85)
            return True
    except Exception as e:
        current_app.logger.error(f"Erro ao criar thumbnail: {e}")
        return False

def validate_file_upload(file):
    """Valida upload de arquivo"""
    errors = []
    
    if not file or not file.filename:
        errors.append("Nenhum arquivo selecionado")
        return errors
    
    # Verificar extensão
    if not allowed_file(file.filename):
        errors.append("Tipo de arquivo não permitido")
    
    # Verificar tamanho (máximo 50MB)
    file.seek(0, 2)  # Vai para o final do arquivo
    size = file.tell()
    file.seek(0)     # Volta para o início
    
    if size > 50 * 1024 * 1024:  # 50MB
        errors.append("Arquivo muito grande (máximo 50MB)")
    
    if size == 0:
        errors.append("Arquivo vazio")
    
    return errors

def generate_unique_filename(original_filename, upload_path):
    """Gera nome único para arquivo evitando conflitos"""
    filename = sanitize_filename(original_filename)
    if not filename:
        filename = f"arquivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    full_path = os.path.join(upload_path, filename)
    
    # Se arquivo não existe, retorna o nome original
    if not os.path.exists(full_path):
        return filename
    
    # Gera nome único adicionando timestamp
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{name}_{timestamp}{ext}"
    
    return unique_filename
