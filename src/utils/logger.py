"""
Logging Configuration

Centralized logging setup using loguru for colored, structured logging.
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(config: dict):
    """
    Setup logging based on configuration
    
    Args:
        config: Logging configuration dict from config.yaml
    """
    # Remove default logger
    logger.remove()
    
    # Console logging
    if config.get('console', {}).get('enabled', True):
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        
        logger.add(
            sys.stderr,
            format=log_format,
            level=config.get('level', 'INFO'),
            colorize=config.get('console', {}).get('colorized', True),
        )
    
    # File logging
    if config.get('file', {}).get('enabled', False):
        log_file = config['file']['path']
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=config.get('level', 'INFO'),
            rotation=f"{config['file'].get('max_size_mb', 100)} MB",
            retention=config['file'].get('backup_count', 5),
            compression="zip",
        )
    
    logger.info(f"Logging configured at level: {config.get('level', 'INFO')}")
