from flask import Blueprint, jsonify, current_app, request, abort
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import time

protected_bp = Blueprint('protected_api', __name__)

@protected_bp.before_request
def verify_jwt():
    """Verificar JWT antes de cada request"""
    try:
        verify_jwt_in_request()
        current_user = get_jwt_identity()
        if not current_user:
            abort(401, description="No autorizado - Usuario no válido")
        return None
    except NoAuthorizationError:
        abort(401, description="No autorizado - Token faltante")
    except InvalidHeaderError:
        abort(401, description="No autorizado - Token mal formado")
    except Exception as e:
        current_app.logger.error(f"Error en autenticación: {str(e)}")
        abort(401, description="No autorizado - Error de autenticación")

@protected_bp.errorhandler(401)
def unauthorized_handler(error):
    """Manejador personalizado para error 401"""
    return jsonify({
        "error": "No autorizado",
        "details": str(error.description)
    }), 401
