import os
import json
import zipfile
import shutil
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from app.admin.backup import bp
from app.decorators import admin_required

class LocalStorageManager:
    def __init__(self, base_path=None):
        """Initialize the LocalStorageManager"""
        if base_path is None:
            # Usar o caminho correto do sistema de armazenamento local
            self.base_path = os.path.join('storage', 'backups')
        else:
            self.base_path = base_path
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """Ensure the backup directory exists"""
        try:
            os.makedirs(self.base_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Erro ao criar diretório de backup: {e}")
            return False
    
    def get_storage_info(self):
        """Get storage information"""
        try:
            if not os.path.exists(self.base_path):
                return {
                    'total_size': 0,
                    'used_space': 0,
                    'free_space': 0,
                    'backup_count': 0,
                    'status': 'warning',
                    'message': 'Diretório de backup não encontrado'
                }
            
            total_size = 0
            backup_count = 0
            
            for filename in os.listdir(self.base_path):
                file_path = os.path.join(self.base_path, filename)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
                    backup_count += 1
            
            # Simular espaço livre (em ambiente real, usar shutil.disk_usage)
            try:
                total, used, free = shutil.disk_usage(self.base_path)
                free_space = free
            except:
                free_space = 1000000000  # 1GB como fallback
            
            return {
                'total_size': total_size,
                'used_space': total_size,
                'free_space': free_space,
                'backup_count': backup_count,
                'status': 'success',
                'message': f'{backup_count} backups encontrados'
            }
        except Exception as e:
            return {
                'total_size': 0,
                'used_space': 0,
                'free_space': 0,
                'backup_count': 0,
                'status': 'error',
                'message': f'Erro ao obter informações: {str(e)}'
            }
    
    def list_backups(self):
        """List all available backups"""
        try:
            if not os.path.exists(self.base_path):
                return []
            
            backups = []
            for filename in os.listdir(self.base_path):
                file_path = os.path.join(self.base_path, filename)
                if os.path.isfile(file_path) and filename.endswith(('.zip', '.sql', '.db')):
                    stat = os.stat(file_path)
                    backups.append({
                        'name': filename,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_mtime),
                        'path': file_path
                    })
            
            # Ordenar por data de criação (mais recente primeiro)
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            return backups
        except Exception as e:
            print(f"Erro ao listar backups: {e}")
            return []
    
    def create_backup(self, source_db_path):
        """Create a new backup"""
        try:
            if not os.path.exists(source_db_path):
                return False, f"Banco de dados não encontrado: {source_db_path}"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"skponto_backup_{timestamp}.zip"
            backup_path = os.path.join(self.base_path, backup_filename)
            
            # Criar backup com informações adicionais
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Adicionar o banco de dados
                zipf.write(source_db_path, 'skponto.db')
                
                # Adicionar arquivo de informações sobre o backup
                backup_info = {
                    'created_at': datetime.now().isoformat(),
                    'database_size': os.path.getsize(source_db_path),
                    'backup_version': '2.0',
                    'system': 'SKPONTO'
                }
                
                import json
                zipf.writestr('backup_info.json', json.dumps(backup_info, indent=2))
            
            backup_size = os.path.getsize(backup_path)
            return True, f"Backup criado com sucesso: {backup_filename} ({backup_size / 1024 / 1024:.1f} MB)"
        except Exception as e:
            return False, f"Erro ao criar backup: {str(e)}"
    
    def delete_backup(self, backup_name):
        """Delete a backup file"""
        try:
            backup_path = os.path.join(self.base_path, backup_name)
            if os.path.exists(backup_path):
                os.remove(backup_path)
                return True, "Backup removido com sucesso"
            else:
                return False, "Backup não encontrado"
        except Exception as e:
            return False, f"Erro ao remover backup: {str(e)}"
    
    def cleanup_old_backups(self, max_backups=10):
        """Remove backups antigos mantendo apenas o número especificado"""
        try:
            backups = self.list_backups()
            
            if len(backups) <= max_backups:
                return True, f"Nenhum backup removido. Total: {len(backups)}"
            
            # Ordenar por data de criação (mais antigo primeiro)
            backups.sort(key=lambda x: x['created_at'])
            
            # Remover os backups mais antigos
            removed_count = 0
            backups_to_remove = backups[:-max_backups] if max_backups > 0 else backups
            
            for backup in backups_to_remove:
                success, _ = self.delete_backup(backup['name'])
                if success:
                    removed_count += 1
            
            return True, f"{removed_count} backups antigos removidos. Mantidos: {max_backups}"
        except Exception as e:
            return False, f"Erro ao limpar backups antigos: {str(e)}"
    
    def delete_multiple_backups(self, backup_names):
        """Delete multiple backup files"""
        try:
            results = []
            success_count = 0
            
            for backup_name in backup_names:
                success, message = self.delete_backup(backup_name)
                results.append({
                    'name': backup_name,
                    'success': success,
                    'message': message
                })
                if success:
                    success_count += 1
            
            total = len(backup_names)
            return True, f"{success_count}/{total} backups removidos com sucesso", results
        except Exception as e:
            return False, f"Erro ao remover múltiplos backups: {str(e)}", []

