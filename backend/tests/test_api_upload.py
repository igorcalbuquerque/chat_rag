"""Tests for the POST /upload endpoint."""

from __future__ import annotations


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
