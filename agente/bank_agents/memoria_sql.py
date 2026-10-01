"""Servicio de memoria de ADK sobre PostgreSQL o SQLite (SQLAlchemy async).

Guarda el texto de los eventos por (app, user_id) y busca por palabras,
con el mismo criterio que InMemoryMemoryService de ADK: devuelve los diez
recuerdos que comparten mas palabras con la consulta. La memoria de cada
cliente queda aislada por user_id, igual que en Memory Bank.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone

from google.adk.memory.base_memory_service import (BaseMemoryService,
                                                    SearchMemoryResponse)
from google.adk.memory.memory_entry import MemoryEntry
from google.genai import types
from sqlalchemy import (Column, DateTime, Integer, MetaData, String, Table,
                        Text, UniqueConstraint, select)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncEngine

MAX_RESULTADOS = 10

_meta = MetaData()
recuerdos = Table(
    "recuerdos", _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("app_name", String(128), nullable=False, index=True),
    Column("user_id", String(128), nullable=False, index=True),
    Column("session_id", String(128)),
    Column("event_id", String(128), nullable=False),
    Column("autor", String(128)),
    Column("texto", Text, nullable=False),
    Column("creado", DateTime(timezone=True), nullable=False),
    UniqueConstraint("app_name", "user_id", "event_id", name="uq_recuerdo"),
)


def _palabras(texto: str) -> set[str]:
    texto = unicodedata.normalize("NFC", texto)
    return {p.lower() for p in re.findall(r"\w+", texto)}


def _texto_evento(evento) -> str:
    partes = getattr(getattr(evento, "content", None), "parts", None) or []
    return " ".join(p.text for p in partes if getattr(p, "text", None)).strip()


class MemoriaSQL(BaseMemoryService):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._lista = False

    async def _asegurar_tabla(self) -> None:
        if not self._lista:
            async with self._engine.begin() as con:
                await con.run_sync(_meta.create_all)
            self._lista = True

    def _insert(self):
        if self._engine.dialect.name == "postgresql":
            return pg_insert(recuerdos)
        return sqlite_insert(recuerdos)

    async def add_events_to_memory(
            self, *, app_name: str, user_id: str, events: Sequence,
            session_id: str | None = None,
            custom_metadata: Mapping[str, object] | None = None) -> None:
        await self._asegurar_tabla()
        filas = []
        for e in events:
            texto = _texto_evento(e)
            if not texto:
                continue
            filas.append({
                "app_name": app_name, "user_id": user_id,
                "session_id": session_id, "event_id": e.id,
                "autor": e.author, "texto": texto,
                "creado": datetime.fromtimestamp(e.timestamp, tz=timezone.utc)})
        if not filas:
            return
        stmt = self._insert().values(filas).on_conflict_do_nothing(
            index_elements=["app_name", "user_id", "event_id"])
        async with self._engine.begin() as con:
            await con.execute(stmt)

    async def add_session_to_memory(self, session) -> None:
        await self.add_events_to_memory(
            app_name=session.app_name, user_id=session.user_id,
            session_id=session.id, events=session.events)

    async def search_memory(self, *, app_name: str, user_id: str,
                            query: str) -> SearchMemoryResponse:
        await self._asegurar_tabla()
        buscadas = _palabras(query)
        async with self._engine.connect() as con:
            filas = (await con.execute(
                select(recuerdos.c.autor, recuerdos.c.texto, recuerdos.c.creado)
                .where(recuerdos.c.app_name == app_name,
                       recuerdos.c.user_id == user_id)
                .order_by(recuerdos.c.id))).all()
        puntuados = []
        for autor, texto, creado in filas:
            coinciden = len(buscadas & _palabras(texto))
            if coinciden:
                puntuados.append((coinciden, MemoryEntry(
                    content=types.Content(role="user" if autor == "user" else "model",
                                          parts=[types.Part(text=texto)]),
                    author=autor,
                    timestamp=creado.isoformat() if creado else None)))
        puntuados.sort(key=lambda x: -x[0])
        return SearchMemoryResponse(
            memories=[m for _, m in puntuados[:MAX_RESULTADOS]])
