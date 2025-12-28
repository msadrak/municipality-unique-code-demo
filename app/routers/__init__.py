# app/routers/__init__.py
"""
API Routers for Municipality ERP
================================
"""

from .budget import router as budget_router

__all__ = ["budget_router"]
