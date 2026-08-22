"""SQLite repository for LiteratureCorpus state, papers, evidence records, and matrices.

Provides lightweight async DAO layer using SQLite in data/research_state.db.
"""

from __future__ import annotations

import os
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite

from backend.app.models.paper import PaperRecord
from backend.app.models.evidence import EvidenceRecord
from backend.app.models.corpus import LiteratureCorpus, EvidenceMatrix, MatrixCell
from backend.app.models.review import SynthesisResult, CompiledReview

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "./data/research_state.db"


class CorpusRepository:
    """Async SQLite Data Access Object for Literature Review workspaces."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(Path(db_path or os.getenv("RESEARCH_DB_PATH", DEFAULT_DB_PATH)).resolve())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    async def initialize(self) -> None:
        """Create tables if they do not exist."""
        if self._initialized:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            
            # Corpora table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS corpora (
                    corpus_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    domain_profile TEXT,
                    created_at REAL,
                    updated_at REAL
                );
            """)
            
            # Corpus-Paper relationship & screening status
            await db.execute("""
                CREATE TABLE IF NOT EXISTS corpus_papers (
                    corpus_id TEXT NOT NULL,
                    paper_id TEXT NOT NULL,
                    screening_status TEXT NOT NULL,
                    exclusion_reason TEXT,
                    PRIMARY KEY (corpus_id, paper_id),
                    FOREIGN KEY (corpus_id) REFERENCES corpora(corpus_id) ON DELETE CASCADE,
                    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
                );
            """)

            # Shared Papers table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    paper_id TEXT PRIMARY KEY,
                    doi TEXT,
                    title TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );
            """)

            # Evidence Records table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS evidence_records (
                    evidence_id TEXT PRIMARY KEY,
                    corpus_id TEXT NOT NULL,
                    paper_id TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    FOREIGN KEY (corpus_id) REFERENCES corpora(corpus_id) ON DELETE CASCADE
                );
            """)

            # Evidence Matrices table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS evidence_matrices (
                    matrix_id TEXT PRIMARY KEY,
                    corpus_id TEXT NOT NULL,
                    schema_json TEXT NOT NULL,
                    cells_json TEXT NOT NULL,
                    FOREIGN KEY (corpus_id) REFERENCES corpora(corpus_id) ON DELETE CASCADE
                );
            """)

            # Synthesis Results table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS synthesis_results (
                    synthesis_id TEXT PRIMARY KEY,
                    corpus_id TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    FOREIGN KEY (corpus_id) REFERENCES corpora(corpus_id) ON DELETE CASCADE
                );
            """)

            # Compiled Reviews table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS compiled_reviews (
                    review_id TEXT PRIMARY KEY,
                    corpus_id TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    FOREIGN KEY (corpus_id) REFERENCES corpora(corpus_id) ON DELETE CASCADE
                );
            """)

            await db.commit()
        self._initialized = True
        logger.info(f"CorpusRepository initialized DB schema at {self.db_path}")

    async def save_corpus(self, corpus: LiteratureCorpus) -> None:
        await self.initialize()
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO corpora (corpus_id, query, domain_profile, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(corpus_id) DO UPDATE SET
                    query=excluded.query,
                    domain_profile=excluded.domain_profile,
                    updated_at=excluded.updated_at;
                """,
                (
                    corpus.corpus_id,
                    corpus.query,
                    json.dumps(corpus.domain_profile),
                    corpus.created_at or now,
                    now,
                )
            )

            # Sync paper relationships: delete prior snapshot for current corpus
            await db.execute("DELETE FROM corpus_papers WHERE corpus_id = ?;", (corpus.corpus_id,))
            for pid in corpus.paper_ids:
                status = "included" if pid in corpus.included_paper_ids else ("excluded" if pid in corpus.excluded_paper_ids else "retrieved")
                reason = corpus.exclusion_reasons.get(pid)
                await db.execute(
                    """
                    INSERT INTO corpus_papers (corpus_id, paper_id, screening_status, exclusion_reason)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(corpus_id, paper_id) DO UPDATE SET
                        screening_status=excluded.screening_status,
                        exclusion_reason=excluded.exclusion_reason;
                    """,
                    (corpus.corpus_id, pid, status, reason)
                )
            await db.commit()

    async def get_corpus(self, corpus_id: str) -> Optional[LiteratureCorpus]:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM corpora WHERE corpus_id = ?;", (corpus_id,))
            row = await cursor.fetchone()
            if not row:
                return None

            p_cursor = await db.execute("SELECT paper_id, screening_status, exclusion_reason FROM corpus_papers WHERE corpus_id = ?;", (corpus_id,))
            p_rows = await p_cursor.fetchall()

            paper_ids = []
            included_ids = []
            excluded_ids = []
            exclusion_reasons = {}
            for pr in p_rows:
                pid = pr["paper_id"]
                paper_ids.append(pid)
                status = pr["screening_status"]
                if status == "included":
                    included_ids.append(pid)
                elif status == "excluded":
                    excluded_ids.append(pid)
                    if pr["exclusion_reason"]:
                        exclusion_reasons[pid] = pr["exclusion_reason"]

            # Fetch evidence IDs
            ev_cursor = await db.execute("SELECT evidence_id FROM evidence_records WHERE corpus_id = ?;", (corpus_id,))
            ev_rows = await ev_cursor.fetchall()
            evidence_ids = [r["evidence_id"] for r in ev_rows]

            # Matrix ID
            m_cursor = await db.execute("SELECT matrix_id FROM evidence_matrices WHERE corpus_id = ? LIMIT 1;", (corpus_id,))
            m_row = await m_cursor.fetchone()
            matrix_id = m_row["matrix_id"] if m_row else None

            # Synthesis ID
            s_cursor = await db.execute("SELECT synthesis_id FROM synthesis_results WHERE corpus_id = ? LIMIT 1;", (corpus_id,))
            s_row = await s_cursor.fetchone()
            synthesis_id = s_row["synthesis_id"] if s_row else None

            domain_profile = json.loads(row["domain_profile"]) if row["domain_profile"] else {}

            return LiteratureCorpus(
                corpus_id=row["corpus_id"],
                query=row["query"],
                domain_profile=domain_profile,
                paper_ids=paper_ids,
                included_paper_ids=included_ids,
                excluded_paper_ids=excluded_ids,
                exclusion_reasons=exclusion_reasons,
                evidence_ids=evidence_ids,
                matrix_id=matrix_id,
                synthesis_id=synthesis_id,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def save_papers(self, papers: List[PaperRecord]) -> None:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            for p in papers:
                await db.execute(
                    """
                    INSERT INTO papers (paper_id, doi, title, data_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(paper_id) DO UPDATE SET
                        doi=excluded.doi,
                        title=excluded.title,
                        data_json=excluded.data_json;
                    """,
                    (p.paper_id, p.doi, p.title, json.dumps(p.model_dump()))
                )
            await db.commit()

    async def get_papers(self, paper_ids: List[str]) -> List[PaperRecord]:
        if not paper_ids:
            return []
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            placeholders = ",".join("?" for _ in paper_ids)
            cursor = await db.execute(f"SELECT data_json FROM papers WHERE paper_id IN ({placeholders});", paper_ids)
            rows = await cursor.fetchall()
            papers = []
            for r in rows:
                data = json.loads(r["data_json"])
                papers.append(PaperRecord.from_dict(data))
            return papers

    async def save_evidence_records(self, corpus_id: str, records: List[EvidenceRecord]) -> None:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            for r in records:
                ev_id = r.evidence_id if r.evidence_id.startswith(f"{corpus_id}_") else f"{corpus_id}_{r.evidence_id}"
                r.evidence_id = ev_id
                await db.execute(
                    """
                    INSERT INTO evidence_records (evidence_id, corpus_id, paper_id, data_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(evidence_id) DO UPDATE SET
                        corpus_id=excluded.corpus_id,
                        data_json=excluded.data_json;
                    """,
                    (r.evidence_id, corpus_id, r.paper_id, json.dumps(r.model_dump()))
                )
            await db.commit()

    async def get_evidence_records(self, evidence_ids: List[str]) -> List[EvidenceRecord]:
        if not evidence_ids:
            return []
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            placeholders = ",".join("?" for _ in evidence_ids)
            cursor = await db.execute(f"SELECT data_json FROM evidence_records WHERE evidence_id IN ({placeholders});", evidence_ids)
            rows = await cursor.fetchall()
            records = []
            for r in rows:
                data = json.loads(r["data_json"])
                records.append(EvidenceRecord(**data))
            return records

    async def get_evidence_records_by_corpus(self, corpus_id: str) -> List[EvidenceRecord]:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT data_json FROM evidence_records WHERE corpus_id = ?;", (corpus_id,))
            rows = await cursor.fetchall()
            records = []
            for r in rows:
                data = json.loads(r["data_json"])
                records.append(EvidenceRecord(**data))
            return records

    async def save_evidence_matrix(self, matrix: EvidenceMatrix) -> None:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            rows_dump = {
                pid: {col_key: cell.model_dump() for col_key, cell in col_map.items()}
                for pid, col_map in matrix.rows.items()
            }
            await db.execute(
                """
                INSERT INTO evidence_matrices (matrix_id, corpus_id, schema_json, cells_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(matrix_id) DO UPDATE SET
                    schema_json=excluded.schema_json,
                    cells_json=excluded.cells_json;
                """,
                (matrix.matrix_id, matrix.corpus_id, json.dumps(matrix.columns), json.dumps(rows_dump))
            )
            await db.commit()

    async def get_evidence_matrix(self, corpus_id: str) -> Optional[EvidenceMatrix]:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM evidence_matrices WHERE corpus_id = ? ORDER BY rowid DESC LIMIT 1;", (corpus_id,))
            row = await cursor.fetchone()
            if not row:
                return None

            columns = json.loads(row["schema_json"])
            raw_cells = json.loads(row["cells_json"])
            parsed_rows: Dict[str, Dict[str, MatrixCell]] = {}
            for pid, col_map in raw_cells.items():
                parsed_rows[pid] = {col_key: MatrixCell(**c_data) for col_key, c_data in col_map.items()}

            return EvidenceMatrix(
                matrix_id=row["matrix_id"],
                corpus_id=row["corpus_id"],
                columns=columns,
                rows=parsed_rows,
            )

    async def save_synthesis_result(self, synthesis: SynthesisResult) -> None:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO synthesis_results (synthesis_id, corpus_id, data_json)
                VALUES (?, ?, ?)
                ON CONFLICT(synthesis_id) DO UPDATE SET
                    data_json=excluded.data_json;
                """,
                (synthesis.synthesis_id, synthesis.corpus_id, json.dumps(synthesis.model_dump()))
            )
            await db.commit()

    async def get_synthesis_result(self, corpus_id: str) -> Optional[SynthesisResult]:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT data_json FROM synthesis_results WHERE corpus_id = ? ORDER BY rowid DESC LIMIT 1;", (corpus_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return SynthesisResult(**json.loads(row["data_json"]))

    async def save_compiled_review(self, review: CompiledReview) -> None:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO compiled_reviews (review_id, corpus_id, data_json)
                VALUES (?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET
                    data_json=excluded.data_json;
                """,
                (review.review_id, review.corpus_id, json.dumps(review.model_dump()))
            )
            await db.commit()

    async def get_compiled_review(self, corpus_id: str) -> Optional[CompiledReview]:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT data_json FROM compiled_reviews WHERE corpus_id = ? ORDER BY rowid DESC LIMIT 1;", (corpus_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return CompiledReview(**json.loads(row["data_json"]))


# Global singleton instance accessor
_repository_instance: Optional[CorpusRepository] = None


def get_corpus_repository(db_path: Optional[str] = None) -> CorpusRepository:
    global _repository_instance
    if _repository_instance is None or db_path is not None:
        _repository_instance = CorpusRepository(db_path=db_path)
    return _repository_instance
