#!/usr/bin/env python3
"""
Fixed server startup script that properly handles logging with uvicorn
"""
import os
import uvicorn
from pathlib import Path

def main():
    """Start the FastAPI server with proper logging configuration"""
    
    # Set working directory to backend folder
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Configure uvicorn logging to avoid conflicts
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(asctime)s %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["default"],
        },
    }
    
    print("🚀 Starting DevSecOps Backend Server...")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Start uvicorn with optimized settings for development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[".", "./api", "./core", "./database"],
        log_config=log_config,
        access_log=True,
        use_colors=True,
        # Disable default uvicorn logging that conflicts with our setup
        log_level="info"
    )

if __name__ == "__main__":
    main()