import sys
import os

# Ruta de tu proyecto en PythonAnywhere (ajustará su usuario automáticamente)
path = os.path.expanduser('~/mysite')
if path not in sys.path:
    sys.path.append(path)

from app import app as application
