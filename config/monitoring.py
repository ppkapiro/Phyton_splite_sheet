from prometheus_client import start_http_server, Counter, Histogram

# Métricas para la API
REQUEST_COUNT = Counter(
    'api_request_count', 'Total de peticiones a la API', ['method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds', 'Tiempo de respuesta de la API', ['endpoint']
)

def start_monitoring_server(port=8000):
    """Inicia un servidor que expone métricas para Prometheus."""
    start_http_server(port)
