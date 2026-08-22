"""Storage package for persistent SQLite DAO repositories.
"""

from backend.app.storage.corpus_repository import CorpusRepository, get_corpus_repository

__all__ = ["CorpusRepository", "get_corpus_repository"]
