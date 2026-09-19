# KG Annotator

面向领域 PDF 的知识图谱人工标注工具。实体由标注员在原文中直接划选；后台保留三轮独立抽取用于 Fleiss' Kappa 一致性评估，人工确认后再通过名称与上下文向量进行跨文档实体去重。

## 功能

- PDF 上传、按页解析与中英文句子切分
- 独立公式重建、PDF 原式截图与前后文关联
- 基于 LangChain structured output 的实体/关系抽取
- 文档级三轮独立抽取：整篇完成一轮后才开始下一轮
- 随机句子子集上的三轮 Fleiss' Kappa（实体、关系和总体）评估
- 纯人工实体边界与类型标注，不向标注员预填模型候选
- 关系类型推荐下拉词表与人工关系编辑
- 单篇文章人工确认结果的 KG 聚合与证据追溯
- 网页知识图谱可视化，以及 JSONL、CSV、Gephi GEXF 导出
- 智谱 BigModel `embedding-3` 跨文档实体去重：≥99% 自动合并，85%–99% 人工审核
- 无 API Key 时使用规则型演示抽取器和本地字符向量

## 快速启动

### 后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

### 前端

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`。API 文档位于 `http://localhost:8000/docs`。

复制 `.env.example` 为 `.env` 并设置模型配置后，后端会自动使用 LangChain 调用结构化输出模型；未设置 API Key 时会使用可离线运行的规则型抽取器。

DeepSeek 示例：

```dotenv
DEEPSEEK_API_KEY=your-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

BigModel embedding 示例：

```dotenv
BIGMODEL_API_KEY=your-key
BIGMODEL_EMBEDDING_URL=https://open.bigmodel.cn/api/paas/v4/embeddings
EMBEDDING_MODEL=embedding-3
EMBEDDING_DIMENSIONS=1024
```

## 数据原则

- 实体标注以字符偏移量为准，分词仅作为辅助信息。
- 三次模型原始输出与人工最终标注分别存储；模型结果不在人工标注页预填或展示。
- 名称完全相同且跨文档综合相似度达到 99% 的实体自动合并；名称不同的候选必须人工选择合并后的规范名称；低于 85% 不处理。
- 合并后的 `aliases` 汇总两侧规范名称及其全部历史别名。
- 人工拒绝的实体对会保留决定，后续重新生成时不再重复出现。
- 实体合并不会删除原始 mention，所有事实都可追溯到文档、页码和句子。

## 当前范围

这是第一版可运行 MVP。文本型 PDF 可直接解析；扫描 PDF/OCR、多人权限、复杂版面坐标和 Neo4j 发布层预留为后续扩展。
