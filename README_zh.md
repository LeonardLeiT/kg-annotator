<div align="center">

# KG Annotator

### 面向科研 PDF 的人工知识图谱标注工具

上传论文、以不限次数的版本人工标注实体与关系、评估标注一致性、执行跨文章实体消歧，并导出证据可追溯的知识图谱。

[English](README.md) · [中文](README_zh.md)

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-后端-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-前端-61DAFB?logo=react&logoColor=20232A)
![TypeScript](https://img.shields.io/badge/TypeScript-类型安全-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-构建-646CFF?logo=vite&logoColor=white)

</div>

---

## 项目简介

KG Annotator 是一个本地优先的领域文献知识图谱标注工作台。PDF 只解析和分句一次，之后由标注员直接在原始句子或公式中划选实体边界、指定实体类型，并创建有类型的关系，不使用模型候选干预人工判断。

首轮人工标注完成后，知识图谱即可直接使用。之后每次保存都会形成不可变的标注版本，图谱始终采用最新版本，修订次数不设上限。当人工版本数量足够时，可计算 Fleiss' Kappa。系统还通过名称和上下文 embedding 辅助跨文章实体消歧，同时保留全部原始 mention、别名和证据来源。

## 核心能力

| 模块 | 能力 |
| --- | --- |
| PDF 处理 | 按页解析、中英文分句、独立公式重建、PDF 原式截图与前后文关联 |
| 人工标注 | 可在前文／本句／后文进行字符级实体划选、建立跨句关系、配置类型，并支持 Pass、不确定状态与不限次数修订 |
| 一致性评估 | 对两个及以上人工标注版本，在可复现的随机句子子集上计算实体、关系和总体 Fleiss' Kappa |
| 知识图谱 | 跨文档规范实体聚合、文档／页码／句子证据追溯、网页关系网络与全局 Gephi GEXF 导出 |
| 实体消歧 | BigModel `embedding-3`、85% 人工候选阈值、同名自动合并、人工选择规范名称、aliases 汇总 |
| 双语界面 | 中文／English 即时切换，并在浏览器本地记住语言选择 |

## 工作流程

```mermaid
flowchart LR
    A[上传 PDF] --> B[解析句子与公式]
    B --> E[人工实体标注]
    E --> F[人工关系标注]
    F --> D[可选的重复标注与 Fleiss' Kappa]
    F --> G[跨文章实体消歧]
    G --> H[全局规范知识图谱]
    H --> I[JSONL / CSV / GEXF]
```

## 技术栈

- **后端：** FastAPI、SQLAlchemy、Pydantic、PyMuPDF
- **前端：** React、TypeScript、Vite
- **Embedding：** BigModel `embedding-3`
- **存储：** MVP 阶段使用 SQLite

## 快速启动

### 1. 后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

### 2. 前端

```powershell
cd frontend
npm install
npm run dev
```

打开 [http://localhost:5173](http://localhost:5173)。API 文档位于 [http://localhost:8000/docs](http://localhost:8000/docs)。

## 模型配置

复制 `.env.example` 为 `.env`，然后填写可选的 Embedding 服务凭据：

```dotenv
BIGMODEL_API_KEY=your-key
BIGMODEL_EMBEDDING_URL=https://open.bigmodel.cn/api/paas/v4/embeddings
EMBEDDING_MODEL=embedding-3
EMBEDDING_DIMENSIONS=1024
```

未配置 API Key 时，人工标注仍可完整使用；实体消歧会回退到本地字符向量。

## 标注与实体消歧原则

- 实体边界以字符偏移量存储，分词仅作为标注辅助。
- PDF 解析、句子与公式划分只执行一次，实体和关系完全由人工标注。
- 每次保存均形成不可变版本，修订次数不限；当前知识图谱使用最新版本。
- Fleiss' Kappa 可指定参与计算的最近人工版本数，仅使用版本数足够的句子。
- 只有名称完全相同且综合相似度达到 99% 的实体才会自动合并。
- 名称不同的候选必须由人工选择规范名称；相似度达到 85% 的候选会进入人工审核。
- 合并后的 `aliases` 汇总两侧规范名称及全部历史别名。
- 人工拒绝的实体对会被记住，后续不再重复出现。
- 实体合并不删除原始 mention，全部事实均可追溯到文档、页码和句子。

## 数据隐私

仓库默认排除本地研究数据和凭据。以下内容只保留在用户电脑中，不会被 Git 提交：

- `.env` 与 API Key
- 上传的 PDF 文件
- SQLite 数据库和标注记录
- 公式截图与临时文件
- 依赖、缓存和构建产物

## 当前范围

当前仓库是面向文本型 PDF 的可运行 MVP。扫描件 OCR、多人权限、复杂版面坐标与 Neo4j 发布层作为后续扩展方向。

---

<div align="center">
让科研知识抽取过程透明、可审核、可追溯。
</div>
