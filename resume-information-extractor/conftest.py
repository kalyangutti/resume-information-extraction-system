"""
pytest configuration and shared fixtures.
"""
import sys
import os

# Ensure the project root is on sys.path so 'app' is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
