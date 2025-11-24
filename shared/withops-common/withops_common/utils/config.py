"""
Configuration utilities for microservices
"""

import os
from typing import Optional
from pydantic import BaseModel


class ServiceConfig(BaseModel):
    """Base configuration for all microservices"""
    service_name: str
    service_port: int
    environment: str = "development"
    
    # Database
    database_url: Optional[str] = None
    
    # Redis
    redis_url: str = "redis://redis:6379"
    
    # Auth
    auth0_domain: Optional[str] = None
    auth0_audience: Optional[str] = None
    
    # Monitoring
    enable_metrics: bool = True
    enable_tracing: bool = True
    
    # Logging
    log_level: str = "INFO"


def get_config(service_name: str, service_port: int) -> ServiceConfig:
    """
    Get configuration from environment variables
    """
    return ServiceConfig(
        service_name=service_name,
        service_port=service_port,
        environment=os.getenv("ENVIRONMENT", "development"),
        database_url=os.getenv("DATABASE_URL"),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379"),
        auth0_domain=os.getenv("AUTH0_DOMAIN"),
        auth0_audience=os.getenv("AUTH0_AUDIENCE"),
        enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
        enable_tracing=os.getenv("ENABLE_TRACING", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
