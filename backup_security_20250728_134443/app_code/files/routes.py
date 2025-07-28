#!/usr/bin/env python
"""
Rotas para gerenciamento de arquivos
"""
import os
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (
    render_template, request, redirect, url_for, flash, 
    send_file, jsonify, current_app, abort
)
from flask_login import login_required, current_user
from app.files import bp
from app.decorators import admin_required
from app.models import db, User, FileUpload
from app.utils import allowed_file, get_file_size, format_file_size, generate_unique_filename
from app.constants import (
    MSG_NO_FILE_SELECTED, MSG_FILE_NOT_FOUND, MSG_INVALID_PARAMETERS,
    MSG_OPERATION_NOT_ALLOWED, MSG_FILE_UPLOADED, MSG_FILE_DELETED,
    MSG_FILE_MOVED, MSG_FILE_RENAMED, MSG_FOLDER_CREATED, MSG_FOLDER_DELETED,
    MSG_ZIP_CREATED, ROUTE_FILE_MANAGER, MAX_FILE_SIZE_BYTES
)
import zipfile
import mimetypes

@bp.route('/manager')
@login_required
@admin_required
def file_manager():
    """Página principal do gerenciador de arquivos"""
    # Listar arquivos do diretório shared_storage
    shared_path = os.path.join(current_app.root_path, '..', 'shared_storage')
    if not os.path.exists(shared_path):
        os.makedirs(shared_path)
    
    files = []
    folders = []
    
    try:
        for item in os.listdir(shared_path):
            item_path = os.path.join(shared_path, item)
            if os.path.isdir(item_path):
                folders.append({
                    'name': item,
                    'path': item,
                    'size': get_folder_size(item_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(item_path)).strftime('%d/%m/%Y %H:%M'),
                    'type': 'folder'
                })
            else:
                files.append({
                    'name': item,
                    'path': item,
                    'size': format_file_size(os.path.getsize(item_path)),
                    'modified': datetime.fromtimestamp(os.path.getmtime(item_path)).strftime('%d/%m/%Y %H:%M'),
                    'type': 'file',
                    'extension': os.path.splitext(item)[1].lower()
                })
    except Exception as e:
        flash(f'Erro ao listar arquivos: {str(e)}', 'error')
    
    return render_template('files/manager.html', files=files, folders=folders)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_file():
    """Upload de arquivos"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash(MSG_NO_FILE_SELECTED, 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash(MSG_NO_FILE_SELECTED, 'error')
            return redirect(request.url)
        
        if file and file.filename and allowed_file(file.filename):
            filename = generate_unique_filename(file.filename, 
                                              os.path.join(current_app.root_path, '..', 'shared_storage'))
            shared_path = os.path.join(current_app.root_path, '..', 'shared_storage')
            
            # Criar diretório se não existir
            if not os.path.exists(shared_path):
                os.makedirs(shared_path)
            
            file_path = os.path.join(shared_path, filename)
            
            try:
                file.save(file_path)
                
                # Salvar no banco de dados
                file_upload = FileUpload(
                    filename=filename,
                    original_filename=file.filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    mime_type=file.content_type,
                    uploaded_by=current_user.id
                )
                db.session.add(file_upload)
                db.session.commit()
                
                flash(MSG_FILE_UPLOADED, 'success')
                return redirect(url_for(ROUTE_FILE_MANAGER))
                
            except Exception as e:
                flash(f'Erro ao fazer upload: {str(e)}', 'error')
        else:
            flash('Tipo de arquivo não permitido', 'error')
    
    return render_template('files/upload.html')

@bp.route('/download/<path:filename>')
@login_required
def download_file(filename):
    """Download de arquivos"""
    shared_path = os.path.join(current_app.root_path, '..', 'shared_storage')
    file_path = os.path.join(shared_path, filename)
    
    if not os.path.exists(file_path):
        abort(404)
    
    if not os.path.isfile(file_path):
        abort(404)
    
    # Verificar se é um arquivo dentro de uma pasta permitida
    if not file_path.startswith(shared_path):
        abort(403)
    
    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(f'Erro ao baixar arquivo: {str(e)}', 'error')
        return redirect(url_for('files.file_manager'))

@bp.route('/create-folder', methods=['POST'])
@login_required
@admin_required
def create_folder():
    """Criar nova pasta"""
    folder_name = request.form.get('folder_name', '').strip()
    
    if not folder_name:
        flash('Nome da pasta não pode estar vazio', 'error')
        return redirect(url_for('files.file_manager'))
    
    # Sanitizar nome da pasta
    folder_name = secure_filename(folder_name)
    
    shared_path = os.path.join(current_app.root_path, '..', 'shared_storage')
    folder_path = os.path.join(shared_path, folder_name)
    
    if os.path.exists(folder_path):
        flash('Pasta já existe', 'error')
        return redirect(url_for('files.file_manager'))
    
    try:
        os.makedirs(folder_path)
        flash(f'Pasta "{folder_name}" criada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao criar pasta: {str(e)}', 'error')
    
    return redirect(url_for('files.file_manager'))

@bp.route('/delete/<path:filename>')
@login_required
@admin_required
def delete_file(filename):
    """Deletar arquivo ou pasta"""
    shared_path = os.path.join(current_app.root_path, '..', 'shared_storage')
    file_path = os.path.join(shared_path, filename)
    
    if not os.path.exists(file_path):
        flash('Arquivo não encontrado', 'error')
        return redirect(url_for('files.file_manager'))
    
    if not file_path.startswith(shared_path):
        flash('Operação não permitida', 'error')
        return redirect(url_for('files.file_manager'))
    
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            # Remover do banco de dados
            file_upload = FileUpload.query.filter_by(filename=filename).first()
            if file_upload:
                db.session.delete(file_upload)
                db.session.commit()
            flash('Arquivo deletado com sucesso!', 'success')
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
            flash('Pasta deletada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao deletar: {str(e)}', 'error')
    
    return redirect(url_for('files.file_manager'))

@bp.route('/move', methods=['POST'])
@login_required
@admin_required
def move_file():
    """Mover arquivo ou pasta"""
    source = request.form.get('source')
    destination = request.form.get('destination')
    
    if not source or not destination:
        return jsonify({'success': False, 'message': 'Parâmetros inválidos'})
    
    shared_path = os.path.join(current_app.root_path, '..', 'shared_storage')
    source_path = os.path.join(shared_path, source)
    dest_path = os.path.join(shared_path, destination)
    
    if not os.path.exists(source_path):
        return jsonify({'success': False, 'message': 'Arquivo de origem não encontrado'})
    
    if not source_path.startswith(shared_path) or not dest_path.startswith(shared_path):
        return jsonify({'success': False, 'message': 'Operação não permitida'})
    
    try:
        # Criar diretório de destino se não existir
        dest_dir = os.path.dirname(dest_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        
        shutil.move(source_path, dest_path)
        
        # Atualizar banco de dados se for arquivo
        if os.path.isfile(dest_path):
            file_upload = FileUpload.query.filter_by(filename=source).first()
            if file_upload:
                file_upload.filename = destination
                file_upload.file_path = dest_path
                db.session.commit()
        
        return jsonify({'success': True, 'message': 'Arquivo movido com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao mover arquivo: {str(e)}'})

@bp.route('/rename', methods=['POST'])
@login_required
@admin_required
def rename_file():
    """Renomear arquivo ou pasta"""
    old_name = request.form.get('old_name')
    new_name = request.form.get('new_name')
    
    if not old_name or not new_name:
        return jsonify({'success': False, 'message': 'Parâmetros inválidos'})
    
    # Sanitizar novo nome
    new_name = secure_filename(new_name)
    
    shared_path = os.path.join(current_app.root_path, '..', 'shared_storage')
    old_path = os.path.join(shared_path, old_name)
    new_path = os.path.join(shared_path, new_name)
    
    if not os.path.exists(old_path):
        return jsonify({'success': False, 'message': 'Arquivo não encontrado'})
    
    if os.path.exists(new_path):
        return jsonify({'success': False, 'message': 'Arquivo com este nome já existe'})
    
    try:
        os.rename(old_path, new_path)
        
        # Atualizar banco de dados se for arquivo
        if os.path.isfile(new_path):
            file_upload = FileUpload.query.filter_by(filename=old_name).first()
            if file_upload:
                file_upload.filename = new_name
                file_upload.file_path = new_path
                db.session.commit()
        
        return jsonify({'success': True, 'message': 'Arquivo renomeado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao renomear: {str(e)}'})

@bp.route('/create-zip', methods=['POST'])
@login_required
@admin_required
def create_zip():
    """Criar arquivo ZIP com arquivos selecionados"""
    files = request.form.getlist('files')
    zip_name = request.form.get('zip_name', 'arquivos.zip')
    
    if not files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
    
    # Sanitizar nome do ZIP
    zip_name = secure_filename(zip_name)
    if not zip_name.endswith('.zip'):
        zip_name += '.zip'
    
    shared_path = os.path.join(current_app.root_path, '..', 'shared_storage')
    zip_path = os.path.join(shared_path, zip_name)
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                file_path = os.path.join(shared_path, file)
                if os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        zipf.write(file_path, file)
                    elif os.path.isdir(file_path):
                        # Adicionar pasta e seus conteúdos
                        for root, dirs, files_in_dir in os.walk(file_path):
                            for file_in_dir in files_in_dir:
                                file_full_path = os.path.join(root, file_in_dir)
                                arcname = os.path.relpath(file_full_path, shared_path)
                                zipf.write(file_full_path, arcname)
        
        return jsonify({'success': True, 'message': f'Arquivo ZIP "{zip_name}" criado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao criar ZIP: {str(e)}'})

@bp.route('/info/<path:filename>')
@login_required
def file_info(filename):
    """Informações detalhadas do arquivo"""
    shared_path = os.path.join(current_app.root_path, '..', 'shared_storage')
    file_path = os.path.join(shared_path, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'Arquivo não encontrado'})
    
    try:
        stat = os.stat(file_path)
        info = {
            'name': filename,
            'size': format_file_size(stat.st_size),
            'size_bytes': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M:%S'),
            'created': datetime.fromtimestamp(stat.st_ctime).strftime('%d/%m/%Y %H:%M:%S'),
            'type': 'Pasta' if os.path.isdir(file_path) else 'Arquivo',
            'extension': os.path.splitext(filename)[1].lower() if os.path.isfile(file_path) else None,
            'mime_type': mimetypes.guess_type(file_path)[0] if os.path.isfile(file_path) else None
        }
        
        # Informações adicionais do banco de dados
        if os.path.isfile(file_path):
            file_upload = FileUpload.query.filter_by(filename=filename).first()
            if file_upload:
                info['uploaded_by'] = file_upload.user.nome if file_upload.user else 'Desconhecido'
                info['upload_date'] = file_upload.created_at.strftime('%d/%m/%Y %H:%M:%S')
        
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': f'Erro ao obter informações: {str(e)}'})

def get_folder_size(folder_path):
    """Calcular tamanho da pasta"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
    except Exception:
        pass
    return format_file_size(total_size)
