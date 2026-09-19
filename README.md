<div align="center">

# KG Annotator

### Human-centered knowledge graph annotation for scientific PDFs

Upload papers, annotate entities and relations manually, evaluate three independent extraction runs, resolve entities across documents, and export an auditable knowledge graph.

[English](README.md) · [Chinese](README_zh.md)

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=20232A)
![TypeScript](https://img.shields.io/badge/TypeScript-Ready-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-Build-646CFF?logo=vite&logoColor=white)

</div>

---

## Overview

KG Annotator is a local-first annotation workspace for turning domain literature into traceable knowledge graphs. Annotators select entity spans directly in the source sentence or formula, assign entity types, and create typed relations. Model outputs are kept separate from the manual interface to avoid biasing human decisions.

Three independent extraction runs are retained in the background for reproducible Fleiss' Kappa agreement evaluation. After review, name and context embeddings support cross-document entity resolution while preserving every original mention and alias.

## Highlights

| Area | Capabilities |
| --- | --- |
| PDF processing | Page-level extraction, Chinese/English sentence segmentation, standalone formula reconstruction, original-formula snapshots, and surrounding context |
| Manual annotation | Character-accurate entity spans, configurable entity types, extensive relation ontology, type-aware relation suggestions, Pass and uncertain decisions |
| Agreement | Entity, relation, and overall Fleiss' Kappa on reproducible random sentence subsets |
| Knowledge graph | Article-level aggregation, evidence provenance, interactive graph visualization, JSONL, CSV, and Gephi GEXF exports |
| Entity resolution | BigModel `embedding-3`, 85% review threshold, exact-name auto-merge policy, human-selected preferred names, and accumulated aliases |
| Interface | Instant Chinese/English switching with the selected language remembered locally |

## Workflow

```mermaid
flowchart LR
    A[Upload PDF] --> B[Parse sentences and formulas]
    B --> C[Three independent model runs]
    C --> D[Fleiss' Kappa evaluation]
    B --> E[Manual entity annotation]
    E --> F[Manual relation annotation]
    F --> G[Article knowledge graph]
    G --> H[Cross-document entity resolution]
    H --> I[JSONL / CSV / GEXF]
```

## Technology

- **Backend:** FastAPI, SQLAlchemy, Pydantic, PyMuPDF, LangChain
- **Frontend:** React, TypeScript, Vite
- **LLM:** OpenAI-compatible structured output, tested with DeepSeek
- **Embeddings:** BigModel `embedding-3`
- **Storage:** SQLite for the local MVP

## Quick start

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Model configuration

Copy `.env.example` to `.env` and add the provider credentials you want to use:

```dotenv
DEEPSEEK_API_KEY=your-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

BIGMODEL_API_KEY=your-key
BIGMODEL_EMBEDDING_URL=https://open.bigmodel.cn/api/paas/v4/embeddings
EMBEDDING_MODEL=embedding-3
EMBEDDING_DIMENSIONS=1024
```

Without an API key, the backend falls back to the offline rule-based demonstration extractor and local character embeddings.

## Annotation and resolution policy

- Entity boundaries are stored as character offsets; tokenization is only an annotation aid.
- Raw outputs from the three model runs and final human annotations are stored separately.
- Model candidates are neither prefilled nor shown on the manual annotation screen.
- Only exactly identical names with at least 99% combined similarity are merged automatically.
- Differently named candidates require a human choice of preferred name; scores from 85% upward are presented for review.
- A merged entity's `aliases` collect both preferred names and all historical aliases.
- Rejected merge pairs are remembered and are not proposed again.
- Merging preserves original mentions and provenance down to document, page, and sentence.

## Data privacy

The repository is configured to exclude local research and credentials. The following remain on the user's machine and are ignored by Git:

- `.env` and API keys
- uploaded PDF files
- SQLite databases and annotation records
- generated formula images and temporary files
- dependencies, caches, and build output

## Current scope

This repository contains a runnable MVP for text-based PDFs. OCR for scanned documents, multi-user permissions, advanced layout coordinates, and a Neo4j publication layer are planned extensions.

---

<div align="center">
Built for transparent, reviewable scientific knowledge extraction.
</div>
