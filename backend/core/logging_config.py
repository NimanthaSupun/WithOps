# Enhanced logging configuration for FastAPI backend
import logging
import logging.handlers
import os
import sys

class SafeFormatter(logging.Formatter):
    """Custom formatter that handles Unicode encoding errors gracefully"""
    
    def format(self, record):
        try:
            # Try normal formatting first
            return super().format(record)
        except UnicodeEncodeError:
            # If encoding fails, create a safe version
            if hasattr(record, 'msg') and isinstance(record.msg, str):
                # Replace problematic Unicode characters with ASCII equivalents
                safe_msg = (record.msg
                           .replace('🔍', '[SEARCH]')
                           .replace('✅', '[SUCCESS]')
                           .replace('❌', '[ERROR]')
                           .replace('⚠️', '[WARNING]')
                           .replace('📊', '[DATA]')
                           .replace('🛡️', '[SECURITY]')
                           .replace('💡', '[INFO]')
                           .replace('📈', '[METRICS]'))
                record.msg = safe_msg
            return super().format(record)

class SafeStreamHandler(logging.StreamHandler):
    """Stream handler that gracefully handles detached buffers"""
    
    def emit(self, record):
        try:
            # Check if the stream is still available
            if hasattr(self.stream, 'closed') and self.stream.closed:
                return
            if hasattr(self.stream, 'mode') and hasattr(self.stream, 'buffer'):
                # Check if buffer is detached
                try:
                    self.stream.buffer
                except ValueError:
                    # Buffer is detached, skip logging to console
                    return
            super().emit(record)
        except (ValueError, AttributeError, OSError):
            # Silently ignore buffer detachment errors
            pass

# Global flag to prevent multiple logging setups
_logging_configured = False

def setup_logging():
    """
    Configure logging for the DevSecOps platform with Unicode support
    """
    global _logging_configured
    
    if _logging_configured:
        return {
            'github': logging.getLogger('github_client'),
            'auth': logging.getLogger('auth'),
            'performance': logging.getLogger('performance')
        }
    
    # Don't try to modify stdout/stderr in multiprocessing environments
    # This prevents buffer detachment issues with uvicorn --reload
    
    # Create logs directory if it doesn't exist
    log_dir = '/app/logs' if os.path.exists('/app/logs') else 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Clear any existing handlers to prevent duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create a safe console handler that handles encoding gracefully
    console_handler = SafeStreamHandler()
    console_handler.setFormatter(SafeFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Configure root logger with file-only logging in multiprocessing environments
    handlers = []
    
    # Always add file handler for persistent logging
    file_handler = logging.handlers.RotatingFileHandler(
        f'{log_dir}/devsecops-backend.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(SafeFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    handlers.append(file_handler)
    
    # Only add console handler if we're not in a problematic multiprocessing environment
    # This prevents the buffer detachment issues
    try:
        # Test if we can write to stdout safely
        sys.stdout.write("")
        sys.stdout.flush()
        handlers.append(console_handler)
    except (ValueError, AttributeError, OSError):
        # Skip console logging if stdout is problematic
        pass
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # Force reconfiguration
    )
    
    # Create specific loggers for different components
    github_logger = logging.getLogger('github_client')
    github_logger.setLevel(logging.INFO)
    
    auth_logger = logging.getLogger('auth')
    auth_logger.setLevel(logging.INFO)
    
    performance_logger = logging.getLogger('performance')
    performance_logger.setLevel(logging.INFO)
    
    # Add separate file handler for GitHub operations with UTF-8 encoding
    github_handler = logging.handlers.RotatingFileHandler(
        f'{log_dir}/github-operations.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    github_handler.setFormatter(
        SafeFormatter('%(asctime)s - GitHub - %(levelname)s - %(message)s')
    )
    github_logger.addHandler(github_handler)
    
    # Add performance logger with UTF-8 support
    performance_handler = logging.handlers.RotatingFileHandler(
        f'{log_dir}/performance.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    performance_handler.setFormatter(
        SafeFormatter('%(asctime)s - Performance - %(levelname)s - %(message)s')
    )
    performance_logger.addHandler(performance_handler)
    
    # Mark logging as configured
    _logging_configured = True
    
    # Log that setup is complete (this will go to file if console is unavailable)
    logging.info("Logging configured successfully")
    logging.info(f"Log directory: {log_dir}")
    
    return {
        'github': github_logger,
        'auth': auth_logger,
        'performance': performance_logger
    }
