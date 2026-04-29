# Práctica 6 - Inteligencia Artificial (AIA)

## Descripción

Este proyecto contiene el desarrollo y experimentación de la Práctica 6 para la asignatura de Inteligencia Artificial (AIA). Su objetivo es aplicar técnicas avanzadas de IA mediante un enfoque modular, robusto y escalable, estructurando el código de manera que facilite tanto la experimentación (con notebooks) como la puesta en producción.

## Estructura del Proyecto

*   **`config/`**: Archivos de configuración (YAML, JSON, .env).
*   **`data/`**: Carpeta para almacenar conjuntos de datos (raw, processed, external).
*   **`doc/`**: Documentación técnica, diagramas y la memoria de la práctica.
*   **`logs/`**: Archivos de registro para monitorización y depuración.
*   **`models/`**: Binarios de los modelos entrenados.
*   **`playground/`**: Área para experimentación y pruebas con Jupyter Notebooks.
*   **`references/`**: Artículos, manuales y bibliografía de referencia.
*   **`src/`**: Código fuente principal modularizado (data, features, models, evaluation, utils).
*   **`tests/`**: Pruebas unitarias y de integración.
*   **`main.py`**: Punto de entrada de ejecución del proyecto.
*   **`requirements.txt`**: Dependencias específicas para reproducir el entorno.

## Instalación y Configuración del Entorno

Es necesario utilizar el entorno virtual compartido de las prácticas, ubicado un nivel arriba en la carpeta principal:

### En Windows (PowerShell):
```powershell
# Activar el entorno virtual compartido
..\.venv\Scripts\Activate.ps1

# (Opcional) Instalar dependencias si hay actualizaciones
pip install -r requirements.txt
```

### En Linux/Mac:
```bash
# Activar el entorno virtual compartido
source ../.venv/bin/activate

# (Opcional) Instalar dependencias
pip install -r requirements.txt
```

## Ejecución

Para iniciar el flujo principal de ejecución de la práctica:

```bash
python main.py
```
