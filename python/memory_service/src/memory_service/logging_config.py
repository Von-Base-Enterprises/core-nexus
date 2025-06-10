"""
Logging configuration for Core Nexus Memory Service.

Supports both local logging and remote syslog (Papertrail) for production.
"""

import logging
import logging.handlers
import os
import socket
import sys


def setup_papertrail_logging(
    papertrail_host: str = None,
    papertrail_port: int = None,
    app_name: str = "core-nexus-memory"
):
    """
    Configure logging to send to Papertrail via syslog.
    
    Args:
        papertrail_host: Papertrail host (e.g., 'logs.papertrailapp.com')
        papertrail_port: Papertrail port (e.g., 34949)
        app_name: Application name for log identification
    """
    # Get from environment if not provided
    if not papertrail_host:
        papertrail_host = os.getenv('PAPERTRAIL_HOST', 'logs.papertrailapp.com')
    if not papertrail_port:
        papertrail_port = int(os.getenv('PAPERTRAIL_PORT', '34949'))

    # Skip if no valid configuration
    if not papertrail_host or not papertrail_port:
        logging.warning("Papertrail configuration not found, using local logging only")
        return False

    try:
        # Create syslog handler for Papertrail
        handler = logging.handlers.SysLogHandler(
            address=(papertrail_host, papertrail_port),
            facility=logging.handlers.SysLogHandler.LOG_LOCAL0,
            socktype=socket.SOCK_DGRAM
        )

        # Format for Papertrail - includes hostname and app name
        hostname = socket.gethostname()
        formatter = logging.Formatter(
            f'{hostname} {app_name}: %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

        # Also add to specific loggers
        app_logger = logging.getLogger('memory_service')
        app_logger.addHandler(handler)

        # Log successful setup
        logging.info(f"Papertrail logging configured: {papertrail_host}:{papertrail_port}")
        return True

    except Exception as e:
        logging.error(f"Failed to configure Papertrail logging: {e}")
        return False


def setup_logging():
    """
    Configure comprehensive logging for the application.
    
    Sets up:
    - Console logging (always enabled)
    - File logging (if LOG_FILE env var is set)
    - Papertrail logging (if configured)
    """
    # Basic configuration
    log_level = os.getenv('LOG_LEVEL', 'INFO')

    # Console handler - always enabled
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)

    # File handler - optional
    log_file = os.getenv('LOG_FILE')
    if log_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(console_formatter)
            root_logger.addHandler(file_handler)
            logging.info(f"File logging enabled: {log_file}")
        except Exception as e:
            logging.error(f"Failed to setup file logging: {e}")

    # Papertrail handler - optional
    setup_papertrail_logging()

    # Log startup
    logging.info("=" * 60)
    logging.info("Core Nexus Memory Service Starting")
    logging.info(f"Log Level: {log_level}")
    logging.info(f"Python Version: {sys.version}")
    logging.info("=" * 60)


# Specialized loggers
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f"memory_service.{name}")
