class Config:
    # Flask Configuration
    DEBUG = True  # Cambiar a False en producción
    CORS_HEADERS = 'Content-Type'
    SECRET_KEY = 'tu_clave_secura_aleatoria_aqui'  # Generar una clave segura en producción
    
    # DocuSign Configuration
    DOCUSIGN_ACCOUNT_ID = '7299e9a9-8a24-43d8-bd9e-10c84be0846'        # API Account ID de DocuSign
    DOCUSIGN_CLIENT_ID = '8b8bc56f-808c-47f0-918e-10c84be0846'         # Integration Key
    DOCUSIGN_CLIENT_SECRET = '21da586d-64da-4821-939a-770147c19e28'    # Secret Key
    DOCUSIGN_AUTH_SERVER = 'account-d.docusign.com'                     # Sandbox server
    DOCUSIGN_REDIRECT_URI = 'http://localhost:5000/callback'            # OAuth callback URL
    DOCUSIGN_PRIVATE_KEY_PATH = 'docusign_private.key'                 # Actualizado para usar el nuevo archivo
    
    # JWT Configuration
    JWT_SECRET_KEY = 'tu_clave_jwt_secreta'  # Cambiar en producción
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hora en segundos
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 días en segundos
    
    # Auth Configuration
    MAX_LOGIN_ATTEMPTS = 3  # Máximo de intentos de login
    LOGIN_TIMEOUT = 300  # Tiempo de bloqueo en segundos (5 minutos)
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///splitsheet.db'  # SQLite para desarrollo
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_CONNECT_OPTIONS = {}
    
    # Test Configuration
    TESTING = False
    
    @classmethod
    def get_test_config(cls):
        test_config = cls()
        test_config.TESTING = True
        test_config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        test_config.JWT_SECRET_KEY = 'test-key'
        return test_config
