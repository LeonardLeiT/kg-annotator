from app import api
from app.models import Document


class FakeSession:
    def __init__(self, document: Document):
        self.document = document
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, model, document_id):
        assert model is Document
        return self.document if document_id == self.document.id else None

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_background_parser_uses_an_independent_session(monkeypatch):
    document = Document(id="doc-1", filename="paper.pdf", storage_path="paper.pdf", status="parsing")
    session = FakeSession(document)
    called = []
    monkeypatch.setattr(api, "SessionLocal", lambda: session)
    monkeypatch.setattr(api, "parse_pdf", lambda db, row: called.append((db, row)))

    api.parse_document_in_background(document.id)

    assert called == [(session, document)]
    assert session.rollbacks == 0


def test_background_parser_records_failure_without_breaking_requests(monkeypatch):
    document = Document(id="doc-2", filename="broken.pdf", storage_path="broken.pdf", status="parsing")
    session = FakeSession(document)
    monkeypatch.setattr(api, "SessionLocal", lambda: session)

    def fail(*_args):
        raise RuntimeError("bad PDF")

    monkeypatch.setattr(api, "parse_pdf", fail)
    api.parse_document_in_background(document.id)

    assert session.rollbacks == 1
    assert session.commits == 1
    assert document.status == "parse_failed"
