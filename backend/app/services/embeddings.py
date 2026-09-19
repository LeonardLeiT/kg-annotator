from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

import httpx

from ..config import get_settings


class EmbeddingProvider(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class LangChainEmbeddingProvider:
    name = "langchain-openai"

    def __init__(self) -> None:
        from langchain_openai import OpenAIEmbeddings

        settings = get_settings()
        self.client = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.client.embed_documents(texts)


class BigModelEmbeddingProvider:
    """智谱 embedding-3 provider using the official HTTP endpoint."""

    name = "bigmodel-embedding-3"
    max_batch_size = 64

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.bigmodel_api_key
        if not self.api_key:
            raise ValueError("未配置 BIGMODEL_API_KEY")
        self.endpoint = endpoint or settings.bigmodel_embedding_url
        self.model = model or settings.embedding_model
        self.dimensions = dimensions or settings.embedding_dimensions
        if self.model == "embedding-3" and self.dimensions not in {256, 512, 1024, 2048}:
            raise ValueError("embedding-3 dimensions 必须是 256、512、1024 或 2048")
        self.client = httpx.Client(timeout=30.0, transport=transport)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.max_batch_size):
            batch = texts[start:start + self.max_batch_size]
            payload: dict[str, object] = {"model": self.model, "input": batch}
            if self.model == "embedding-3":
                payload["dimensions"] = self.dimensions
            response = self.client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            ordered = sorted(data, key=lambda item: item["index"])
            if len(ordered) != len(batch):
                raise ValueError(f"BigModel 返回向量数量异常: 期望 {len(batch)}，实际 {len(ordered)}")
            for item in ordered:
                vector = item.get("embedding")
                if not isinstance(vector, list) or len(vector) != self.dimensions:
                    raise ValueError("BigModel 返回了无效的 embedding 维度")
                vectors.append([float(value) for value in vector])
        return vectors


class LocalHashEmbeddingProvider:
    """Deterministic offline fallback; useful for demos, not semantic matching."""

    name = "local-hash"
    dimensions = 256

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        normalized = re.sub(r"\s+", "", text.casefold())
        padded = f"  {normalized}  "
        vector = [0.0] * self.dimensions
        for index in range(max(1, len(padded) - 2)):
            token = padded[index:index + 3]
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
            bucket = int.from_bytes(digest, "big") % self.dimensions
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.bigmodel_api_key:
        return BigModelEmbeddingProvider()
    if settings.openai_api_key:
        return LangChainEmbeddingProvider()
    return LocalHashEmbeddingProvider()
