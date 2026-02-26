"""
Agent package for inventory management.

Re-exports the main agent functions for convenient imports:
    from src.agent import run_inventory_agent, create_inventory_agent
"""
from .core import create_inventory_agent, run_inventory_agent

__all__ = [
    "create_inventory_agent",
    "run_inventory_agent",
]

