"""Tests for the ingestion service: chunking, embeddings and Redis indexing."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services import ingestion


def test_chunk_text_respects_size_and_overlap(monkeypatch):
    import tiktoken

    monkeypatch.setenv("CHUNK_SIZE", "50")
    monkeypatch.setenv("CHUNK_OVERLAP", "10")
    get_settings.cache_clear()

    text = "palavra " * 200
    chunks = ingestion.chunk_text(text)

    # Chunking is token-based: each chunk must stay within the token budget.
    enc = tiktoken.get_encoding("cl100k_base")
    assert len(chunks) > 1
    assert all(len(enc.encode(c)) <= 50 for c in chunks)


def test_chunk_text_skips_empty():
    assert ingestion.chunk_text("   \n  ") == []


def test_extract_text_txt():
    text = ingestion._extract_text("notes.txt", b"hello world")
    assert text == "hello world"


def test_extract_text_unsupported():
    with pytest.raises(ingestion.UnsupportedFileType):
        ingestion._extract_text("image.png", b"\x00\x01")


def test_ingest_file_indexes_chunks(fake_redis, fake_embeddings):
    data = ("frase de teste. " * 200).encode("utf-8")
    result = ingestion.ingest_file("doc.txt", data)

    assert result["status"] == "indexed"
    assert result["chunks_indexed"] > 0
    assert result["name"] == "doc.txt"

    # Each chunk is stored as a hash with the expected fields.
    prefix = get_settings().redis_key_prefix
    keys = list(fake_redis.scan_iter(match=f"{prefix}*"))
    assert len(keys) == result["chunks_indexed"]

    fields = fake_redis.hgetall(keys[0])
    assert b"content" in fields
    assert b"embedding" in fields
    assert fields[b"source"] == b"doc.txt"


def test_ingest_empty_file(fake_redis, fake_embeddings):
    result = ingestion.ingest_file("empty.txt", b"   ")
    assert result["chunks_indexed"] == 0
    assert result["status"] == "empty"
