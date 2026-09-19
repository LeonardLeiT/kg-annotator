import json

import httpx

from app.services.embeddings import BigModelEmbeddingProvider, LocalHashEmbeddingProvider
from app.services.resolution import classify_similarity, cosine


def test_local_embedding_is_deterministic_and_normalized():
    provider = LocalHashEmbeddingProvider()
    left, same, different = provider.embed_documents(["polyethylene", "polyethylene", "hardness"])

    assert left == same
    assert cosine(left, same) > 0.99
    assert cosine(left, different) < 0.5


def test_bigmodel_embedding_orders_response_and_sends_dimensions():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={
            "data": [
                {"index": 1, "embedding": [0.0, 1.0] + [0.0] * 254},
                {"index": 0, "embedding": [1.0, 0.0] + [0.0] * 254},
            ]
        })

    provider = BigModelEmbeddingProvider(
        api_key="test-key",
        endpoint="https://example.test/embeddings",
        model="embedding-3",
        dimensions=256,
        transport=httpx.MockTransport(handler),
    )
    vectors = provider.embed_documents(["材料", "性质"])
    assert vectors[0][:2] == [1.0, 0.0]
    assert vectors[1][:2] == [0.0, 1.0]
    assert all(len(vector) == 256 for vector in vectors)
    assert captured["authorization"] == "Bearer test-key"
    assert captured["payload"] == {
        "model": "embedding-3", "input": ["材料", "性质"], "dimensions": 256,
    }


def test_embedding_merge_policy_thresholds():
    assert classify_similarity(0.999) == "auto_merge"
    assert classify_similarity(0.99) == "auto_merge"
    assert classify_similarity(0.989) == "candidate"
    assert classify_similarity(0.85) == "candidate"
    assert classify_similarity(0.849) == "ignore"
