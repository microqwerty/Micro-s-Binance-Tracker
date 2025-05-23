import os
import logging
import datetime
from typing import Optional


class Logger:
    """
    Logger utility for the application.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'Logger':
        """
        Get singleton instance of the logger.
        
        Returns:
            Logger instance
        """
        if cls._instance is None:
            cls._instance = Logger()
        return cls._instance
    
    def __init__(self):
        """Initialize logger."""
        # Create logger
        self.logger = logging.getLogger("BinanceTracker")
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Create file handler
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"app_{datetime.datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        """
        Log debug message.
        
        Args:
            message: Debug message
        """
        self.logger.debug(message)
    
    def info(self, message: str):
        """
        Log info message.
        
        Args:
            message: Info message
        """
        self.logger.info(message)
    
    def warning(self, message: str):
        """
        Log warning message.
        
        Args:
            message: Warning message
        """
        self.logger.warning(message)
    
    def error(self, message: str, exc: Optional[Exception] = None):
        """
        Log error message.
        
        Args:
            message: Error message
            exc: Optional exception
        """
        if exc:
            self.logger.error(f"{message}: {str(exc)}", exc_info=True)
        else:
            self.logger.error(message)
    
    def critical(self, message: str, exc: Optional[Exception] = None):
        """
        Log critical message.
        
        Args:
            message: Critical message
            exc: Optional exception
        """
        if exc:
            self.logger.critical(f"{message}: {str(exc)}", exc_info=True)
        else:
            self.logger.critical(message)


# Convenience functions
def debug(message: str):
    """
    Log debug message.
    
    Args:
        message: Debug message
    """
    Logger.get_instance().debug(message)


def info(message: str):
    """
    Log info message.
    
    Args:
        message: Info message
    """
    Logger.get_instance().info(message)


def warning(message: str):
    """
    Log warning message.
    
    Args:
        message: Warning message
    """
    Logger.get_instance().warning(message)


def error(message: str, exc: Optional[Exception] = None):
    """
    Log error message.
    
    Args:
        message: Error message
        exc: Optional exception
    """
    Logger.get_instance().error(message, exc)


def critical(message: str, exc: Optional[Exception] = None):
    """
    Log critical message.
    
    Args:
        message: Critical message
        exc: Optional exception
    """
    Logger.get_instance().critical(message, exc)