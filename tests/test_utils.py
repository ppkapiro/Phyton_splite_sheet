import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import sys

class TestReporter:
    """Clase unificada para generar reportes de pruebas"""
    # Atributos de clase
    results: List[Dict[str, Any]] = []
    start_time = datetime.now()  # Inicializar al definir la clase
    log_dir = None
    log_file = None
    json_file = None
    terminal_log = None

    @classmethod
    def setup_class(cls):
        """Método de inicialización de clase para pytest"""
        # Reinicializar atributos al comenzar las pruebas
        cls.results = []
        cls.start_time = datetime.now()  # Actualizar tiempo de inicio
        cls._setup_logging()

    @classmethod
    def _setup_logging(cls) -> None:
        """Configurar logging para las pruebas"""
        cls.log_dir = Path(__file__).parent.parent / 'reports'
        cls.log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cls.log_file = cls.log_dir / f'test_output_{timestamp}.log'
        cls.json_file = cls.log_dir / f'test_report_{timestamp}.json'
        cls.terminal_log = cls.log_dir / 'pytest-log.txt'
        
        # Configurar formato detallado
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Handler para archivo de log general
        file_handler = logging.FileHandler(cls.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # Handler específico para la salida de terminal
        terminal_handler = logging.FileHandler(cls.terminal_log, encoding='utf-8', mode='a')
        terminal_handler.setFormatter(formatter)
        
        # Configurar logger raíz
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(terminal_handler)
        
        # Capturar salida estándar y de error
        sys.stdout = TeeOutput(sys.stdout, [cls.log_file, cls.terminal_log])
        sys.stderr = TeeOutput(sys.stderr, [cls.log_file, cls.terminal_log])

    def add_result(self, test_name: str, status: str, duration: float, 
                  error: str = None) -> None:
        """Agregar resultado de una prueba"""
        self.results.append({
            'test_name': test_name,
            'status': status,
            'duration': f"{duration:.3f}s",
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
    
    def generate_reports(self) -> Dict[str, str]:
        """Generar reportes en JSON y texto"""
        # Asegurar que start_time tenga un valor válido
        if self.start_time is None:
            self.start_time = datetime.now()
            logging.warning("start_time no estaba inicializado, se estableció al tiempo actual")

        try:
            # Verificar/crear directorio
            reports_dir = self.log_dir
            reports_dir.mkdir(parents=True, exist_ok=True)
            print(f"\nDirectorio de reportes: {reports_dir}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Definir rutas de archivos
            json_file = reports_dir / f'test_report_{timestamp}.json'
            txt_file = reports_dir / f'test_summary_{timestamp}.txt'
            log_file = reports_dir / f'test_output_{timestamp}.log'
            
            # Generar y guardar reporte JSON
            json_content = json.dumps(self._generate_report_data(), indent=2, ensure_ascii=False)
            json_file.write_text(json_content, encoding='utf-8')
            print(f"Archivo JSON creado: {json_file} ({len(json_content)} bytes)")
            
            # Generar y guardar reporte de texto
            txt_content = self._generate_text_report()
            txt_file.write_text(txt_content, encoding='utf-8')
            print(f"Archivo TXT creado: {txt_file} ({len(txt_content)} bytes)")
            
            # Copiar y verificar archivo de log
            if hasattr(self, 'log_file') and self.log_file.exists():
                import shutil
                shutil.copy2(self.log_file, log_file)
                print(f"Archivo LOG creado: {log_file} ({log_file.stat().st_size} bytes)")
            
            # Verificar que los archivos existen
            files = {
                'json': str(json_file),
                'txt': str(txt_file),
                'log': str(log_file)
            }
            
            for file_type, file_path in files.items():
                path = Path(file_path)
                if path.exists():
                    print(f"✓ Verificado {file_type}: {path}")
                else:
                    print(f"✗ Error: No se creó {file_type}: {path}")
            
            return files
            
        except Exception as e:
            print(f"\nError generando reportes: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    def _generate_report_data(self) -> Dict[str, Any]:
        """Generar datos del reporte"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        # Calcular estadísticas
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = total - passed
        
        return {
            'summary': {
                'total_tests': total,
                'passed': passed,
                'failed': failed,
                'duration': f"{duration:.2f} segundos",
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat()
            },
            'results': self.results
        }
    
    def _generate_text_report(self) -> str:
        """Generar reporte de texto"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = total - passed
        
        report = []
        report.append(f"Reporte de Pruebas\n")
        report.append(f"=================\n\n")
        report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"Total pruebas: {total}\n")
        report.append(f"Exitosas: {passed}\n")
        report.append(f"Fallidas: {failed}\n")
        report.append(f"Duración: {duration:.2f} segundos\n\n")
        
        report.append("Detalle de pruebas:\n")
        report.append("-----------------\n")
        for result in self.results:
            report.append(f"\n{result['test_name']}:\n")
            report.append(f"  Estado: {result['status']}\n")
            report.append(f"  Duración: {result['duration']}\n")
            if result['error']:
                report.append(f"  Error: {result['error']}\n")
        
        return ''.join(report)

class TeeOutput:
    """Clase para escribir en múltiples archivos y la terminal"""
    def __init__(self, original_stream, log_files):
        self.original_stream = original_stream
        self.log_files = [Path(f) if isinstance(f, str) else f for f in log_files]
        self.file_handles = {}
    
    def write(self, message):
        # Escribir en la terminal
        self.original_stream.write(message)
        
        # Escribir en cada archivo de log
        for log_file in self.log_files:
            if log_file not in self.file_handles:
                self.file_handles[log_file] = open(log_file, 'a', encoding='utf-8')
            self.file_handles[log_file].write(message)
            self.file_handles[log_file].flush()
    
    def flush(self):
        self.original_stream.flush()
        for handle in self.file_handles.values():
            handle.flush()
    
    def __del__(self):
        for handle in self.file_handles.values():
            handle.close()
