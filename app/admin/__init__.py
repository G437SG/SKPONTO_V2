from flask import Blueprint

bp = Blueprint('admin', __name__)

from app.admin import routes, hour_bank_routes, overtime_admin
# Removido: dropbox_database_routes (não é mais necessário)
