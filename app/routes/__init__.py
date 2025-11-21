from flask import Blueprint

main_bp = Blueprint('main', __name__)

# Import routes after blueprint creation to avoid circular imports
from app.routes import main
