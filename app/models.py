from datetime import datetime, timezone
import os
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.constants import (
    USERS_TABLE_ID, CASCADE_DELETE_ORPHAN, 
    DEFAULT_WORK_HOURS, DEFAULT_LUNCH_HOURS,
    ADMIN_EMAIL, ADMIN_PASSWORD,
    BACKUP_STATUS_PENDING, BACKUP_STATUS_COMPLETED, BACKUP_STATUS_FAILED,
    USER_APPROVAL_REQUIRED
)
import enum

class UserType(enum.Enum):
    """Tipos de usuários do sistema"""
    ADMIN = "admin"
    TRABALHADOR = "trabalhador"
    ESTAGIARIO = "estagiario"

class NotificationType(enum.Enum):
    """Tipos de notificaé§éµes"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

class AttestationType(enum.Enum):
    """Tipos de atestados mé©dicos"""
    MEDICO = "MEDICO"
    ODONTOLOGICO = "ODONTOLOGICO"  
    PSICOLOGICO = "PSICOLOGICO"
    OUTROS = "OUTROS"

class AttestationStatus(enum.Enum):
    """Status do atestado"""
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    REJEITADO = "REJEITADO"

class BackupStatus(enum.Enum):
    """Status do backup"""
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"  
    CONCLUIDO = "CONCLUIDO"
    FALHOU = "FALHOU"
    CANCELADO = "CANCELADO"

class BackupType(enum.Enum):
    """Tipo de backup"""
    MANUAL = "MANUAL"
    AUTOMATICO = "AUTOMATICO"
    COMPLETO = "COMPLETO"
    INCREMENTAL = "INCREMENTAL"

class ApprovalStatus(enum.Enum):
    """Status de aprovaçéo"""
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    REJEITADO = "REJEITADO"

class OvertimeType(enum.Enum):
    """Tipos de horas extras"""
    NORMAL = "NORMAL"           # Horas extras normais (multiplicador 1.5)
    URGENTE = "URGENTE"         # Horas extras urgentes (multiplicador 2.0)
    PLANEJADA = "PLANEJADA"     # Horas extras planejadas (multiplicador 1.5)
    FERIADO = "FERIADO"         # Horas extras em feriado (multiplicador 2.5)
    DOMINGO = "DOMINGO"         # Horas extras em domingo (multiplicador 2.0)
    NOTURNA = "NOTURNA"         # Adicional noturno (multiplicador 1.2)

class OvertimeStatus(enum.Enum):
    """Status de aprovaçéo de horas extras"""
    PENDENTE = "PENDENTE"
    APROVADA = "APROVADA"
    REJEITADA = "REJEITADA"
    CANCELADA = "CANCELADA"

class HourBankTransactionType(enum.Enum):
    """Tipos de transaçéo no banco de horas"""
    CREDITO = "CREDITO"         # Adicionar horas ao banco
    DEBITO = "DEBITO"           # Remover horas do banco
    COMPENSACAO = "COMPENSACAO" # Compensaçéo automática
    AJUSTE = "AJUSTE"           # Ajuste manual pelo admin
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"  # Ajuste manual (compatibilidade)
    EXPIRAÇéO = "EXPIRACAO"     # Expiraçéo de horas

class CompensationStatus(enum.Enum):
    """Status de compensaçéo de horas"""
    PENDENTE = "PENDENTE"
    APLICADA = "APLICADA"
    CANCELADA = "CANCELADA"

class WorkClass(db.Model):
    """Modelo de classe de trabalho com carga horária personalizada"""
    __tablename__ = 'work_classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    daily_work_hours = db.Column(db.Float, nullable=False)  # Horas de trabalho por dia
    lunch_hours = db.Column(db.Float, nullable=False, default=1.0)  # Horas de almoço
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)  # Aprovaçéo de usuário
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    
    # Relacionamentos
    users = db.relationship('User', foreign_keys='User.work_class_id', back_populates='work_class')
    creator = db.relationship('User', foreign_keys=[created_by], post_update=True)
    
    @property
    def usuarios(self):
        """Alias em português para users - compatibilidade com templates"""
        return self.users
    
    def get_active_users(self):
        """Retorna usuários ativos desta classe"""
        return db.session.query(User).filter_by(work_class_id=self.id, is_active=True)
    
    def get_users_count(self):
        """Retorna número de usuários ativos"""
        return db.session.query(User).filter_by(work_class_id=self.id, is_active=True).count()
    
    @property
    def total_daily_hours(self):
        """Calcula total de horas no local (trabalho + almoé§o)"""
        return self.daily_work_hours + self.lunch_hours
    
    def __repr__(self):
        return f'<WorkClass {self.name}>'

class User(UserMixin, db.Model):
    """Modelo de usuário"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    cpf = db.Column(db.String(14), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False)
    sobrenome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    cargo = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.Enum(UserType), nullable=False, default=UserType.TRABALHADOR)
    work_class_id = db.Column(db.Integer, db.ForeignKey('work_classes.id'), nullable=True)
    foto_perfil = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)  # Aprovaçéo de usuário
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    work_class = db.relationship('WorkClass', foreign_keys=[work_class_id], back_populates='users')
    pontos = db.relationship('TimeRecord', backref='usuario', lazy='dynamic', 
                           foreign_keys='TimeRecord.user_id', cascade=CASCADE_DELETE_ORPHAN)
    atestados = db.relationship('MedicalAttestation', backref='usuario', lazy='dynamic', 
                              foreign_keys='MedicalAttestation.user_id', cascade=CASCADE_DELETE_ORPHAN)
    notificacoes_recebidas = db.relationship('Notification', backref='destinatario', lazy='dynamic', 
                                           foreign_keys='Notification.user_id', cascade=CASCADE_DELETE_ORPHAN)
    notificacoes_enviadas = db.relationship('Notification', backref='remetente', lazy='dynamic',
                                          foreign_keys='Notification.sender_id')
    logs = db.relationship('SecurityLog', backref='usuario', lazy='dynamic', 
                         foreign_keys='SecurityLog.user_id', cascade=CASCADE_DELETE_ORPHAN)
    banco_horas_transacoes = db.relationship('HourBankTransaction', backref='usuario', lazy='dynamic', 
                                           foreign_keys='HourBankTransaction.user_id', cascade=CASCADE_DELETE_ORPHAN)
    
    # English aliases for compatibility
    @property
    def time_records(self):
        """Alias for pontos"""
        return self.pontos
    
    @property
    def medical_attestations(self):
        """Alias for atestados"""
        return self.atestados
    
    def set_password(self, password):
        """Define a senha do usué¡rio"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica a senha do usué¡rio"""
        # HARDCODED ADMIN CREDENTIALS - INTRINSIC TO THE CODE
        if self.email == 'admin@skponto.com' and password == 'admin123':
            return True
        return check_password_hash(self.password_hash, password)
    
    @property
    def nome_completo(self):
        """Retorna o nome completo do usué¡rio"""
        return f"{self.nome} {self.sobrenome}"
    
    @property
    def is_admin(self):
        """Verifica se o usué¡rio é© administrador"""
        # HARDCODED ADMIN - INTRINSIC TO THE CODE
        if self.email == 'admin@skponto.com':
            return True
        return self.user_type == UserType.ADMIN
    
    @property
    def is_trabalhador(self):
        """Verifica se o usué¡rio é© trabalhador"""
        return self.user_type == UserType.TRABALHADOR
    
    @property
    def is_estagiario(self):
        """Verifica se o usué¡rio é© estagié¡rio"""
        return self.user_type == UserType.ESTAGIARIO
    
    @property
    def expected_daily_hours(self):
        """Returns expected daily work hours from work class"""
        if self.work_class:
            return self.work_class.daily_work_hours
        return 8.0  # Default fallback

    @property
    def expected_lunch_hours(self):
        """Returns expected lunch hours from work class"""
        if self.work_class:
            return self.work_class.lunch_hours
        return 1.0  # Default fallback

    @property
    def expected_total_hours(self):
        """Retorna o total de horas esperadas por dia (trabalho + almoé§o)"""
        if self.work_class:
            return self.work_class.daily_work_hours + self.work_class.lunch_hours
        return 8.0  # Default 8 hours if no work class assigned

    @property
    def profile_picture_url(self):
        """Return the URL for user's profile picture or default avatar"""
        if self.foto_perfil:
            # Ensure the path doesn't include 'profiles/' prefix
            filename = self.foto_perfil.replace('profiles/', '').replace('profiles\\', '')
            return f"uploads/profiles/{filename}"
        return "img/default-avatar.svg"  # Default avatar
    
    @property
    def has_profile_picture(self):
        """Check if user has a profile picture"""
        if not self.foto_perfil:
            return False
        
        import os
        from flask import current_app
        
        # Clean the filename
        filename = self.foto_perfil.replace('profiles/', '').replace('profiles\\', '')
        if current_app.static_folder:
            file_path = os.path.join(current_app.static_folder, 'uploads', 'profiles', filename)
            return os.path.exists(file_path)
        return False

    def calculate_overtime(self, horas_trabalhadas_brutas):
        """
        Calcula horas extras baseado nas horas trabalhadas brutas
        
        Args:
            horas_trabalhadas_brutas (float): Total de horas trabalhadas (sem desconto de almoé§o)
            
        Returns:
            float: Horas extras (0.0 se né£o houver extras)
        """
        horas_normais = self.expected_daily_hours
        if horas_trabalhadas_brutas > horas_normais:
            return horas_trabalhadas_brutas - horas_normais
        return 0.0

    def __repr__(self):
        return f'<User {self.email}>'

