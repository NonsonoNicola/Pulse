from __future__ import annotations

from fastapi import Depends

# These will be set by main.py after app creation
_db = None
_analysis = None
_event_store = None
_kb = None
_llm_service = None


def set_dependencies(db, analysis, event_store, kb, llm_service):
    global _db, _analysis, _event_store, _kb, _llm_service
    _db = db
    _analysis = analysis
    _event_store = event_store
    _kb = kb
    _llm_service = llm_service


def get_db():
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


def get_analysis():
    if _analysis is None:
        raise RuntimeError("Analysis service not initialized")
    return _analysis


def get_event_store():
    if _event_store is None:
        raise RuntimeError("Event store not initialized")
    return _event_store


def get_kb():
    if _kb is None:
        raise RuntimeError("Knowledge base not initialized")
    return _kb


def get_llm_service():
    if _llm_service is None:
        raise RuntimeError("LLM service not initialized")
    return _llm_service