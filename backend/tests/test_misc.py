"""Coverage for small edge cases across services and routers."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import HTTPException

from app import config
from app.services import documents, history


# --- config ---
def test_embedding_dimension_known_and_default(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
    config.get_settings.cache_clear()
    assert config.get_settings().embedding_dimension == 1536

    monkeypatch.setenv("EMBEDDING_MODEL", "some-unknown-model")
    config.get_settings.cache_clear()
    assert config.get_settings().embedding_dimension == config.DEFAULT_DIMENSION


# --- documents helpers ---
def test_decode_handles_none_str_bytes():
    assert documents._decode(None) == ""
    assert documents._decode("already") == "already"
    assert documents._decode(b"bytes") == "bytes"


def test_list_documents_skips_keys_without_file_id(fake_redis):
    prefix = config.get_settings().redis_key_prefix
    # A key under the prefix but missing the file_id field is ignored.
    fake_redis.hset(f"{prefix}orphan", mapping={"content": "x"})
    assert documents.list_documents() == []


# --- history ---
def test_get_history_skips_malformed_entries(fake_redis):
    key = history._key("s1", "public")
    fake_redis.rpush(key, b"not valid json")
    fake_redis.rpush(key, json.dumps({"role": "user", "content": "hi"}))

    assert history.get_history("s1") == [{"role": "user", "content": "hi"}]


# --- upload router ---
def test_upload_rejects_empty_file_list():
    from app.routers import upload

    with pytest.raises(HTTPException) as exc:
        asyncio.run(upload.upload(files=[]))
    assert exc.value.status_code == 400
