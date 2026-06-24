"""Tests for the POST /upload endpoint."""

from __future__ import annotations

from app import config
from app.config import get_settings


def test_upload_single_file(client, fake_embeddings):
    files = {"files": ("report.txt", b"texto de exemplo " * 100, "text/plain")}
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["chunks_indexed"] > 0
    assert len(body["files"]) == 1
    assert body["files"][0]["name"] == "report.txt"


def test_upload_multiple_files(client, fake_embeddings):
    files = [
        ("files", ("a.txt", b"conteudo a " * 80, "text/plain")),
        ("files", ("b.txt", b"conteudo b " * 80, "text/plain")),
    ]
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    assert len(response.json()["files"]) == 2


def test_upload_unsupported_type(client, fake_embeddings):
    files = {"files": ("image.png", b"\x89PNG", "image/png")}
    response = client.post("/upload", files=files)
    assert response.status_code == 415


def test_upload_rejects_oversized_file(client, fake_embeddings, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    config.get_settings.cache_clear()

    oversized = b"x" * (2 * 1024 * 1024)  # 2 MB > 1 MB limit
    files = {"files": ("big.txt", oversized, "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 413


def test_upload_rejects_too_many_files(client, fake_embeddings, monkeypatch):
    monkeypatch.setenv("MAX_FILES_PER_REQUEST", "1")
    config.get_settings.cache_clear()

    files = [
        ("files", ("a.txt", b"conteudo a " * 80, "text/plain")),
        ("files", ("b.txt", b"conteudo b " * 80, "text/plain")),
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 413


def test_upload_is_transactional_on_failure(client, fake_redis, fake_embeddings):
    # A valid file followed by an unsupported one: the request fails and the
    # valid file must NOT have been indexed (all-or-nothing).
    files = [
        ("files", ("ok.txt", b"conteudo valido " * 80, "text/plain")),
        ("files", ("bad.png", b"\x89PNG", "image/png")),
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 415

    prefix = get_settings().redis_key_prefix
    assert list(fake_redis.scan_iter(match=f"{prefix}*")) == []


def test_upload_scanned_pdf_without_ocr_returns_422(client, fake_embeddings, monkeypatch):
    import io

    from pypdf import PdfWriter

    from app.services import ingestion

    monkeypatch.setattr(ingestion, "_ocr_available", lambda: False)
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = io.BytesIO()
    writer.write(buffer)

    files = {"files": ("scan.pdf", buffer.getvalue(), "application/pdf")}
    response = client.post("/upload", files=files)
    assert response.status_code == 422
