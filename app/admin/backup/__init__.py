from flask import Blueprint

bp = Blueprint('backup', __name__, template_folder='templates')

from app.admin.backup import routes
