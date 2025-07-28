from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, TextAreaField, DateField, TimeField, HiddenField, FloatField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional, NumberRange
from wtforms.widgets import TextArea
from app.models import User, UserType, AttestationType, OvertimeType, db
import re

class LoginForm(FlaskForm):
    """Formulário de login"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    """Formulário de cadastro"""
    nome = StringField('Nome', validators=[DataRequired(), Length(min=2, max=50)])
    sobrenome = StringField('Sobrenome', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    cpf = StringField('CPF', validators=[DataRequired(), Length(min=11, max=14)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmar Senha', 
                             validators=[DataRequired(), EqualTo('password', message='Senhas devem ser iguais')])
    user_type = SelectField('Tipo de Usuário', 
                           choices=[(UserType.TRABALHADOR.value, 'Trabalhador'), 
                                   (UserType.ESTAGIARIO.value, 'Estagiário')],
                           default=UserType.TRABALHADOR.value)
    foto_perfil = FileField('Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    user_message = TextAreaField('Mensagem (Opcional)', 
                                validators=[Optional(), Length(max=500)],
                                description='Mensagem opcional para o administrador')
    
    def validate_email(self, email):
        user = User.query.filter(User.email.ilike(email.data)).first()
        if user:
            raise ValidationError('Email já cadastrado.')
    
    def validate_cpf(self, cpf):
        # Remove caracteres especiais
        cpf_numbers = re.sub(r'[^0-9]', '', cpf.data)
        
        # Verifica se tem 11 dígitos
        if len(cpf_numbers) != 11:
            raise ValidationError('CPF deve ter 11 dígitos.')
        
        # Verifica se não são todos iguais
        if len(set(cpf_numbers)) == 1:
            raise ValidationError('CPF inválido.')
        
        # Verifica se já existe
        user = User.query.filter_by(cpf=cpf_numbers).first()
        if user:
            raise ValidationError('CPF já cadastrado.')
        
        # Formata o CPF
        cpf.data = f"{cpf_numbers[:3]}.{cpf_numbers[3:6]}.{cpf_numbers[6:9]}-{cpf_numbers[9:]}"

class ForgotPasswordForm(FlaskForm):
    """Formulário de recuperação de senha"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    cpf = StringField('CPF', validators=[DataRequired(), Length(min=11, max=14)])
    
    # Removemos as validações individuais para fazer a validação conjunta na rota

class ResetPasswordForm(FlaskForm):
    """Formulário de redefinição de senha"""
    password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmar Nova Senha', 
                             validators=[DataRequired(), EqualTo('password', message='Senhas devem ser iguais')])

