from flask import Flask
from models.database import db, init_app

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Inicializar componentes
    init_app(app)
    
    return app

app = create_app()
