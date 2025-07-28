import click
from flask import current_app
from app import db
from app.models import User, UserType, SystemConfig
from app.utils import backup_database
import os
from datetime import datetime

def register_cli_commands(app):
    """Registra comandos CLI personalizados"""
    
    @app.cli.command()
    def init_db():
        """Inicializa o banco de dados"""
        db.create_all()
        click.echo('Banco de dados inicializado.')
    
    @app.cli.command()
    @click.option('--email', prompt='Email do admin', help='Email do administrador')
    @click.option('--password', prompt='Senha', hide_input=True, help='Senha do administrador')
    @click.option('--nome', prompt='Nome', help='Nome do administrador')
    @click.option('--sobrenome', prompt='Sobrenome', help='Sobrenome do administrador')
    @click.option('--cpf', prompt='CPF', help='CPF do administrador')
    def create_admin(email, password, nome, sobrenome, cpf):
        """Cria um usuário administrador"""
        # Verificar se já existe
        if User.query.filter_by(email=email).first():
            click.echo('Usuário com este email já existe.')
            return
        
        if User.query.filter_by(cpf=cpf).first():
            click.echo('Usuário com este CPF já existe.')
            return
        
        # Criar admin
        admin = User(
            email=email,
            cpf=cpf,
            nome=nome,
            sobrenome=sobrenome,
            user_type=UserType.ADMIN
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        click.echo(f'Administrador {email} criado com sucesso!')
    
    @app.cli.command()
    def backup():
        """Cria backup do banco de dados"""
        success, result = backup_database()
        if success:
            click.echo(f'Backup criado: {result}')
        else:
            click.echo(f'Erro ao criar backup: {result}')
    
    @app.cli.command()
    @click.option('--days', default=30, help='Dias de logs para manter')
    def cleanup_logs(days):
        """Remove logs antigos"""
        from app.models import SecurityLog
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = SecurityLog.query.filter(
            SecurityLog.created_at < cutoff_date
        ).delete()
        
        db.session.commit()
        click.echo(f'{deleted} logs removidos (mais antigos que {days} dias).')
    
    @app.cli.command()
    def init_config():
        """Inicializa configurações padrão do sistema"""
        configs = [
            ('work_hours_per_day', '8', 'Horas de trabalho por dia'),
            ('overtime_threshold', '8', 'Limite de horas para considerar extra'),
            ('backup_retention_days', '30', 'Dias para manter backups'),
            ('notification_retention_days', '90', 'Dias para manter notificações'),
            ('max_file_size_mb', '16', 'Tamanho máximo de arquivo em MB'),
        ]
        
        for chave, valor, descricao in configs:
            config = SystemConfig.query.filter_by(chave=chave).first()
            if not config:
                config = SystemConfig(
                    chave=chave,
                    valor=valor,
                    descricao=descricao
                )
                db.session.add(config)
        
        db.session.commit()
        click.echo('Configurações padrão inicializadas.')
    
    @app.cli.command()
    def reset_db():
        """CUIDADO: Remove e recria todo o banco de dados"""
        if click.confirm('ATENÇÃO: Isso irá apagar TODOS os dados. Continuar?'):
            db.drop_all()
            db.create_all()
            click.echo('Banco de dados resetado.')
    
    @app.cli.command()
    @click.option('--email', help='Email do usuário')
    def promote_admin(email):
        """Promove um usuário a administrador"""
        if not email:
            email = click.prompt('Email do usuário')
        
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo('Usuário não encontrado.')
            return
        
        user.user_type = UserType.ADMIN
        db.session.commit()
        
        click.echo(f'Usuário {email} promovido a administrador.')
    
    @app.cli.command()
    def list_users():
        """Lista todos os usuários"""
        users = User.query.order_by(User.nome).all()
        
        click.echo(f'{"ID":<5} {"Nome":<25} {"Email":<30} {"Tipo":<12} {"Ativo"}')
        click.echo('-' * 80)
        
        for user in users:
            status = 'Sim' if user.is_active else 'Não'
            click.echo(f'{user.id:<5} {user.nome_completo:<25} {user.email:<30} {user.user_type.value:<12} {status}')
    
    @app.cli.command()
    @click.option('--user-id', type=int, help='ID do usuário')
    def toggle_user_status(user_id):
        """Ativa/desativa um usuário"""
        if not user_id:
            user_id = click.prompt('ID do usuário', type=int)
        
        user = User.query.get(user_id)
        if not user:
            click.echo('Usuário não encontrado.')
            return
        
        user.is_active = not user.is_active
        status = 'ativado' if user.is_active else 'desativado'
        db.session.commit()
        
        click.echo(f'Usuário {user.email} {status}.')
    
    @app.cli.command()
    def stats():
        """Mostra estatísticas do sistema"""
        from app.models import TimeRecord, MedicalAttestation, Notification
        
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        admins = User.query.filter_by(user_type=UserType.ADMIN).count()
        
        total_records = TimeRecord.query.count()
        today_records = TimeRecord.query.filter_by(data=datetime.utcnow().date()).count()
        
        pending_attestations = MedicalAttestation.query.filter_by(
            status='pendente'
        ).count()
        
        unread_notifications = Notification.query.filter_by(lida=False).count()
        
        click.echo('=== ESTATÍSTICAS DO SISTEMA ===')
        click.echo(f'Usuários totais: {total_users}')
        click.echo(f'Usuários ativos: {active_users}')
        click.echo(f'Administradores: {admins}')
        click.echo(f'Registros de ponto: {total_records}')
        click.echo(f'Registros hoje: {today_records}')
        click.echo(f'Atestados pendentes: {pending_attestations}')
        click.echo(f'Notificações não lidas: {unread_notifications}')
    
    @app.cli.command()
    def test_email():
        """Testa configuração de email"""
        try:
            # Aqui você pode implementar teste de email
            click.echo('Teste de email não implementado ainda.')
        except Exception as e:
            click.echo(f'Erro no teste de email: {e}')
            click.echo(f'Erro no teste de email: {e}')