class TimeRecord(db.Model):
    """Modelo de registro de ponto"""
    __tablename__ = 'time_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False)
    data = db.Column(db.Date, nullable=False, index=True)
    entrada = db.Column(db.Time, nullable=True)
    saida_almoco = db.Column(db.Time, nullable=True)  # Horé¡rio de saé­da para almoé§o
    volta_almoco = db.Column(db.Time, nullable=True)  # Horé¡rio de volta do almoé§o
    saida = db.Column(db.Time, nullable=True)
    horas_trabalhadas = db.Column(db.Float, default=0.0)  # Em horas decimais
    horas_extras = db.Column(db.Float, default=0.0)
    observacoes = db.Column(db.Text, nullable=True)
    localizacao = db.Column(db.String(255), nullable=True)
    # Atestado fields
    is_atestado = db.Column(db.Boolean, default=False)  # Indica se é© um registro de atestado
    atestado_id = db.Column(db.Integer, db.ForeignKey('medical_attestations.id'), nullable=True)
    motivo_atestado = db.Column(db.String(500), nullable=True)  # Motivo do atestado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    edited_by = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    justificativa_edicao = db.Column(db.Text, nullable=True)
    
    # Relacionamento com editor
    editor = db.relationship('User', foreign_keys=[edited_by])
    # Relacionamento com atestado
    atestado = db.relationship('MedicalAttestation', foreign_keys=[atestado_id])
    
    @property
    def is_completo(self):
        """Verifica se o registro esté¡ completo (entrada e saé­da)"""
        return self.entrada is not None and self.saida is not None
    
    @property
    def tem_almoco_registrado(self):
        """Verifica se tem horé¡rios de almoé§o registrados"""
        return self.saida_almoco is not None and self.volta_almoco is not None
    
    @property
    def proxima_acao(self):
        """Retorna qual é© a pré³xima aé§é£o necessé¡ria no registro"""
        if not self.entrada:
            return "entrada"
        elif not self.saida_almoco:
            return "saida_almoco"
        elif not self.volta_almoco:
            return "volta_almoco"
        elif not self.saida:
            return "saida"
        else:
            return "completo"
    
    def calcular_horas(self):
        """Calcula as horas trabalhadas e extras baseado na classe de trabalho do usué¡rio"""
        if self.entrada and self.saida:
            # Converter para datetime para cé¡lculo
            entrada_dt = datetime.combine(self.data, self.entrada)
            saida_dt = datetime.combine(self.data, self.saida)
            
            # Se saé­da é© no dia seguinte
            if self.saida < self.entrada:
                from datetime import timedelta
                saida_dt += timedelta(days=1)
            
            # Calcular diferené§a total em horas
            diferenca = saida_dt - entrada_dt
            horas_totais = diferenca.total_seconds() / 3600
            
            # Subtrair tempo de almoé§o se aplicé¡vel
            horas_almoco = self.usuario.expected_lunch_hours
            horas_trabalhadas_brutas = max(0, horas_totais - horas_almoco)
            
            # Calcular horas normais e extras baseado na classe do usué¡rio
            horas_normais = self.usuario.expected_daily_hours
            self.horas_trabalhadas = min(horas_trabalhadas_brutas, horas_normais)
            self.horas_extras = self.usuario.calculate_overtime(horas_trabalhadas_brutas)
            
            # Processar horas extras no banco de horas automaticamente
            self._process_hours_to_bank(horas_trabalhadas_brutas, horas_normais)
        else:
            self.horas_trabalhadas = 0.0
            self.horas_extras = 0.0
    
    def _process_hours_to_bank(self, horas_trabalhadas_brutas, horas_normais):
        """Processa horas extras e déficit para o banco de horas do usuário"""
        # Criar ou obter banco de horas do usuário
        hour_bank = self.usuario.hour_bank
        if not hour_bank:
            hour_bank = HourBank(user_id=self.usuario.id)
            db.session.add(hour_bank)
            db.session.flush()  # Para obter o ID
        
        # Verificar se já foi processado para evitar duplicaçéo
        existing_transaction = HourBankTransaction.query.filter_by(
            time_record_id=self.id
        ).first()
        
        if existing_transaction:
            return  # Já foi processado
        
        # Calcular diferença entre horas trabalhadas e esperadas
        diferenca_horas = horas_trabalhadas_brutas - horas_normais
        
        if diferenca_horas > 0:
            # Horas extras - creditar no banco
            hour_bank.add_hours(
                diferenca_horas,
                HourBankTransactionType.CREDITO,
                f"Horas extras do dia {self.data.strftime('%d/%m/%Y')} - {diferenca_horas:.2f}h extras"
            )
            
            # Associar a transaçéo a este registro de ponto
            transaction = HourBankTransaction.query.filter_by(
                user_id=self.usuario.id,
                time_record_id=None
            ).order_by(HourBankTransaction.created_at.desc()).first()
            
            if transaction:
                transaction.time_record_id = self.id
                transaction.reference_date = self.data
                
        elif diferenca_horas < 0 and hour_bank.current_balance > 0:
            # Déficit de horas - debitar do banco se houver saldo
            horas_deficit = abs(diferenca_horas)
            horas_a_debitar = min(horas_deficit, hour_bank.current_balance)
            
            if horas_a_debitar > 0:
                hour_bank.debit_hours(
                    horas_a_debitar,
                    HourBankTransactionType.DEBITO,
                    f"Compensaçéo de déficit do dia {self.data.strftime('%d/%m/%Y')} - {horas_a_debitar:.2f}h debitadas"
                )
                
                # Associar a transaçéo a este registro de ponto
                transaction = HourBankTransaction.query.filter_by(
                    user_id=self.usuario.id,
                    time_record_id=None
                ).order_by(HourBankTransaction.created_at.desc()).first()
                
                if transaction:
                    transaction.time_record_id = self.id
                    transaction.reference_date = self.data


    def calcular_horas_detalhado(self, saida_almoco=None, volta_almoco=None):
        """Calcula horas considerando horé¡rios de almoé§o especé­ficos"""
        if not (self.entrada and self.saida):
            self.horas_trabalhadas = 0.0
            self.horas_extras = 0.0
            return
        
        # Converter para datetime
        entrada_dt = datetime.combine(self.data, self.entrada)
        saida_dt = datetime.combine(self.data, self.saida)
        
        # Se saé­da é© no dia seguinte
        if self.saida < self.entrada:
            from datetime import timedelta
            saida_dt += timedelta(days=1)
        
        # Calcular tempo total
        tempo_total = saida_dt - entrada_dt
        horas_totais = tempo_total.total_seconds() / 3600
        
        # Calcular tempo de almoé§o
        if saida_almoco and volta_almoco:
            saida_almoco_dt = datetime.combine(self.data, saida_almoco)
            volta_almoco_dt = datetime.combine(self.data, volta_almoco)
            tempo_almoco = volta_almoco_dt - saida_almoco_dt
            horas_almoco = tempo_almoco.total_seconds() / 3600
        else:
            # Usar tempo padré£o de almoé§o se esteve mais que as horas esperadas
            if horas_totais > self.usuario.expected_daily_hours:
                horas_almoco = self.usuario.expected_lunch_hours
            else:
                horas_almoco = 0
        
        # Calcular horas efetivamente trabalhadas
        horas_trabalhadas_brutas = max(0, horas_totais - horas_almoco)
        
        # Definir horas normais e extras
        horas_normais = self.usuario.expected_daily_hours
        self.horas_trabalhadas = min(horas_trabalhadas_brutas, horas_normais)
        self.horas_extras = self.usuario.calcular_horas_extras(horas_trabalhadas_brutas)
    
    def __repr__(self):
        return f'<TimeRecord {self.usuario.nome} - {self.data}>'

