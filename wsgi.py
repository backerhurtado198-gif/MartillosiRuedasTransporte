import sys
import os

# Ruta exacta del proyecto en PythonAnywhere
path = '/home/beckeroot/mysite'
if path not in sys.path:
    sys.path.append(path)

# Importar la app de Flask desde app.py
from app import app as application
