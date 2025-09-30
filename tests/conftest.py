import os, sys
# add project root to sys.path so "from tools.predict import simple_rules" works
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
