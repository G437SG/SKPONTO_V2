# -*- coding: utf-8 -*-
"""
Constantes do sistema SKPONTO
Centraliza valores literais para evitar duplicação
"""

# Database Table References
USERS_TABLE_ID = 'users.id'
TIME_RECORDS_TABLE = 'time_records'
MEDICAL_ATTESTATIONS_TABLE = 'medical_attestations'
NOTIFICATIONS_TABLE = 'notifications'
SECURITY_LOGS_TABLE = 'security_logs'
SYSTEM_CONFIGS_TABLE = 'system_configs'
WORK_CLASSES_TABLE = 'work_classes'

# Cascade Options
CASCADE_DELETE_ORPHAN = 'all, delete-orphan'

# File Upload
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

# Image Optimization
MAX_IMAGE_SIZE = (800, 800)
IMAGE_QUALITY = 85

# Pagination
DEFAULT_PER_PAGE = 20
ADMIN_PER_PAGE = 50
MAX_PER_PAGE = 100

# Date Formats
DATE_FORMAT_BR = '%d/%m/%Y'
DATETIME_FORMAT_BR = '%d/%m/%Y %H:%M:%S'
TIME_FORMAT_BR = '%H:%M'

# Backup
BACKUP_RETENTION_DAYS = 30
MAX_BACKUP_SIZE_MB = 100

# Security
MAX_LOGIN_ATTEMPTS = 5
SESSION_TIMEOUT_HOURS = 1
PASSWORD_MIN_LENGTH = 6

# Work Hours
DEFAULT_WORK_HOURS = 8.0
DEFAULT_LUNCH_HOURS = 1.0
MAX_DAILY_HOURS = 12.0

# Notification Types
NOTIFICATION_RETENTION_DAYS = 90

# File Size Limits
MAX_FILE_SIZE_MB = 16
MAX_PROFILE_IMAGE_SIZE_MB = 5

# Admin Credentials (Hardcoded)
ADMIN_EMAIL = 'admin@skponto.com'
ADMIN_PASSWORD = 'admin123'
ADMIN_NAME = 'Administrador'
ADMIN_SURNAME = 'Sistema'
ADMIN_CPF = '00000000000'

# Time Zones
DEFAULT_TIMEZONE = 'America/Sao_Paulo'

# Month Names in Portuguese
MONTH_NAMES = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

# Weekday Names in Portuguese
WEEKDAY_NAMES = {
    0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
    3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
}

# local Backup
local_BACKUP_FOLDER = '/skponto_backups'
local_TOKEN_FILE = 'local_token.txt'
BACKUP_SCHEDULE_HOURS = [6, 12, 18]  # Horários automáticos de backup
AUTO_BACKUP_ENABLED = True

# GitHub Backup (Secundário)
GITHUB_BACKUP_BRANCH = 'main'
GITHUB_API_URL = 'https://api.github.com'

# Log Retention
LOG_RETENTION_DAYS = 30
SECURITY_LOG_MAX_ENTRIES = 10000

# User Approval System
USER_APPROVAL_REQUIRED = True
AUTO_APPROVE_ADMINS = True
PENDING_APPROVAL_MESSAGE = 'Sua conta está aguardando aprovação do administrador.'

# Backup Status
BACKUP_STATUS_PENDING = 'PENDENTE'
BACKUP_STATUS_IN_PROGRESS = 'EM_PROGRESSO'
BACKUP_STATUS_COMPLETED = 'CONCLUIDO'
BACKUP_STATUS_FAILED = 'FALHOU'
BACKUP_STATUS_CANCELLED = 'CANCELADO'

# System Status
SYSTEM_STATUS_ACTIVE = 'ATIVO'
SYSTEM_STATUS_MAINTENANCE = 'MANUTENCAO'
SYSTEM_STATUS_ERROR = 'ERRO'

# User Approval Status
APPROVAL_STATUS_PENDING = 'PENDENTE'
APPROVAL_STATUS_APPROVED = 'APROVADO'
APPROVAL_STATUS_REJECTED = 'REJEITADO'

# User Approval Settings
USER_APPROVAL_REQUIRED = True
APPROVAL_NOTIFICATION_RETENTION_DAYS = 30

# local Backup Settings
local_BACKUP_FOLDER = '/SKPONTO_Backups'
local_BACKUP_RETENTION_DAYS = 30
local_MAX_BACKUP_SIZE_MB = 500
local_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks

# local Configuration
local_CLIENT_NOT_CONFIGURED = "Cliente local não configurado"
local_ATTESTATIONS_FOLDER = "/skponto_atestados"
local_BACKUP_FOLDER = "/skponto_backups"
local_UPLOAD_SUCCESS = "Upload realizado com sucesso"
local_DELETE_SUCCESS = "Arquivo removido com sucesso"
local_ERROR_FILE_NOT_FOUND = "Arquivo não encontrado"
local_ERROR_API = "Erro da API local"
local_ERROR_UNEXPECTED = "Erro inesperado"

# Security Actions
SECURITY_ACTION_UPLOAD_ATTESTATION = "Upload de atestado para local"
SECURITY_ACTION_DELETE_ATTESTATION = "Exclusão de atestado do local"

# File Manager Icons
ICON_IMAGE = 'fas fa-image text-primary'
ICON_DOCUMENT = 'fas fa-file-alt text-info'
ICON_ARCHIVE = 'fas fa-file-archive text-warning'
ICON_VIDEO = 'fas fa-film text-secondary'
ICON_AUDIO = 'fas fa-music text-success'
ICON_PDF = 'fas fa-file-pdf text-danger'
ICON_WORD = 'fas fa-file-word text-primary'
ICON_EXCEL = 'fas fa-file-excel text-success'
ICON_POWERPOINT = 'fas fa-file-powerpoint text-warning'
ICON_CODE = 'fas fa-code text-info'
ICON_FILE = 'fas fa-file text-muted'

# File Manager Messages
MSG_NO_FILE_SELECTED = 'Nenhum arquivo selecionado'
MSG_FILE_NOT_FOUND = 'Arquivo não encontrado'
MSG_INVALID_PARAMETERS = 'Parâmetros inválidos'
MSG_OPERATION_NOT_ALLOWED = 'Operação não permitida'
MSG_FILE_UPLOADED = 'Arquivo enviado com sucesso!'
MSG_FILE_DELETED = 'Arquivo deletado com sucesso!'
MSG_FILE_MOVED = 'Arquivo movido com sucesso!'
MSG_FILE_RENAMED = 'Arquivo renomeado com sucesso!'
MSG_FOLDER_CREATED = 'Pasta criada com sucesso!'
MSG_FOLDER_DELETED = 'Pasta deletada com sucesso!'
MSG_ZIP_CREATED = 'Arquivo ZIP criado com sucesso!'

# File Manager Routes
ROUTE_FILE_MANAGER = 'files.file_manager'

# File Size Limits
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# File Extensions
ALLOWED_FILE_EXTENSIONS = {
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
