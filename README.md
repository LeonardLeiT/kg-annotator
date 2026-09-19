# KG Annotator

[中文](#中文说明) · [English](#english)

## 中文说明

面向领域 PDF 的知识图谱人工标注工具。实体由标注员在原文中直接划选；后台保留三轮独立抽取用于 Fleiss' Kappa 一致性评估，人工确认后再通过名称与上下文向量进行跨文档实体去重。网页界面支持中文和 English 即时切换。

### 功能

- PDF 上传、按页解析与中英文句子切分
- 独立公式重建、PDF 原式截图与前后文关联
- 文档级三轮独立抽取：整篇完成一轮后才开始下一轮
- 随机句子子集上的三轮 Fleiss' Kappa（实体、关系和总体）评估
- 纯人工实体边界与类型标注，不向标注员预填模型候选
- 丰富的关系类型词表、按实体类型推荐及人工关系编辑
- 单篇文章人工确认结果的 KG 聚合与证据追溯
- 网页知识图谱可视化，以及 JSONL、CSV、Gephi GEXF 导出
- 智谱 BigModel `embedding-3` 跨文档实体去重
- 中文／英文网页界面
- 无 API Key 时使用规则型演示抽取器和本地字符向量

### 快速启动

后端：

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`。API 文档位于 `http://localhost:8000/docs`。

复制 `.env.example` 为 `.env` 并设置模型配置。未设置 API Key 时使用可离线运行的规则型抽取器。

```dotenv
DEEPSEEK_API_KEY=your-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

BIGMODEL_API_KEY=your-key
BIGMODEL_EMBEDDING_URL=https://open.bigmodel.cn/api/paas/v4/embeddings
EMBEDDING_MODEL=embedding-3
EMBEDDING_DIMENSIONS=1024
```

### 数据原则

- 实体标注以字符偏移量为准，分词仅作为辅助信息。
- 三次模型原始输出与人工最终标注分别存储；模型结果不在人工标注页预填或展示。
- 名称完全相同且综合相似度达到 99% 的实体自动合并；名称不同的候选必须人工选择规范名称；低于 85% 不处理。
- 合并后的 `aliases` 汇总两侧规范名称及其全部历史别名。
- 人工拒绝的实体对会保留决定，后续不再重复出现。
- 实体合并不删除原始 mention，所有事实均可追溯到文档、页码和句子。
- `.env`、PDF、SQLite、标注数据和公式截图默认被 Git 忽略。

### 当前范围

这是第一版可运行 MVP。文本型 PDF 可直接解析；扫描 PDF/OCR、多人权限、复杂版面坐标和 Neo4j 发布层预留为后续扩展。

---

## English

KG Annotator is a manual knowledge-graph annotation tool for domain PDFs. Annotators select entity spans directly in the source text. Three independent model runs are retained in the background for Fleiss' Kappa agreement evaluation, while name and context embeddings support cross-document entity resolution after human review. The web interface can switch instantly between Chinese and English.

### Features

- PDF upload, page-level parsing, and Chinese/English sentence segmentation
- Reconstruction of standalone formulas with original-PDF snapshots and surrounding context
- Three independent document-level extraction runs, completed sequentially by full document
- Entity, relation, and overall Fleiss' Kappa on reproducible random sentence subsets
- Fully manual entity span and type annotation without prefilled model candidates
- Extensive relation ontology, type-aware recommendations, and manual relation editing
- Article-level KG aggregation with evidence provenance
- Interactive graph visualization plus JSONL, CSV, and Gephi GEXF exports
- Cross-document entity resolution with BigModel `embedding-3`
- Chinese and English web interface
- Offline rule-based demonstration extractor and local character embeddings when API keys are absent

### Quick start

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API documentation is available at `http://localhost:8000/docs`.

Copy `.env.example` to `.env` and configure the model providers. Without an API key, the backend falls back to the offline rule-based extractor.

```dotenv
DEEPSEEK_API_KEY=your-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

BIGMODEL_API_KEY=your-key
BIGMODEL_EMBEDDING_URL=https://open.bigmodel.cn/api/paas/v4/embeddings
EMBEDDING_MODEL=embedding-3
EMBEDDING_DIMENSIONS=1024
```

### Data principles

- Entity annotations use character offsets; tokenization is only an aid.
- Raw outputs from the three model runs and final human annotations are stored separately. Model candidates are not prefilled or shown on the annotation screen.
- Exactly identical names with at least 99% combined similarity are merged automatically. Differently named candidates require a human choice of preferred name; scores below 85% are ignored.
- A merged entity's `aliases` collect both preferred names and all historical aliases.
- Rejected merge pairs are remembered and are not proposed again.
- Entity merging preserves original mentions and provenance down to document, page, and sentence.
- `.env`, PDFs, SQLite databases, annotation data, and formula images are ignored by Git by default.

### Current scope

This is a runnable MVP. Text-based PDFs are supported directly. OCR for scanned PDFs, multi-user permissions, advanced layout coordinates, and a Neo4j publication layer are reserved for future work.
