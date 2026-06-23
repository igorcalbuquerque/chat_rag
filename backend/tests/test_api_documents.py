"""Tests for GET /documents and DELETE /documents/{id}."""

from __future__ import annotations


def _upload(client):
    files = {"files": ("doc.txt", b"algum conteudo " * 100, "text/plain")}
    return client.post("/upload", files=files).json()


def test_list_documents_empty(client, fake_embeddings):
    response = client.get("/documents")
    assert response.status_code == 200
    assert response.json() == []


def test_list_documents_after_upload(client, fake_embeddings):
    uploaded = _upload(client)
    response = client.get("/documents")

    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 1
    assert docs[0]["file_id"] == uploaded["file_id"]
    assert docs[0]["name"] == "doc.txt"
    assert docs[0]["chunks"] == uploaded["chunks_indexed"]


def test_delete_document(client, fake_embeddings):
    uploaded = _upload(client)
    file_id = uploaded["file_id"]

    response = client.delete(f"/documents/{file_id}")
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # Document is gone afterwards.
    assert client.get("/documents").json() == []


def test_delete_missing_document(client, fake_embeddings):
    response = client.delete("/documents/does-not-exist")
    assert response.status_code == 404
