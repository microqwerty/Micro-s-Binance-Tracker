#!/usr/bin/env python
"""
Binance Portfolio Tracker - Launcher Script

This script launches the Binance Portfolio Tracker application.
It ensures the proper Python path is set up for imports.
"""

import os
import sys
import importlib.util

# Get the absolute path of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the current directory to the Python path
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the main module directly
main_path = os.path.join(current_dir, "binance_tracker", "main.py")
spec = importlib.util.spec_from_file_location("main_module", main_path)
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)

if __name__ == "__main__":
    # Run the main function from the imported module
    main_module.main()