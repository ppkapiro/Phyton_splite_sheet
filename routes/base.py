from flask import Blueprint, jsonify

bp = Blueprint('base', __name__)

@bp.route('/')
def index():
    return jsonify({"status": "API funcionando"})