class EditProfileForm(FlaskForm):
    """Formulário de edição de perfil"""
    nome = StringField('Nome', validators=[DataRequired(), Length(min=2, max=50)])
    sobrenome = StringField('Sobrenome', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    cargo = StringField('Cargo', validators=[Optional(), Length(max=100)])
    avatar = FileField('Nova Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    foto_perfil = FileField('Nova Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    
    # Campos para alteração de senha
    senha_atual = PasswordField('Senha Atual', validators=[Optional()])
    nova_senha = PasswordField('Nova Senha', validators=[Optional(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Nova Senha', validators=[
        Optional(), 
        EqualTo('nova_senha', message='As senhas devem ser iguais')
    ])
    
    def __init__(self, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email
    
    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter(User.email.ilike(email.data)).first()
            if user:
                raise ValidationError('Email já cadastrado.')

class TimeRecordForm(FlaskForm):
    """Formulário de registro de ponto"""
    data = DateField('Data', validators=[DataRequired()])
    entrada = TimeField('Entrada', validators=[Optional()])
    saida_almoco = TimeField('Saída para Almoço', validators=[Optional()])
    volta_almoco = TimeField('Volta do Almoço', validators=[Optional()])
    saida = TimeField('Saída', validators=[Optional()])
    observacoes = TextAreaField('Observações')
    justificativa_edicao = TextAreaField('Justificativa para Edição')
    
    def validate_saida_almoco(self, saida_almoco):
        if saida_almoco.data and self.entrada.data:
            if saida_almoco.data <= self.entrada.data:
                raise ValidationError('Saída para almoço deve ser posterior à entrada.')
    
    def validate_volta_almoco(self, volta_almoco):
        if volta_almoco.data and self.saida_almoco.data:
            if volta_almoco.data <= self.saida_almoco.data:
                raise ValidationError('Volta do almoço deve ser posterior à saída para almoço.')
    
    def validate_saida(self, saida):
        if saida.data:
            if self.volta_almoco.data and saida.data <= self.volta_almoco.data:
                raise ValidationError('Saída deve ser posterior à volta do almoço.')
            elif not self.volta_almoco.data and self.entrada.data and saida.data <= self.entrada.data:
                raise ValidationError('Saída deve ser posterior à entrada.')

class MedicalAttestationForm(FlaskForm):
    """Formulário de atestado médico"""
    tipo = SelectField('Tipo de Atestado', 
                      choices=[(AttestationType.MEDICO.value, 'Médico'),
                              (AttestationType.ODONTOLOGICO.value, 'Odontológico'),
                              (AttestationType.PSICOLOGICO.value, 'Psicológico'),
                              (AttestationType.OUTROS.value, 'Outros')],
                      default=AttestationType.MEDICO.value)
    data_inicio = DateField('Data de Início', validators=[DataRequired()])
    data_fim = DateField('Data de Fim', validators=[DataRequired()])
    cid = StringField('CID (opcional)', validators=[Optional(), Length(max=10)])
    medico_clinica = StringField('Médico/Clínica', validators=[Optional(), Length(max=200)])
    observacoes = TextAreaField('Observações')
    arquivo = FileField('Arquivo do Atestado', 
                       validators=[DataRequired(), FileAllowed(['pdf', 'jpg', 'png', 'jpeg'], 
                                                             'Apenas PDF ou imagens!')])
    
    def validate_data_fim(self, data_fim):
        if data_fim.data < self.data_inicio.data:
            raise ValidationError('Data de fim deve ser posterior à data de início.')

class ApproveAttestationForm(FlaskForm):
    """Formulário de aprovação de atestado"""
    motivo_rejeicao = TextAreaField('Motivo da Rejeição (se aplicável)')

class NotificationForm(FlaskForm):
    """Formulário de notificação"""
    titulo = StringField('Título', validators=[DataRequired(), Length(max=200)])
    mensagem = TextAreaField('Mensagem', validators=[DataRequired()])
    destinatarios = SelectField('Destinatários', 
                               choices=[('todos', 'Todos os usuários'),
                                       ('trabalhadores', 'Apenas trabalhadores'),
                                       ('estagiarios', 'Apenas estagiários'),
                                       ('admins', 'Apenas administradores'),
                                       ('individual', 'Usuário específico')])
    usuario_individual = SelectField('Usuário', 
                                    choices=[],
                                    validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(NotificationForm, self).__init__(*args, **kwargs)
        # Carregar lista de usuários ativos
        from app.models import User
        usuarios = User.query.filter_by(is_active=True).order_by(User.nome, User.sobrenome).all()
        self.usuario_individual.choices = [('', 'Selecione um usuário...')]
        self.usuario_individual.choices.extend([
            (str(u.id), f"{u.nome_completo} ({u.email})") for u in usuarios
        ])

class UserManagementForm(FlaskForm):
    """Formulário de gestão de usuários (admin)"""
    nome = StringField('Nome', validators=[DataRequired(), Length(min=2, max=50)])
    sobrenome = StringField('Sobrenome', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    cpf = StringField('CPF', validators=[DataRequired(), Length(min=11, max=14)])
    password = PasswordField('Senha', validators=[Optional(), Length(min=6)])
    password2 = PasswordField('Confirmar Senha', 
                             validators=[Optional(), EqualTo('password', message='Senhas devem ser iguais')])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    cargo = StringField('Cargo', validators=[Optional(), Length(max=100)])
    foto_perfil = FileField('Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    user_type = SelectField('Tipo de Usuário', 
                           choices=[(UserType.ADMIN.value, 'Administrador'),
                                   (UserType.TRABALHADOR.value, 'Trabalhador'), 
                                   (UserType.ESTAGIARIO.value, 'Estagiário')])
    work_class_id = SelectField('Classe de Trabalho', 
                               choices=[],
                               validators=[Optional()])
    is_active = SelectField('Status', 
                           choices=[('1', 'Ativo'), ('0', 'Inativo')],
                           coerce=int,
                           default='1')
    
    # Campos para edição de senha (opcionais)
    nova_senha = PasswordField('Nova Senha', validators=[Optional(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Nova Senha', 
                                   validators=[Optional(), EqualTo('nova_senha', message='Senhas devem ser iguais')])
    
    def __init__(self, original_email=None, original_cpf=None, *args, **kwargs):
        super(UserManagementForm, self).__init__(*args, **kwargs)
        self.original_email = original_email
        self.original_cpf = original_cpf
        
        # Carregar classes de trabalho
        from app.models import WorkClass
        classes = WorkClass.query.filter_by(is_active=True).order_by(WorkClass.name).all()
        self.work_class_id.choices = [('', 'Configuração Padrão')]
        self.work_class_id.choices.extend([(str(c.id), f"{c.name} ({c.daily_work_hours}h)") for c in classes])
    
    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter(User.email.ilike(email.data)).first()
            if user:
                raise ValidationError('Email já cadastrado.')
    
    def validate_cpf(self, cpf):
        # Remove caracteres especiais
        cpf_numbers = re.sub(r'[^0-9]', '', cpf.data)
        
        if cpf_numbers != self.original_cpf:
            user = User.query.filter_by(cpf=cpf_numbers).first()
            if user:
                raise ValidationError('CPF já cadastrado.')
        
        # Formata o CPF
        cpf.data = f"{cpf_numbers[:3]}.{cpf_numbers[3:6]}.{cpf_numbers[6:9]}-{cpf_numbers[9:]}"

class ReportForm(FlaskForm):
    """Formulário de relatórios"""
    data_inicio = DateField('Data de Início', validators=[DataRequired()])
    data_fim = DateField('Data de Fim', validators=[DataRequired()])
    user_id = SelectField('Funcionário', coerce=int, choices=[], validators=[Optional()])
    formato = SelectField('Formato', 
                         choices=[('pdf', 'PDF'), ('excel', 'Excel')],
                         default='pdf')
    
    def validate_data_fim(self, data_fim):
        if data_fim.data < self.data_inicio.data:
            raise ValidationError('Data de fim deve ser posterior à data de início.')

class SearchForm(FlaskForm):
    """Formulário de busca"""
    q = StringField('Buscar', validators=[DataRequired()])

class WorkClassForm(FlaskForm):
    """Formulário para criar/editar classes de trabalho"""
    name = StringField('Nome da Classe', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    daily_work_hours = SelectField('Horas Diárias de Trabalho', 
                               choices=[
                                   ('4.0', '4 horas'),
                                   ('6.0', '6 horas'),
                                   ('8.0', '8 horas'),
                                   ('10.0', '10 horas'),
                                   ('12.0', '12 horas'),
                               ],
                               default='8.0')
    lunch_hours = SelectField('Horas de Almoço', 
                              choices=[
                                  ('0.5', '30 minutos'),
                                  ('1.0', '1 hora'),
                                  ('1.5', '1 hora e 30 minutos'),
                                  ('2.0', '2 horas'),
                              ],
                              default='1.0')
    
    def __init__(self, original_class_id=None, *args, **kwargs):
        super(WorkClassForm, self).__init__(*args, **kwargs)
        self.original_class_id = original_class_id
    
    def validate_name(self, name):
        from app.models import WorkClass
        # Verifica se já existe uma classe com este nome
        existing = WorkClass.query.filter_by(name=name.data).first()
        if existing:
            # Se estamos editando, verificar se não é a mesma classe
            if self.original_class_id and existing.id != self.original_class_id:
                raise ValidationError('Já existe uma classe de trabalho com este nome.')
            elif not self.original_class_id:
                # Se não tem original_class_id, é uma nova classe
                raise ValidationError('Já existe uma classe de trabalho com este nome.')

class AssignWorkClassForm(FlaskForm):
    """Formulário para atribuir classe de trabalho a usuários"""
    user_ids = HiddenField('IDs dos Usuários')
    work_class_id = SelectField('Classe de Trabalho', 
                               choices=[],
                               validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        super(AssignWorkClassForm, self).__init__(*args, **kwargs)
        from app.models import WorkClass
        # Carregar classes de trabalho ativas
        classes = WorkClass.query.filter_by(is_active=True).order_by(WorkClass.name).all()
        self.work_class_id.choices = [(str(c.id), f"{c.name} ({c.daily_work_hours}h)") for c in classes]
        # Adicionar opção para remover classe
        self.work_class_id.choices.insert(0, ('', 'Usar configuração padrão'))

class BulkWorkClassForm(FlaskForm):
    """Formulário para atribuir classe de trabalho em massa"""
    user_type = SelectField('Tipo de Usuário', 
                           choices=[
                               ('', 'Todos os tipos'),
                               ('admin', 'Administradores'),
                               ('trabalhador', 'Trabalhadores'),
                               ('estagiario', 'Estagiários'),
                           ],
                           default='')
    work_class_id = SelectField('Nova Classe de Trabalho', 
                               choices=[],
                               validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        super(BulkWorkClassForm, self).__init__(*args, **kwargs)
        from app.models import WorkClass
        # Carregar classes de trabalho ativas
        classes = WorkClass.query.filter_by(is_active=True).order_by(WorkClass.name).all()
        self.work_class_id.choices = [(str(c.id), f"{c.name} ({c.daily_work_hours}h)") for c in classes]
        # Adicionar opção para remover classe
        self.work_class_id.choices.insert(0, ('', 'Usar configuração padrão'))

class EmptyForm(FlaskForm):
    """Formulário vazio para botões CSRF"""
    pass

class UserApprovalForm(FlaskForm):
    """Formulário para aprovar/rejeitar usuários"""
    action = HiddenField('Action', validators=[DataRequired()])
    admin_notes = TextAreaField('Notas do Administrador', 
                               validators=[Optional(), Length(max=500)],
                               description='Notas internas para controle')
    rejection_reason = TextAreaField('Motivo da Rejeição', 
                                   validators=[Optional(), Length(max=500)],
                                   description='Motivo da rejeição (será enviado ao usuário)')

class localConfigForm(FlaskForm):
    """Formulário para configuração do local"""
    app_key = StringField('App Key', validators=[DataRequired(), Length(min=10, max=255)], 
                         render_kw={"placeholder": "4fdh28kcr14hepi"})
    app_secret = StringField('App Secret', validators=[DataRequired(), Length(min=10, max=255)], 
                            render_kw={"placeholder": "6h8iy57xplni7x6"})
    access_token = StringField('Token de Acesso (Opcional)', validators=[Optional(), Length(min=10)],
                              render_kw={"placeholder": "Deixe vazio para usar refresh token"})
    refresh_token = StringField('Refresh Token (Opcional)', validators=[Optional(), Length(min=10)],
                               render_kw={"placeholder": "Token de longa duração"})
    backup_folder = StringField('Pasta de Backup', validators=[DataRequired(), Length(min=1, max=255)], 
                               default='/SKPONTO_Backups')
    retention_days = SelectField('Retenção de Backup (dias)', 
                                choices=[('7', '7 dias'), ('15', '15 dias'), ('30', '30 dias'), 
                                        ('60', '60 dias'), ('90', '90 dias')],
                                default='30')
    is_active = SelectField('Status', 
                           choices=[('True', 'Ativo'), ('False', 'Inativo')],
                           default='True')

class BackupScheduleForm(FlaskForm):
    """Formulário para agendamento de backup"""
    backup_type = SelectField('Tipo de Backup', 
                             choices=[('AUTOMATICO', 'Automático'), ('COMPLETO', 'Completo'), 
                                     ('INCREMENTAL', 'Incremental')],
                             default='AUTOMATICO')
    schedule_time = TimeField('Horário', validators=[DataRequired()])
    is_active = SelectField('Status do Agendamento', 
                           choices=[('True', 'Ativo'), ('False', 'Inativo')],
                           default='True')

# ============================================================================
# FORMULÁRIOS DO SISTEMA DE BANCO DE HORAS
# ============================================================================

class OvertimeRequestForm(FlaskForm):
    """Formulário para solicitação de horas extras"""
    date = DateField('Data', validators=[DataRequired()],
                    description='Data em que as horas extras serão realizadas')
    start_time = TimeField('Horário de Início', validators=[DataRequired()],
                          description='Horário de início das horas extras')
    end_time = TimeField('Horário de Fim', validators=[DataRequired()],
                        description='Horário de fim das horas extras')
    overtime_type = SelectField('Tipo de Hora Extra', 
                               choices=[
                                   (OvertimeType.NORMAL.value, 'Normal (1.5x)'),
                                   (OvertimeType.URGENTE.value, 'Urgente (2.0x)'),
                                   (OvertimeType.PLANEJADA.value, 'Planejada (1.5x)'),
                                   (OvertimeType.FERIADO.value, 'Feriado (2.5x)'),
                                   (OvertimeType.DOMINGO.value, 'Domingo (2.0x)'),
                                   (OvertimeType.NOTURNA.value, 'Noturna (1.2x)')
                               ],
                               default=OvertimeType.NORMAL.value,
                               validators=[DataRequired()])
    justification = TextAreaField('Justificativa', 
                                 validators=[DataRequired(), Length(min=10, max=500)],
                                 description='Explicação detalhada da necessidade das horas extras')
    
    def validate_end_time(self, field):
        """Valida se horário de fim é depois do início"""
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError('Horário de fim deve ser posterior ao horário de início.')
    
    def validate_date(self, field):
        """Valida se a data não é no passado"""
        from datetime import date
        if field.data and field.data < date.today():
            raise ValidationError('Não é possível solicitar horas extras para datas passadas.')

class OvertimeApprovalForm(FlaskForm):
    """Formulário para aprovação/rejeição de horas extras"""
    action = HiddenField('Action', validators=[DataRequired()])
    rejection_reason = TextAreaField('Motivo da Rejeição', 
                                   validators=[Optional(), Length(max=500)],
                                   description='Motivo da rejeição (será enviado ao solicitante)')
    actual_hours = FloatField('Horas Reais Trabalhadas',
                             validators=[Optional(), NumberRange(min=0, max=24)],
                             description='Horas realmente trabalhadas (opcional)')

class HourCompensationForm(FlaskForm):
    """Formulário para solicitação de compensação de horas"""
    requested_date = DateField('Data Solicitada', validators=[DataRequired()],
                              description='Data em que deseja usar as horas do banco')
    hours_to_compensate = FloatField('Horas a Compensar', 
                                   validators=[DataRequired(), NumberRange(min=0.5, max=8)],
                                   description='Quantidade de horas a compensar (máximo 8h por dia)')
    justification = TextAreaField('Justificativa', 
                                 validators=[Optional(), Length(max=500)],
                                 description='Motivo da solicitação de compensação')
    
    def validate_requested_date(self, field):
        """Valida se a data é futura"""
        from datetime import date
        if field.data and field.data <= date.today():
            raise ValidationError('A data de compensação deve ser futura.')

class HourCompensationApprovalForm(FlaskForm):
    """Formulário para aprovação de compensação de horas"""
    action = HiddenField('Action', validators=[DataRequired()])
    rejection_reason = TextAreaField('Motivo da Rejeição', 
                                   validators=[Optional(), Length(max=500)],
                                   description='Motivo da rejeição (será enviado ao solicitante)')

class OvertimeSettingsForm(FlaskForm):
    """Formulário para configurações de horas extras do usuário"""
    max_daily_overtime = FloatField('Limite Diário (horas)', 
                                   validators=[DataRequired(), NumberRange(min=0, max=12)],
                                   default=4.0,
                                   description='Máximo de horas extras por dia')
    max_weekly_overtime = FloatField('Limite Semanal (horas)', 
                                    validators=[DataRequired(), NumberRange(min=0, max=60)],
                                    default=16.0,
                                    description='Máximo de horas extras por semana')
    max_monthly_overtime = FloatField('Limite Mensal (horas)', 
                                     validators=[DataRequired(), NumberRange(min=0, max=200)],
                                     default=60.0,
                                     description='Máximo de horas extras por mês')
    requires_approval = BooleanField('Requer Aprovação Prévia', 
                                   default=True,
                                   description='Horas extras precisam de aprovação prévia')
    auto_approval_limit = FloatField('Limite de Aprovação Automática (horas)', 
                                    validators=[DataRequired(), NumberRange(min=0, max=8)],
                                    default=2.0,
                                    description='Horas extras aprovadas automaticamente (até este limite)')
    overtime_multiplier_normal = FloatField('Multiplicador Normal', 
                                           validators=[DataRequired(), NumberRange(min=1, max=5)],
                                           default=1.5,
                                           description='Multiplicador para horas extras normais')
    overtime_multiplier_urgent = FloatField('Multiplicador Urgente', 
                                           validators=[DataRequired(), NumberRange(min=1, max=5)],
                                           default=2.0,
                                           description='Multiplicador para horas extras urgentes')
    overtime_multiplier_holiday = FloatField('Multiplicador Feriado', 
                                            validators=[DataRequired(), NumberRange(min=1, max=5)],
                                            default=2.5,
                                            description='Multiplicador para horas extras em feriados')
    overtime_multiplier_sunday = FloatField('Multiplicador Domingo', 
                                           validators=[DataRequired(), NumberRange(min=1, max=5)],
                                           default=2.0,
                                           description='Multiplicador para horas extras em domingos')
    overtime_multiplier_night = FloatField('Multiplicador Noturno', 
                                          validators=[DataRequired(), NumberRange(min=1, max=5)],
                                          default=1.2,
                                          description='Multiplicador para adicional noturno')

class HourBankAdjustmentForm(FlaskForm):
    """Formulário para ajuste manual do banco de horas (admin)"""
    hours = FloatField('Horas', 
                      validators=[DataRequired(), NumberRange(min=-999, max=999)],
                      description='Horas a adicionar (positivo) ou remover (negativo)')
    description = TextAreaField('Descrição', 
                               validators=[DataRequired(), Length(min=5, max=500)],
                               description='Motivo do ajuste manual')
    reference_date = DateField('Data de Referência', 
                              validators=[Optional()],
                              description='Data de referência para o ajuste (opcional)')

class HourBankTransferForm(FlaskForm):
    """Formulário para transferência de horas entre usuários (admin)"""
    from_user_id = SelectField('De (Usuário)', 
                              choices=[],
                              validators=[DataRequired()],
                              description='Usuário que doará as horas')
    to_user_id = SelectField('Para (Usuário)', 
                            choices=[],
                            validators=[DataRequired()],
                            description='Usuário que receberá as horas')
    hours = FloatField('Horas a Transferir', 
                      validators=[DataRequired(), NumberRange(min=0.1, max=999)],
                      description='Quantidade de horas a transferir')
    description = TextAreaField('Descrição', 
                               validators=[DataRequired(), Length(min=5, max=500)],
                               description='Motivo da transferência')
    
    def __init__(self, *args, **kwargs):
        super(HourBankTransferForm, self).__init__(*args, **kwargs)
        # Carregar usuários ativos com banco de horas
        users = User.query.filter_by(is_active=True, is_approved=True).order_by(User.nome).all()
        user_choices = [(str(u.id), f"{u.nome_completo} ({u.email})") for u in users]
        self.from_user_id.choices = user_choices
        self.to_user_id.choices = user_choices
    
    def validate_to_user_id(self, field):
        """Valida se usuário de destino é diferente do origem"""
        if self.from_user_id.data and field.data:
            if self.from_user_id.data == field.data:
                raise ValidationError('Usuário de origem e destino devem ser diferentes.')

class OvertimeLimitsForm(FlaskForm):
    """Formulário para configuração de limites de horas extras"""
    name = StringField('Nome da Configuração', 
                      validators=[DataRequired(), Length(min=3, max=100)],
                      description='Nome identificador desta configuração')
    description = TextAreaField('Descrição', 
                               validators=[Optional(), Length(max=500)],
                               description='Descrição detalhada da configuração')
    user_type = SelectField('Tipo de Usuário', 
                           choices=[
                               ('', 'Todos os tipos'),
                               (UserType.ADMIN.value, 'Administradores'),
                               (UserType.TRABALHADOR.value, 'Trabalhadores'),
                               (UserType.ESTAGIARIO.value, 'Estagiários')
                           ],
                           default='',
                           description='Tipo de usuário ao qual se aplica')
    work_class_id = SelectField('Classe de Trabalho', 
                               choices=[],
                               description='Classe específica (opcional)')
    daily_limit = FloatField('Limite Diário (horas)', 
                            validators=[DataRequired(), NumberRange(min=0, max=12)],
                            default=4.0,
                            description='Máximo de horas extras por dia')
    weekly_limit = FloatField('Limite Semanal (horas)', 
                             validators=[DataRequired(), NumberRange(min=0, max=60)],
                             default=16.0,
                             description='Máximo de horas extras por semana')
    monthly_limit = FloatField('Limite Mensal (horas)', 
                              validators=[DataRequired(), NumberRange(min=0, max=200)],
                              default=60.0,
                              description='Máximo de horas extras por mês')
    yearly_limit = FloatField('Limite Anual (horas)', 
                             validators=[DataRequired(), NumberRange(min=0, max=2000)],
                             default=600.0,
                             description='Máximo de horas extras por ano')
    requires_approval_after = FloatField('Aprovação Necessária Após (horas)', 
                                        validators=[DataRequired(), NumberRange(min=0, max=12)],
                                        default=2.0,
                                        description='Horas que requerem aprovação prévia')
    is_active = BooleanField('Ativo', 
                            default=True,
                            description='Se esta configuração está ativa')
    
    def __init__(self, *args, **kwargs):
        super(OvertimeLimitsForm, self).__init__(*args, **kwargs)
        from app.models import WorkClass
        # Carregar classes de trabalho ativas
        classes = WorkClass.query.filter_by(is_active=True).order_by(WorkClass.name).all()
        self.work_class_id.choices = [('', 'Todas as classes')] + [(str(c.id), f"{c.name} ({c.daily_work_hours}h)") for c in classes]

class HourBankReportForm(FlaskForm):
    """Formulário para relatórios de banco de horas"""
    user_id = SelectField('Usuário', 
                         choices=[],
                         description='Usuário específico (deixe em branco para todos)')
    start_date = DateField('Data Inicial', 
                          validators=[Optional()],
                          description='Data inicial do relatório')
    end_date = DateField('Data Final', 
                        validators=[Optional()],
                        description='Data final do relatório')
    transaction_type = SelectField('Tipo de Transação', 
                                  choices=[
                                      ('', 'Todas'),
                                      ('CREDITO', 'Créditos'),
                                      ('DEBITO', 'Débitos'),
                                      ('COMPENSACAO', 'Compensações'),
                                      ('AJUSTE', 'Ajustes'),
                                      ('EXPIRACAO', 'Expirações')
                                  ],
                                  default='',
                                  description='Filtrar por tipo de transação')
    format_type = SelectField('Formato de Exportação', 
                             choices=[
                                 ('html', 'Visualizar na Tela'),
                                 ('pdf', 'PDF'),
                                 ('excel', 'Excel')
                             ],
                             default='html',
                             validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        super(HourBankReportForm, self).__init__(*args, **kwargs)
        # Carregar usuários com banco de horas
        users = User.query.filter_by(is_active=True, is_approved=True).order_by(User.nome).all()
        self.user_id.choices = [('', 'Todos os usuários')] + [(str(u.id), f"{u.nome_completo}") for u in users]
    
    def validate_end_date(self, field):
        """Valida se data final é posterior à inicial"""
        if self.start_date.data and field.data:
            if field.data < self.start_date.data:
                raise ValidationError('Data final deve ser posterior à data inicial.')
