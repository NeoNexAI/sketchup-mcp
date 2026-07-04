"""Pone ``src/`` en sys.path para todo el proceso de pytest, sin depender del
orden de recoleccion de los test modules."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
