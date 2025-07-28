import os
import traceback
import logging
from datetime import datetime
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.admin.backup import bp

# Configurar logger específico para erros de backup
backup_logger = logging.getLogger('backup_errors')
backup_logger.setLevel(logging.DEBUG)

# Handler para arquivo de log
log_file = os.path.join('logs', 'backup_errors.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
backup_logger.addHandler(file_handler)

class BackupErrorLogger:
    """Classe para capturar e registrar erros detalhados do sistema de backup"""
    
    @staticmethod
    def log_error(error_type, error_message, context=None):
        """Registra um erro com contexto detalhado"""
        try:
            error_data = {
                'timestamp': datetime.now().isoformat(),
                'error_type': error_type,
                'error_message': str(error_message),
                'traceback': traceback.format_exc(),
                'user': current_user.email if current_user.is_authenticated else 'Anonymous',
                'request_path': request.path if request else 'N/A',
                'request_method': request.method if request else 'N/A',
                'user_agent': request.headers.get('User-Agent') if request else 'N/A',
                'context': context or {}
            }
            
            backup_logger.error(f"BACKUP_ERROR: {error_data}")
            return error_data
        except Exception as e:
            backup_logger.critical(f"ERRO CRÍTICO ao registrar erro: {str(e)}")
            return None
    
    @staticmethod
    def log_access_attempt(endpoint, success=False, error=None):
        """Registra tentativas de acesso ao sistema de backup"""
        try:
            access_data = {
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'success': success,
                'user': current_user.email if current_user.is_authenticated else 'Anonymous',
                'user_id': current_user.id if current_user.is_authenticated else None,
                'is_admin': current_user.user_type.value == 'admin' if current_user.is_authenticated else False,
                'ip_address': request.remote_addr if request else 'N/A',
                'error': str(error) if error else None
            }
            
            if success:
                backup_logger.info(f"BACKUP_ACCESS_SUCCESS: {access_data}")
            else:
                backup_logger.warning(f"BACKUP_ACCESS_FAILED: {access_data}")
            
            return access_data
        except Exception as e:
            backup_logger.critical(f"ERRO CRÍTICO ao registrar acesso: {str(e)}")
            return None

@bp.route('/error-log')
@login_required
def error_log_page():
    """Página de diagnóstico de erros do sistema de backup"""
    try:
        BackupErrorLogger.log_access_attempt('/admin/backup/error-log', success=True)
        
        # Verificar permissões
        if not current_user.is_authenticated:
            error_data = BackupErrorLogger.log_error(
                'AUTHENTICATION_ERROR',
                'Usuário não autenticado tentando acessar logs de erro',
                {'endpoint': '/admin/backup/error-log'}
            )
            return render_template('admin/backup/error_log.html', 
                                 error_data=error_data,
                                 diagnosis_result="Erro de autenticação")
        
        if current_user.user_type.value != 'admin':
            error_data = BackupErrorLogger.log_error(
                'PERMISSION_ERROR',
                f'Usuário {current_user.email} sem permissão admin tentando acessar logs',
                {'user_type': current_user.user_type.value}
            )
            return render_template('admin/backup/error_log.html',
                                 error_data=error_data,
                                 diagnosis_result="Erro de permissão")
        
        # Executar diagnóstico completo
        diagnosis_result = run_backup_diagnosis()
        
        return render_template('admin/backup/error_log.html',
                             diagnosis_result=diagnosis_result,
                             user_info={
                                 'id': current_user.id,
                                 'email': current_user.email,
                                 'user_type': current_user.user_type.value,
                                 'is_admin': current_user.user_type.value == 'admin'
                             })
    
    except Exception as e:
        error_data = BackupErrorLogger.log_error(
            'CRITICAL_ERROR',
            f'Erro crítico na página de diagnóstico: {str(e)}',
            {'endpoint': '/admin/backup/error-log'}
        )
        return render_template('admin/backup/error_log.html',
                             error_data=error_data,
                             diagnosis_result="Erro crítico no diagnóstico")

def run_backup_diagnosis():
    """Executa diagnóstico completo do sistema de backup"""
    diagnosis = {
        'timestamp': datetime.now().isoformat(),
        'tests': [],
        'summary': 'OK',
        'critical_errors': [],
        'warnings': []
    }
    
    try:
        # Teste 1: Verificar importações
        diagnosis['tests'].append(test_imports())
        
        # Teste 2: Verificar estrutura de diretórios
        diagnosis['tests'].append(test_directory_structure())
        
        # Teste 3: Verificar LocalStorageManager
        diagnosis['tests'].append(test_storage_manager())
        
        # Teste 4: Verificar blueprint registration
        diagnosis['tests'].append(test_blueprint_registration())
        
        # Teste 5: Verificar templates
        diagnosis['tests'].append(test_templates())
        
        # Teste 6: Verificar permissões
        diagnosis['tests'].append(test_permissions())
        
        # Compilar resultados
        failed_tests = [t for t in diagnosis['tests'] if not t['passed']]
        warning_tests = [t for t in diagnosis['tests'] if t.get('warning')]
        
        if failed_tests:
            diagnosis['summary'] = 'FALHAS CRÍTICAS'
            diagnosis['critical_errors'] = [t['error'] for t in failed_tests]
        elif warning_tests:
            diagnosis['summary'] = 'AVISOS'
            diagnosis['warnings'] = [t['warning'] for t in warning_tests]
        
    except Exception as e:
        diagnosis['summary'] = 'ERRO DE DIAGNÓSTICO'
        diagnosis['critical_errors'].append(f'Falha no diagnóstico: {str(e)}')
        BackupErrorLogger.log_error('DIAGNOSIS_ERROR', str(e))
    
    return diagnosis

def test_imports():
    """Testa se as importações estão funcionando"""
    try:
        from app.admin.backup.routes import LocalStorageManager, storage_manager
        return {
            'name': 'Importações',
            'passed': True,
            'message': 'LocalStorageManager importado com sucesso'
        }
    except Exception as e:
        return {
            'name': 'Importações',
            'passed': False,
            'error': f'Erro ao importar: {str(e)}'
        }

def test_directory_structure():
    """Testa a estrutura de diretórios"""
    try:
        required_dirs = [
            'app/admin/backup',
            'app/admin/backup/templates/admin/backup',
            'backups'
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            return {
                'name': 'Estrutura de Diretórios',
                'passed': False,
                'error': f'Diretórios ausentes: {", ".join(missing_dirs)}'
            }
        
        return {
            'name': 'Estrutura de Diretórios',
            'passed': True,
            'message': 'Todos os diretórios necessários existem'
        }
    except Exception as e:
        return {
            'name': 'Estrutura de Diretórios',
            'passed': False,
            'error': f'Erro ao verificar diretórios: {str(e)}'
        }

def test_storage_manager():
    """Testa o LocalStorageManager"""
    try:
        from app.admin.backup.routes import storage_manager
        
        # Testar método get_storage_info
        storage_info = storage_manager.get_storage_info()
        
        if not isinstance(storage_info, dict):
            return {
                'name': 'LocalStorageManager',
                'passed': False,
                'error': 'get_storage_info() não retornou um dicionário'
            }
        
        required_keys = ['total_size', 'used_space', 'free_space', 'backup_count', 'status', 'message']
        missing_keys = [key for key in required_keys if key not in storage_info]
        
        if missing_keys:
            return {
                'name': 'LocalStorageManager',
                'passed': False,
                'error': f'Chaves ausentes em storage_info: {", ".join(missing_keys)}'
            }
        
        return {
            'name': 'LocalStorageManager',
            'passed': True,
            'message': f'Storage Manager funcionando. Status: {storage_info["status"]}'
        }
    except Exception as e:
        return {
            'name': 'LocalStorageManager',
            'passed': False,
            'error': f'Erro no LocalStorageManager: {str(e)}'
        }

def test_blueprint_registration():
    """Testa se o blueprint está registrado corretamente"""
    try:
        from flask import current_app
        
        # Verificar se a rota existe
        endpoint = 'backup.dashboard'
        if endpoint in current_app.url_map._rules_by_endpoint:
            return {
                'name': 'Blueprint Registration',
                'passed': True,
                'message': 'Blueprint registrado e rota encontrada'
            }
        else:
            return {
                'name': 'Blueprint Registration',
                'passed': False,
                'error': f'Endpoint {endpoint} não encontrado no mapa de rotas'
            }
    except Exception as e:
        return {
            'name': 'Blueprint Registration',
            'passed': False,
            'error': f'Erro ao verificar blueprint: {str(e)}'
        }

def test_templates():
    """Testa se os templates existem"""
    try:
        template_path = 'app/admin/backup/templates/admin/backup/dashboard.html'
        
        if not os.path.exists(template_path):
            return {
                'name': 'Templates',
                'passed': False,
                'error': f'Template não encontrado: {template_path}'
            }
        
        return {
            'name': 'Templates',
            'passed': True,
            'message': 'Template dashboard.html encontrado'
        }
    except Exception as e:
        return {
            'name': 'Templates',
            'passed': False,
            'error': f'Erro ao verificar templates: {str(e)}'
        }

def test_permissions():
    """Testa as permissões do usuário atual"""
    try:
        if not current_user.is_authenticated:
            return {
                'name': 'Permissões',
                'passed': False,
                'error': 'Usuário não autenticado'
            }
        
        if current_user.user_type.value != 'admin':
            return {
                'name': 'Permissões',
                'passed': False,
                'error': f'Usuário não é admin. Tipo atual: {current_user.user_type.value}'
            }
        
        return {
            'name': 'Permissões',
            'passed': True,
            'message': f'Usuário {current_user.email} é admin'
        }
    except Exception as e:
        return {
            'name': 'Permissões',
            'passed': False,
            'error': f'Erro ao verificar permissões: {str(e)}'
        }

@bp.route('/api/diagnosis')
@login_required
def api_diagnosis():
    """API endpoint para diagnóstico em tempo real"""
    try:
        if current_user.user_type.value != 'admin':
            return jsonify({'error': 'Acesso negado'}), 403
        
        diagnosis = run_backup_diagnosis()
        return jsonify(diagnosis)
    except Exception as e:
        BackupErrorLogger.log_error('API_DIAGNOSIS_ERROR', str(e))
        return jsonify({'error': str(e)}), 500
