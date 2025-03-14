import os
from pathlib import Path
import ast
import re
from datetime import datetime

def extract_test_info(content):
    """Extrae información de tests del contenido del archivo."""
    test_info = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # Extraer docstring si existe
                docstring = ast.get_docstring(node) or "Sin descripción"
                test_info.append({
                    'name': node.name,
                    'description': docstring,
                    'line_number': node.lineno
                })
    except Exception as e:
        test_info.append({
            'name': 'Error parsing',
            'description': f"Error analizando archivo: {str(e)}",
            'line_number': 0
        })
    return test_info

def analyze_tests(test_dir='tests'):
    """Analiza la estructura de tests y genera un informe."""
    base_path = Path(__file__).parent.parent / test_dir
    output_path = base_path.parent / 'docs' / 'Test_Estado.md'
    
    content = [
        "# Estado de la Estructura de Tests",
        f"*Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n",
        "## Estructura General\n"
    ]
    
    total_tests = 0
    test_files = []
    
    # Analizar cada archivo
    for file_path in base_path.rglob('*.py'):
        if file_path.name.startswith('test_'):
            rel_path = file_path.relative_to(base_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    
                tests = extract_test_info(file_content)
                total_tests += len(tests)
                
                test_files.append({
                    'path': str(rel_path),
                    'tests': tests,
                    'size': len(file_content.splitlines())
                })
            except Exception as e:
                print(f"Error procesando {file_path}: {e}")
    
    # Generar informe
    content.extend([
        f"- Total archivos de test: {len(test_files)}",
        f"- Total tests: {total_tests}\n",
        "## Detalle por Archivo\n"
    ])
    
    for file_info in sorted(test_files, key=lambda x: x['path']):
        content.extend([
            f"### {file_info['path']}",
            f"- Líneas de código: {file_info['size']}",
            "- Tests encontrados:"
        ])
        
        for test in file_info['tests']:
            content.extend([
                f"  - `{test['name']}` (línea {test['line_number']})",
                f"    - {test['description'].strip()}"
            ])
        content.append("")
    
    # Guardar informe
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    
    print(f"Informe generado en: {output_path}")

if __name__ == '__main__':
    analyze_tests()
