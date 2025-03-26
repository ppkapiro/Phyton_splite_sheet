import pytest
from flask import json

def test_login_rate_limit(client):
    """Prueba que al realizar múltiples peticiones al endpoint de login se active el rate limit."""
    login_payload = {
        "username": "some_user",
        "password": "some_password"
    }
    headers = {"Content-Type": "application/json"}

    # Se realizan 6 peticiones (el límite es 5 por minuto)
    responses = [client.post('/api/login', json=login_payload, headers=headers) for _ in range(6)]
    
    # Se espera que al menos una respuesta tenga código 429 Too Many Requests.
    statuses = [resp.status_code for resp in responses]
    assert any(status == 429 for status in statuses), "No se aplicó rate limiting (se esperaba un 429)"
