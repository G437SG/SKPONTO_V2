from flask import render_template, request, jsonify
from app import db
from app.errors import bp

@bp.app_errorhandler(404)
def not_found_error(error):
    """Página não encontrada"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint não encontrado'}), 404
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    """Erro interno do servidor"""
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Erro interno do servidor'}), 500
    return render_template('errors/500.html'), 500

@bp.app_errorhandler(403)
def forbidden_error(error):
    """Acesso proibido"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Acesso negado'}), 403
    return render_template('errors/403.html'), 403

@bp.app_errorhandler(413)
def request_entity_too_large(error):
    """Arquivo muito grande"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Arquivo muito grande'}), 413
    return render_template('errors/413.html'), 413
