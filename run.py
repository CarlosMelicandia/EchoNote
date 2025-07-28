#!/usr/bin/env python3
"""
EchoNote Application Entry Point

This script runs the EchoNote Flask application.
Usage: python run.py
"""

import sys
import os

# Add the src directory to Python path so we can import our package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from echonote.app import app
from echonote.database import init_db

if __name__ == '__main__':
    # Initialize the database
    init_db()
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
