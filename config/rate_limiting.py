from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configuración básica: 200 peticiones/día y 50 por hora por IP de forma global.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