class MedicalAttestation(db.Model):
    """Modelo de atestado mé©dico"""
    __tablename__ = 'medical_attestations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False)
    tipo = db.Column(db.Enum(AttestationType), nullable=False, default=AttestationType.MEDICO)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    cid = db.Column(db.String(10), nullable=True)
    medico_clinica = db.Column(db.String(200), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    arquivo = db.Column(db.String(255), nullable=False)  # Nome do arquivo
    local_path = db.Column(db.String(500), nullable=True)  # Caminho local do arquivo
    status = db.Column(db.Enum(AttestationStatus), default=AttestationStatus.PENDENTE, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    aprovado_por = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    data_aprovacao = db.Column(db.DateTime, nullable=True)
    motivo_rejeicao = db.Column(db.Text, nullable=True)
    
    # Relacionamento com aprovador
    aprovador = db.relationship('User', foreign_keys=[aprovado_por])
    
    @property
    def dias_licenca(self):
        """Calcula o néºmero de dias de licené§a"""
        return (self.data_fim - self.data_inicio).days + 1
    
    def __repr__(self):
        return f'<MedicalAttestation {self.usuario.nome} - {self.data_inicio}>'

class Notification(db.Model):
    """Modelo de notificaé§éµes"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    titulo = db.Column(db.String(200), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.Enum(NotificationType), default=NotificationType.INFO, nullable=False)
    lida = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.titulo}>'

class SecurityLog(db.Model):
    """Modelo de logs de segurané§a"""
    __tablename__ = 'security_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    acao = db.Column(db.String(100), nullable=False)
    detalhes = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sucesso = db.Column(db.Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f'<SecurityLog {self.acao} - {self.created_at}'

class SystemConfig(db.Model):
    """Modelo de configuraé§éµes do sistema"""
    __tablename__ = 'system_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text, nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemConfig {self.chave}>'

# Removido - classe DropboxConfig néo é mais necessária com sistema local

class BackupHistory(db.Model):
    """Histórico de backups"""
    __tablename__ = 'backup_history'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=True)  # Tamanho em bytes
    backup_type = db.Column(db.Enum(BackupType), nullable=False, default=BackupType.MANUAL)
    status = db.Column(db.Enum(BackupStatus), nullable=False, default=BackupStatus.PENDENTE)
    local_path = db.Column(db.String(500), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    
    # Relacionamento
    creator = db.relationship('User', foreign_keys=[created_by])
    
    @property
    def duration_formatted(self):
        """Retorna duraçéo formatada"""
        if not self.duration_seconds:
            return "N/A"
        
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    
    @property
    def file_size_formatted(self):
        """Retorna tamanho formatado"""
        if not self.file_size:
            return "N/A"
        
        # Converter bytes para MB
        size_mb = self.file_size / (1024 * 1024)
        
        if size_mb >= 1024:
            return f"{size_mb/1024:.1f} GB"
        elif size_mb >= 1:
            return f"{size_mb:.1f} MB"
        else:
            return f"{self.file_size/1024:.1f} KB"
    
    def __repr__(self):
        return f'<BackupHistory {self.filename} - {self.status.value}>'

class UserApprovalRequest(db.Model):
    """Solicitações de aprovaçéo de usuários"""
    __tablename__ = 'user_approval_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False)
    status = db.Column(db.Enum(ApprovalStatus), default=ApprovalStatus.PENDENTE, nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    user_message = db.Column(db.Text, nullable=True)  # Mensagem do usuário solicitante
    admin_notes = db.Column(db.Text, nullable=True)   # Notas do administrador
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    @property
    def is_pending(self):
        return self.status == ApprovalStatus.PENDENTE
    
    @property
    def is_approved(self):
        return self.status == ApprovalStatus.APROVADO
    
    @property
    def is_rejected(self):
        return self.status == ApprovalStatus.REJEITADO
    
    def __repr__(self):
        return f'<UserApprovalRequest {self.user.email if self.user else "N/A"} - {self.status.value}>'

class SystemStatus(db.Model):
    """Status geral do sistema"""
    __tablename__ = 'system_status'
    
    id = db.Column(db.Integer, primary_key=True)
    component = db.Column(db.String(100), nullable=False)  # backup, database, storage, etc
    status = db.Column(db.String(50), nullable=False)  # ATIVO, ERRO, MANUTENCAO
    message = db.Column(db.Text, nullable=True)
    last_check = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_success = db.Column(db.DateTime, nullable=True)
    error_count = db.Column(db.Integer, default=0, nullable=False)
    is_critical = db.Column(db.Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f'<SystemStatus {self.component} - {self.status}'

class OvertimeSettings(db.Model):
    """Configurações de horas extras por usuário"""
    __tablename__ = 'overtime_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False, unique=True)
    max_daily_overtime = db.Column(db.Float, default=4.0, nullable=False)  # Máximo 4h extras por dia
    max_weekly_overtime = db.Column(db.Float, default=16.0, nullable=False)  # Máximo 16h extras por semana
    max_monthly_overtime = db.Column(db.Float, default=60.0, nullable=False)  # Máximo 60h extras por mês
    requires_approval = db.Column(db.Boolean, default=True, nullable=False)  # Requer aprovaçéo prévia
    auto_approval_limit = db.Column(db.Float, default=2.0, nullable=False)  # Aprovaçéo automática até 2h
    overtime_multiplier_normal = db.Column(db.Float, default=1.5, nullable=False)
    overtime_multiplier_urgent = db.Column(db.Float, default=2.0, nullable=False)
    overtime_multiplier_holiday = db.Column(db.Float, default=2.5, nullable=False)
    overtime_multiplier_sunday = db.Column(db.Float, default=2.0, nullable=False)
    overtime_multiplier_night = db.Column(db.Float, default=1.2, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    user = db.relationship('User', backref='overtime_settings')
    
    def get_multiplier(self, overtime_type):
        """Retorna o multiplicador baseado no tipo de hora extra"""
        multipliers = {
            OvertimeType.NORMAL: self.overtime_multiplier_normal,
            OvertimeType.URGENTE: self.overtime_multiplier_urgent,
            OvertimeType.PLANEJADA: self.overtime_multiplier_normal,
            OvertimeType.FERIADO: self.overtime_multiplier_holiday,
            OvertimeType.DOMINGO: self.overtime_multiplier_sunday,
            OvertimeType.NOTURNA: self.overtime_multiplier_night,
        }
        return multipliers.get(overtime_type, 1.5)
    
    def __repr__(self):
        return f'<OvertimeSettings {self.user.nome if self.user else "N/A"}>'

class OvertimeRequest(db.Model):
    """Solicitações de horas extras"""
    __tablename__ = 'overtime_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    estimated_hours = db.Column(db.Float, nullable=False)
    overtime_type = db.Column(db.Enum(OvertimeType), default=OvertimeType.NORMAL, nullable=False)
    justification = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(OvertimeStatus), default=OvertimeStatus.PENDENTE, nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    actual_hours = db.Column(db.Float, nullable=True)  # Horas realmente trabalhadas
    multiplier_applied = db.Column(db.Float, nullable=True)  # Multiplicador aplicado
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id])
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    @property
    def is_pending(self):
        return self.status == OvertimeStatus.PENDENTE
    
    @property
    def is_approved(self):
        return self.status == OvertimeStatus.APROVADA
    
    @property
    def is_rejected(self):
        return self.status == OvertimeStatus.REJEITADA
    
    @property
    def effective_hours(self):
        """Retorna as horas efetivas (estimadas ou reais)"""
        return self.actual_hours if self.actual_hours is not None else self.estimated_hours
    
    def calculate_compensation_value(self):
        """Calcula valor da compensaçéo baseado no multiplicador"""
        if not self.multiplier_applied:
            # Buscar multiplicador das configurações do usuário
            settings = OvertimeSettings.query.filter_by(user_id=self.user_id).first()
            if settings:
                self.multiplier_applied = settings.get_multiplier(self.overtime_type)
            else:
                self.multiplier_applied = 1.5  # Padréo
        
        return self.effective_hours * self.multiplier_applied
    
    def __repr__(self):
        return f'<OvertimeRequest {self.user.nome if self.user else "N/A"} - {self.date}>'

class HourBank(db.Model):
    """Banco de horas do usuário"""
    __tablename__ = 'hour_bank'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False, unique=True)
    current_balance = db.Column(db.Float, default=0.0, nullable=False)  # Saldo atual em horas
    total_credited = db.Column(db.Float, default=0.0, nullable=False)   # Total creditado (histórico)
    total_debited = db.Column(db.Float, default=0.0, nullable=False)    # Total debitado (histórico)
    last_transaction = db.Column(db.DateTime, nullable=True)
    expiration_enabled = db.Column(db.Boolean, default=True, nullable=False)
    expiration_months = db.Column(db.Integer, default=12, nullable=False)  # Horas expiram em X meses
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    user = db.relationship('User', backref=db.backref('hour_bank', uselist=False))
    
    @property
    def has_positive_balance(self):
        return self.current_balance > 0
    
    @property
    def formatted_balance(self):
        """Retorna saldo formatado (permite valores negativos)"""
        balance = self.current_balance
        is_negative = balance < 0
        
        # Trabalhar com valor absoluto para cálculos
        abs_balance = abs(balance)
        hours = int(abs_balance)
        minutes = int((abs_balance % 1) * 60)
        
        # Aplicar sinal negativo se necessário
        if is_negative:
            return f"-{hours}h {minutes}m"
        else:
            return f"{hours}h {minutes}m"
    
    def can_debit(self, hours):
        """Verifica se pode debitar horas"""
        return self.current_balance >= hours
    
    def add_hours(self, hours, transaction_type=HourBankTransactionType.CREDITO, description=""):
        """Adiciona horas ao banco"""
        balance_before = self.current_balance  # Capturar saldo antes da alteraçéo
        self.current_balance += hours
        self.total_credited += hours
        self.last_transaction = datetime.now(timezone.utc)
        
        # Registrar transaçéo
        transaction = HourBankTransaction(
            user_id=self.user_id,
            transaction_type=transaction_type,
            hours=hours,
            balance_before=balance_before,
            balance_after=self.current_balance,
            description=description
        )
        db.session.add(transaction)
    
    def debit_hours(self, hours, transaction_type=HourBankTransactionType.DEBITO, description="", allow_negative=False):
        """Remove horas do banco"""
        if not allow_negative and not self.can_debit(hours):
            raise ValueError(f"Saldo insuficiente. Saldo atual: {self.current_balance}h, tentativa de débito: {hours}h")
        
        balance_before = self.current_balance  # Capturar saldo antes da alteraçéo
        self.current_balance -= hours
        self.total_debited += hours
        self.last_transaction = datetime.now(timezone.utc)
        
        # Registrar transaçéo
        transaction = HourBankTransaction(
            user_id=self.user_id,
            transaction_type=transaction_type,
            hours=-hours,  # Negativo para débito
            balance_before=balance_before,
            balance_after=self.current_balance,
            description=description
        )
        db.session.add(transaction)
    
    def admin_adjust_hours(self, hours_adjustment, transaction_type=HourBankTransactionType.AJUSTE, description=""):
        """Ajusta horas permitindo saldo negativo (só para admins)"""
        balance_before = self.current_balance
        self.current_balance += hours_adjustment
        
        if hours_adjustment > 0:
            self.total_credited += hours_adjustment
        else:
            self.total_debited += abs(hours_adjustment)
            
        self.last_transaction = datetime.now(timezone.utc)
        
        # Registrar transaçéo
        transaction = HourBankTransaction(
            user_id=self.user_id,
            transaction_type=transaction_type,
            hours=hours_adjustment,
            balance_before=balance_before,
            balance_after=self.current_balance,
            description=description
        )
        db.session.add(transaction)
    
    def __repr__(self):
        return f'<HourBank {self.user.nome if self.user else "N/A"} - {self.formatted_balance}>'

class HourBankTransaction(db.Model):
    """Histórico de transações do banco de horas"""
    __tablename__ = 'hour_bank_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False)
    transaction_type = db.Column(db.Enum(HourBankTransactionType), nullable=False)
    hours = db.Column(db.Float, nullable=False)  # Positivo para crédito, negativo para débito
    balance_before = db.Column(db.Float, nullable=True)
    balance_after = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    reference_date = db.Column(db.Date, nullable=True)  # Data de referência (ex: data do ponto)
    overtime_request_id = db.Column(db.Integer, db.ForeignKey('overtime_requests.id'), nullable=True)
    time_record_id = db.Column(db.Integer, db.ForeignKey('time_records.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)  # Data de expiraçéo para créditos
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id], overlaps="banco_horas_transacoes,usuario")
    overtime_request = db.relationship('OvertimeRequest', foreign_keys=[overtime_request_id])
    time_record = db.relationship('TimeRecord', foreign_keys=[time_record_id])
    creator = db.relationship('User', foreign_keys=[created_by], overlaps="banco_horas_transacoes,usuario")
    
    @property
    def is_credit(self):
        return self.hours > 0
    
    @property
    def is_debit(self):
        return self.hours < 0
    
    @property
    def absolute_hours(self):
        return abs(self.hours)
    
    @property
    def formatted_hours(self):
        """Retorna horas formatadas"""
        hours = int(abs(self.hours))
        minutes = int((abs(self.hours) % 1) * 60)
        sign = "+" if self.is_credit else "-"
        return f"{sign}{hours}h {minutes}m"
    
    @property
    def is_expired(self):
        """Verifica se a transaçéo expirou"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def __repr__(self):
        return f'<HourBankTransaction {self.user.nome if self.user else "N/A"} - {self.formatted_hours}>'

class HourCompensation(db.Model):
    """Compensações de horas (folgas programadas)"""
    __tablename__ = 'hour_compensations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False)
    requested_date = db.Column(db.Date, nullable=False)  # Data solicitada para compensaçéo
    hours_to_compensate = db.Column(db.Float, nullable=False)  # Horas a compensar
    justification = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(CompensationStatus), default=CompensationStatus.PENDENTE, nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    applied_at = db.Column(db.DateTime, nullable=True)  # Quando a compensaçéo foi aplicada
    rejection_reason = db.Column(db.Text, nullable=True)
    hour_bank_transaction_id = db.Column(db.Integer, db.ForeignKey('hour_bank_transactions.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id])
    approver = db.relationship('User', foreign_keys=[approved_by])
    bank_transaction = db.relationship('HourBankTransaction', foreign_keys=[hour_bank_transaction_id])
    
    @property
    def is_pending(self):
        return self.status == CompensationStatus.PENDENTE
    
    @property
    def is_applied(self):
        return self.status == CompensationStatus.APLICADA
    
    @property
    def formatted_hours(self):
        """Retorna horas formatadas"""
        hours = int(self.hours_to_compensate)
        minutes = int((self.hours_to_compensate % 1) * 60)
        return f"{hours}h {minutes}m"
    
    def can_apply(self):
        """Verifica se a compensaçéo pode ser aplicada"""
        if not self.user.hour_bank:
            return False
        return self.user.hour_bank.can_debit(self.hours_to_compensate)
    
    def __repr__(self):
        return f'<HourCompensation {self.user.nome if self.user else "N/A"} - {self.requested_date}>'

class OvertimeLimits(db.Model):
    """Limites de horas extras por tipo de usuário ou departamento"""
    __tablename__ = 'overtime_limits'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_type = db.Column(db.Enum(UserType), nullable=True)  # Aplicável a tipo de usuário
    work_class_id = db.Column(db.Integer, db.ForeignKey('work_classes.id'), nullable=True)  # Ou classe específica
    daily_limit = db.Column(db.Float, default=4.0, nullable=False)
    weekly_limit = db.Column(db.Float, default=16.0, nullable=False)
    monthly_limit = db.Column(db.Float, default=60.0, nullable=False)
    yearly_limit = db.Column(db.Float, default=600.0, nullable=False)
    requires_approval_after = db.Column(db.Float, default=2.0, nullable=False)  # Horas que requerem aprovaçéo
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    work_class = db.relationship('WorkClass', foreign_keys=[work_class_id])
    
    def __repr__(self):
        return f'<OvertimeLimits {self.name}>'


class FileUpload(db.Model):
    """Modelo para gerenciar uploads de arquivos"""
    __tablename__ = 'file_uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    download_count = db.Column(db.Integer, default=0, nullable=False)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    description = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[uploaded_by])
    
    @property
    def formatted_size(self):
        """Retorna tamanho formatado do arquivo"""
        return format_file_size(self.file_size)
    
    @property
    def file_extension(self):
        """Retorna extenséo do arquivo"""
        return os.path.splitext(self.filename)[1].lower()
    
    @property
    def is_image(self):
        """Verifica se o arquivo é uma imagem"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']
        return self.file_extension in image_extensions
    
    @property
    def is_document(self):
        """Verifica se o arquivo é um documento"""
        doc_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf']
        return self.file_extension in doc_extensions
    
    @property
    def is_archive(self):
        """Verifica se o arquivo é um arquivo compactado"""
        archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']
        return self.file_extension in archive_extensions
    
    def increment_download_count(self):
        """Incrementa o contador de downloads"""
        self.download_count += 1
        db.session.commit()
    
    def get_icon_class(self):
        """Retorna classe CSS do ícone baseado no tipo de arquivo"""
        if self.is_image:
            return 'fas fa-image text-primary'
        elif self.is_document:
            return 'fas fa-file-alt text-info'
        elif self.is_archive:
            return 'fas fa-file-archive text-warning'
        elif self.file_extension == '.pdf':
            return 'fas fa-file-pdf text-danger'
        elif self.file_extension in ['.mp4', '.avi', '.mov', '.wmv', '.flv']:
            return 'fas fa-film text-secondary'
        elif self.file_extension in ['.mp3', '.wav', '.ogg', '.flac']:
            return 'fas fa-music text-success'
        else:
            return 'fas fa-file text-muted'
    
    def __repr__(self):
        return f'<FileUpload {self.filename}>'


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


class HourBankHistory(db.Model):
    """Histórico de alterações no banco de horas dos usuários"""
    __tablename__ = 'hour_bank_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey(USERS_TABLE_ID), nullable=False)
    
    # Valores do banco de horas
    old_balance = db.Column(db.Float, nullable=False, default=0.0)
    adjustment = db.Column(db.Float, nullable=False)
    new_balance = db.Column(db.Float, nullable=False)
    
    # Detalhes da operaçéo
    reason = db.Column(db.Text, nullable=False)
    operation_type = db.Column(db.String(50), default='MANUAL_ADJUSTMENT')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    user = db.relationship('User', foreign_keys=[user_id], backref='hour_bank_history')
    admin = db.relationship('User', foreign_keys=[admin_id])
    
    @property
    def adjustment_formatted(self):
        """Retorna o ajuste formatado com sinal"""
        if self.adjustment >= 0:
            return f"+{self.adjustment:.1f}h"
        else:
            return f"{self.adjustment:.1f}h"
    
    @property
    def is_positive_adjustment(self):
        """Verifica se o ajuste foi positivo"""
        return self.adjustment > 0
    
    @property
    def is_negative_adjustment(self):
        """Verifica se o ajuste foi negativo"""
        return self.adjustment < 0
    
    @property
    def created_at_formatted(self):
        """Retorna data formatada"""
        return self.created_at.strftime('%d/%m/%Y %H:%M')
    
    def __repr__(self):
        return (f'<HourBankHistory User:{self.user_id} '
                f'Admin:{self.admin_id} Adjustment:{self.adjustment:.1f}h>')


