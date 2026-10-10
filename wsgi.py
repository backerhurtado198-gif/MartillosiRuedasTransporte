import sys
import os

path = '/home/beckeroot/mysite'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
