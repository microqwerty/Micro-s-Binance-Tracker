import os
import sys
import traceback
import importlib.util
import customtkinter as ctk
from typing import Optional

# Get the absolute path of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Import modules directly using file paths
def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import required modules
ui_main_window = import_from_file("main_window", os.path.join(current_dir, "ui", "main_window.py"))
utils_logger = import_from_file("logger", os.path.join(current_dir, "utils", "logger.py"))
utils_threader = import_from_file("threader", os.path.join(current_dir, "utils", "threader.py"))

# Get required classes and functions
MainWindow = ui_main_window.MainWindow
Logger = utils_logger.Logger
info = utils_logger.info
error = utils_logger.error
shutdown_threads = utils_threader.shutdown_threads


def setup_exception_handler():
    """Set up global exception handler."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle keyboard interrupt specially
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        # Log the exception
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        error(f"Uncaught exception: {error_msg}")
        
        # Show error dialog
        if hasattr(ctk, "CTk"):  # Check if CTk is initialized
            root = ctk.CTk()
            root.title("Error")
            root.geometry("400x300")
            
            frame = ctk.CTkFrame(root)
            frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            label = ctk.CTkLabel(
                frame,
                text="An unexpected error occurred:",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            label.pack(pady=(0, 10))
            
            error_text = ctk.CTkTextbox(frame, height=150)
            error_text.pack(fill="both", expand=True, pady=(0, 10))
            error_text.insert("1.0", str(exc_value))
            error_text.configure(state="disabled")
            
            ok_button = ctk.CTkButton(frame, text="OK", command=root.destroy)
            ok_button.pack(pady=(0, 10))
            
            root.mainloop()
    
    # Set the exception handler
    sys.excepthook = handle_exception


def main():
    """Main application entry point."""
    try:
        # Initialize logger
        logger = Logger.get_instance()
        info("Starting Binance Portfolio Tracker")
        
        # Set up exception handler
        setup_exception_handler()
        
        # Set appearance mode and default theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        app = MainWindow()
        
        # Start main loop
        info("Application started")
        app.mainloop()
        
        # Clean up
        info("Application closing")
        shutdown_threads()
        
    except Exception as e:
        error("Error in main function", e)
        raise


if __name__ == "__main__":
    # Add the project root directory to the Python path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    sys.path.insert(0, project_root)
    
    # Run main function
    main()