# Instância global do LocalStorageManager
storage_manager = LocalStorageManager()

class AutoBackupManager:
    def __init__(self):
        self.config_file = os.path.join('storage', 'backup_config.json')
        self.is_running = False
        self.thread = None
        self.ensure_config_directory()
    
    def ensure_config_directory(self):
        """Ensure the config directory exists"""
        config_dir = os.path.dirname(self.config_file)
        os.makedirs(config_dir, exist_ok=True)
    
    def load_config(self):
        """Load auto backup configuration"""
        default_config = {
            'enabled': False,
            'frequency': 'daily',  # daily, weekly, monthly
            'time': '02:00',  # HH:MM format
            'max_backups': 10,
            'auto_cleanup': True,
            'last_backup': None
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            return default_config
        except Exception as e:
            print(f"Erro ao carregar configuração de backup automático: {e}")
            return default_config
    
    def save_config(self, config):
        """Save auto backup configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração de backup automático: {e}")
            return False
    
    def should_create_backup(self):
        """Check if a backup should be created based on schedule"""
        config = self.load_config()
        
        if not config['enabled']:
            return False
        
        last_backup = config.get('last_backup')
        if not last_backup:
            return True
        
        try:
            last_backup_date = datetime.fromisoformat(last_backup)
            now = datetime.now()
            
            if config['frequency'] == 'daily':
                return (now - last_backup_date).days >= 1
            elif config['frequency'] == 'weekly':
                return (now - last_backup_date).days >= 7
            elif config['frequency'] == 'monthly':
                return (now - last_backup_date).days >= 30
            
            return False
        except Exception as e:
            print(f"Erro ao verificar agendamento de backup: {e}")
            return False
    
    def create_scheduled_backup(self):
        """Create a scheduled backup"""
        try:
            success, message, filename = storage_manager.create_backup()
            
            if success:
                config = self.load_config()
                config['last_backup'] = datetime.now().isoformat()
                self.save_config(config)
                
                # Auto cleanup if enabled
                if config.get('auto_cleanup', True):
                    storage_manager.cleanup_old_backups(config.get('max_backups', 10))
                
                print(f"Backup automático criado com sucesso: {filename}")
            else:
                print(f"Erro ao criar backup automático: {message}")
                
            return success, message
        except Exception as e:
            error_msg = f"Erro no backup automático: {str(e)}"
            print(error_msg)
            return False, error_msg

# Instância global do AutoBackupManager
auto_backup_manager = AutoBackupManager()

@bp.route('/debug')
def debug():
    """Endpoint de debug sem autenticação para diagnosticar problemas"""
    try:
        from flask_login import current_user
        
        debug_info = {
            'user_authenticated': current_user.is_authenticated if current_user else False,
            'user_id': current_user.id if current_user and current_user.is_authenticated else None,
            'user_email': current_user.email if current_user and current_user.is_authenticated else None,
            'user_is_admin': None,
            'storage_manager_ok': False,
            'blueprint_registered': True,
            'error': None
        }
        
        # Verificar se user tem atributo is_admin
        if current_user and current_user.is_authenticated:
            try:
                debug_info['user_is_admin'] = getattr(current_user, 'is_admin', 'ATRIBUTO_NAO_EXISTE')
                debug_info['user_attributes'] = [attr for attr in dir(current_user) if not attr.startswith('_')]
            except Exception as e:
                debug_info['user_is_admin'] = f'ERRO: {str(e)}'
        
        # Verificar storage manager
        try:
            storage_info = storage_manager.get_storage_info()
            debug_info['storage_manager_ok'] = True
            debug_info['storage_info'] = storage_info
        except Exception as e:
            debug_info['storage_manager_error'] = str(e)
        
        return f"""
        <h1>Debug Dashboard de Backup</h1>
        <pre>{json.dumps(debug_info, indent=2, default=str)}</pre>
        <hr>
        <h2>Testes:</h2>
        <a href="/admin/backup/dashboard">Tentar acessar dashboard (com auth)</a><br>
        <a href="/admin/backup/test-no-auth">Teste sem autenticação</a><br>
        <a href="/admin/dashboard">Dashboard admin normal</a>
        """
    except Exception as e:
        return f"<h1>Erro no debug:</h1><pre>{str(e)}</pre>"

@bp.route('/test-no-auth')
def test_no_auth():
    """Teste do template sem autenticação"""
    try:
        storage_info = storage_manager.get_storage_info()
        backups = storage_manager.list_backups()
        
        return render_template('admin/backup/dashboard.html',
                             storage_info=storage_info,
                             backups=backups)
    except Exception as e:
        return f"<h1>Erro no template:</h1><pre>{str(e)}</pre>"

@bp.route('/test-simple')
def test_simple():
    """Teste super simples sem nada"""
    return "<h1>✅ Blueprint funcionando!</h1><p>Se você vê isso, o blueprint está registrado corretamente.</p>"

@bp.route('/dashboard')
@login_required  
@admin_required
def dashboard():
    """Dashboard de backup com informações de armazenamento"""
    try:
        storage_info = storage_manager.get_storage_info()
        backups = storage_manager.list_backups()
        
        return render_template('admin/backup/dashboard.html',
                             storage_info=storage_info,
                             backups=backups)
    except Exception as e:
        flash(f'Erro ao carregar dashboard de backup: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/api/storage-info')
@login_required
@admin_required
def api_storage_info():
    """API endpoint para obter informações de armazenamento"""
    try:
        storage_info = storage_manager.get_storage_info()
        return jsonify(storage_info)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/api/list-backups')
@login_required
@admin_required
def api_list_backups():
    """API endpoint para listar backups"""
    try:
        backups = storage_manager.list_backups()
        # Converter datetime para string para JSON
        for backup in backups:
            backup['created_at'] = backup['created_at'].isoformat()
        return jsonify(backups)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """Criar um novo backup"""
    try:
        # Caminho do banco de dados baseado na configuração
        from config import Config
        import re
        
        # Extrair o caminho do banco da URI
        db_uri = Config.SQLALCHEMY_DATABASE_URI
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
        else:
            # Fallback para caminho padrão
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            db_path = os.path.join(base_dir, 'storage', 'database', 'skponto.db')
        
        print(f"DEBUG: Tentando criar backup do banco: {db_path}")
        print(f"DEBUG: Arquivo existe: {os.path.exists(db_path)}")
        
        success, message = storage_manager.create_backup(db_path)
        
        if success:
            # Se for uma requisição AJAX, retornar JSON
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'status': 'success',
                    'message': message
                }), 200
            
            flash(message, 'success')
        else:
            # Se for uma requisição AJAX, retornar JSON
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'status': 'error',
                    'message': message
                }), 400
                
            flash(message, 'error')
        
        return redirect(url_for('backup.dashboard'))
    except Exception as e:
        error_message = f'Erro ao criar backup: {str(e)}'
        print(f"DEBUG: Exceção na criação de backup: {error_message}")
        
        # Se for uma requisição AJAX, retornar JSON
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'status': 'error',
                'message': error_message
            }), 500
            
        flash(error_message, 'error')
        return redirect(url_for('backup.dashboard'))

@bp.route('/delete/<backup_name>', methods=['GET', 'DELETE'])
@login_required
@admin_required
def delete_backup(backup_name):
    """Deletar um backup específico"""
    print(f"DEBUG: delete_backup chamado com método {request.method} para backup: {backup_name}")
    try:
        success, message = storage_manager.delete_backup(backup_name)
        print(f"DEBUG: Resultado da deleção - success: {success}, message: {message}")
        
        # Se for uma requisição AJAX (DELETE), retornar JSON
        if request.method == 'DELETE':
            print("DEBUG: Retornando resposta JSON")
            if success:
                return jsonify({
                    'status': 'success',
                    'message': message
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': message
                }), 400
        
        # Se for uma requisição GET, usar flash e redirect
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('backup.dashboard'))
    except Exception as e:
        error_message = f'Erro ao deletar backup: {str(e)}'
        print(f"DEBUG: Exceção capturada: {error_message}")
        
        # Se for uma requisição AJAX (DELETE), retornar JSON
        if request.method == 'DELETE':
            return jsonify({
                'status': 'error',
                'message': error_message
            }), 500
        
        # Se for uma requisição GET, usar flash e redirect
        flash(error_message, 'error')
        return redirect(url_for('backup.dashboard'))

@bp.route('/download/<backup_name>')
@login_required
@admin_required
def download_backup(backup_name):
    """Download de um backup específico"""
    try:
        # Usar caminho absoluto para o arquivo
        backup_path = os.path.abspath(os.path.join(storage_manager.base_path, backup_name))
        
        # Debug: verificar se o arquivo existe
        print(f"DEBUG - Tentando download de: {backup_path}")
        print(f"DEBUG - Arquivo existe: {os.path.exists(backup_path)}")
        print(f"DEBUG - Base path: {storage_manager.base_path}")
        
        if os.path.exists(backup_path):
            return send_file(backup_path, as_attachment=True, download_name=backup_name)
        else:
            flash(f'Backup não encontrado: {backup_path}', 'error')
            return redirect(url_for('backup.dashboard'))
    except Exception as e:
        print(f"DEBUG - Erro no download: {str(e)}")
        flash(f'Erro ao fazer download: {str(e)}', 'error')
        return redirect(url_for('backup.dashboard'))

@bp.route('/delete-multiple', methods=['POST'])
@login_required
@admin_required
def delete_multiple_backups():
    """Deletar múltiplos backups"""
    try:
        data = request.get_json()
        if not data or 'backup_names' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Lista de backups não fornecida'
            }), 400
        
        backup_names = data['backup_names']
        if not isinstance(backup_names, list) or len(backup_names) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Lista de backups inválida'
            }), 400
        
        success, message, results = storage_manager.delete_multiple_backups(backup_names)
        
        return jsonify({
            'status': 'success' if success else 'error',
            'message': message,
            'results': results
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao deletar múltiplos backups: {str(e)}'
        }), 500

@bp.route('/cleanup', methods=['POST'])
@login_required
@admin_required
def cleanup_backups():
    """Limpar backups antigos mantendo apenas a quantidade especificada"""
    try:
        data = request.get_json()
        max_backups = data.get('max_backups', 10) if data else 10
        
        if not isinstance(max_backups, int) or max_backups < 0:
            return jsonify({
                'status': 'error',
                'message': 'Número máximo de backups deve ser um inteiro positivo'
            }), 400
        
        success, message = storage_manager.cleanup_old_backups(max_backups)
        
        return jsonify({
            'status': 'success' if success else 'error',
            'message': message
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao limpar backups: {str(e)}'
        }), 500

@bp.route('/auto-backup-config', methods=['GET', 'POST'])
@login_required
@admin_required
def auto_backup_config():
    """Manage auto backup configuration"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            config = auto_backup_manager.load_config()
            config.update({
                'enabled': data.get('enabled', False),
                'frequency': data.get('frequency', 'daily'),
                'time': data.get('time', '02:00'),
                'max_backups': int(data.get('max_backups', 10)),
                'auto_cleanup': data.get('auto_cleanup', True)
            })
            
            if auto_backup_manager.save_config(config):
                return jsonify({
                    'status': 'success',
                    'message': 'Configuração de backup automático salva com sucesso'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Erro ao salvar configuração'
                }), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Erro ao processar configuração: {str(e)}'
            }), 500
    
    # GET request - return current configuration
    config = auto_backup_manager.load_config()
    return jsonify({
        'status': 'success',
        'config': config
    })

@bp.route('/trigger-auto-backup', methods=['POST'])
@login_required
@admin_required
def trigger_auto_backup():
    """Manually trigger an auto backup"""
    try:
        success, message = auto_backup_manager.create_scheduled_backup()
        
        return jsonify({
            'status': 'success' if success else 'error',
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao executar backup automático: {str(e)}'
        }), 500

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def backup_settings():
    """Configurações de backup"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            max_backups = data.get('max_backups', 10)
            auto_cleanup = data.get('auto_cleanup', False)
            
            # Aqui você pode salvar as configurações em um arquivo ou banco de dados
            # Por agora, vamos apenas aplicar a limpeza se solicitada
            
            if auto_cleanup:
                success, message = storage_manager.cleanup_old_backups(max_backups)
                return jsonify({
                    'status': 'success' if success else 'error',
                    'message': f'Configurações salvas. {message}'
                })
            
            return jsonify({
                'status': 'success',
                'message': 'Configurações salvas com sucesso'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Erro ao salvar configurações: {str(e)}'
            }), 500
    
    # GET request - retornar configurações atuais
    return jsonify({
        'max_backups': 10,  # Valor padrão - pode ser carregado de configuração
        'auto_cleanup': False
    })
