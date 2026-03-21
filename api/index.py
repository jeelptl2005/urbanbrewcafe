import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(_file_)))

from app import app

handler = app
