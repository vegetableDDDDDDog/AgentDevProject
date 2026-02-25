"""
API Routers Package

Contains all API route modules for the Agent Platform.
"""

# Import routers here for easy registration
from api.routers import chat, agents, sessions

__all__ = ["chat", "agents", "sessions"]
