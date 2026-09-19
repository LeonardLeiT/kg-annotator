import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import type { AgreementResult, ArticleGraph, DocumentItem, EntityCandidate, MergeCandidate, Ontology, RelationCandidate, SentenceDetail, SentenceItem } from "./types";

type Page = "documents" | "annotation" | "graph" | "merge";
type EditableEntity = EntityCandidate & { enabled: boolean };
type EditableRelation = RelationCandidate & { enabled: boolean };

function StatusBadge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    parsed: "待抽取", queued: "排队中", extracting: "抽取中", reviewable: "待标注",
    approved: "已采用", skipped: "已 Pass", uncertain: "不确定", predicted: "待审核", pending: "未处理",
  };
  return <span className={`status status-${status}`}>{labels[status] || status}</span>;
}

function DocumentsPage({ onAnnotate, onDeleted }: { onAnnotate: (doc: DocumentItem) => void; onDeleted: (id: string) => void }) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const refresh = () => api.documents().then((items) => { setDocuments(items); setMessage(""); }).catch((e) => setMessage(e.message));
  useEffect(() => { void refresh(); }, []);

  async function upload(file?: File) {
    if (!file) return;
    setBusy(true); setMessage("正在解析 PDF…");
    try { await api.upload(file); setMessage("PDF 解析完成"); await refresh(); }
    catch (e) { setMessage((e as Error).message); }
    finally { setBusy(false); }
  }

  async function extract(doc: DocumentItem) {
    setBusy(true);
    try {
      const { job_id } = await api.extract(doc.id);
      while (true) {
        const job = await api.job(job_id);
        setMessage(`${job.message} ${Math.round(job.progress * 100)}%`);
        if (job.status === "completed") break;
        if (job.status === "failed") throw new Error(job.message);
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      await refresh();
    } catch (e) { setMessage((e as Error).message); }
    finally { setBusy(false); }
  }

  async function remove(doc: DocumentItem) {
    const confirmed = window.confirm(`确定删除“${doc.filename}”吗？\n\n对应的句子、抽取结果、人工标注和图谱记录也会删除，此操作无法撤销。`);
    if (!confirmed) return;
    setBusy(true);
    setMessage(`正在删除 ${doc.filename}…`);
    try {
      await api.deleteDocument(doc.id);
      onDeleted(doc.id);
      await refresh();
      setMessage(`已删除 ${doc.filename}`);
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return <main className="page">
    <section className="hero">
      <div><p className="eyebrow">DOCUMENT WORKSPACE</p><h1>从论文到可审核的知识图谱</h1><p>整篇论文依次完成三轮独立识别，再以共识结果作为人工标注起点。</p></div>
      <label className={`upload-button ${busy ? "disabled" : ""}`}>上传 PDF<input type="file" accept="application/pdf" disabled={busy} onChange={(e) => upload(e.target.files?.[0])}/></label>
    </section>
    {message && <div className="notice">{message}</div>}
    <section className="panel">
      <div className="section-title"><h2>文档</h2><span>{documents.length} 篇</span></div>
      {documents.length === 0 ? <div className="empty">上传一篇文本型 PDF 开始标注</div> :
        <div className="document-list">{documents.map((doc) => <article className="document-row" key={doc.id}>
          <div className="doc-icon">PDF</div>
          <div className="doc-main"><strong>{doc.filename}</strong><span>{doc.page_count} 页 · {doc.sentence_count} 个句子</span></div>
          <StatusBadge status={doc.status}/>
          {doc.status === "parsed" && <button disabled={busy} onClick={() => extract(doc)}>执行三轮抽取</button>}
          {doc.status === "reviewable" && <button className="primary" onClick={() => onAnnotate(doc)}>开始标注</button>}
          {doc.status === "completed" && <button onClick={() => onAnnotate(doc)}>查看标注</button>}
          <button className="danger-button" disabled={busy || ["queued", "extracting"].includes(doc.status)} onClick={() => remove(doc)}>删除</button>
        </article>)}</div>}
    </section>
  </main>;
}

function HighlightedSentence({ text, entities, onSelection }: { text: string; entities: EditableEntity[]; onSelection: (start: number, end: number, text: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const active = entities.filter((e) => e.enabled).sort((a, b) => a.start - b.start);
  const chunks: Array<{ text: string; entity?: EditableEntity }> = [];
  let cursor = 0;
  for (const entity of active) {
    if (entity.start < cursor) continue;
    if (entity.start > cursor) chunks.push({ text: text.slice(cursor, entity.start) });
    chunks.push({ text: text.slice(entity.start, entity.end), entity });
    cursor = entity.end;
  }
  if (cursor < text.length) chunks.push({ text: text.slice(cursor) });

  function selected() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !ref.current || !selection.rangeCount) return;
    const range = selection.getRangeAt(0);
    if (!ref.current.contains(range.commonAncestorContainer)) return;
    const before = range.cloneRange();
    before.selectNodeContents(ref.current);
    before.setEnd(range.startContainer, range.startOffset);
    const start = before.toString().length;
    const selectedText = range.toString();
    onSelection(start, start + selectedText.length, selectedText);
  }

  return <div className="sentence-text" ref={ref} onMouseUp={selected}>{chunks.map((chunk, index) => chunk.entity
    ? <mark className={`entity-mark vote-${chunk.entity.vote_count}`} data-entity-type={chunk.entity.entity_type} key={index} title={`${chunk.entity.entity_type} · ${chunk.entity.vote_count}/3`}>{chunk.text}</mark>
    : <span key={index}>{chunk.text}</span>)}</div>;
}

function RelationTypePicker({ relation, entities, ontology, onChange }: {
  relation: EditableRelation;
  entities: EditableEntity[];
  ontology: Ontology | null;
  onChange: (value: string) => void;
}) {
  const entries = Object.entries(ontology?.relation_types || {});
  const known = new Set(entries.map(([key]) => key));
  const sourceType = entities.find((entity) => entity.id === relation.source_entity_id)?.entity_type;
  const targetType = entities.find((entity) => entity.id === relation.target_entity_id)?.entity_type;
  const recommended = entries.filter(([, spec]) =>
    (!spec.subject_types.length || (!!sourceType && spec.subject_types.includes(sourceType))) &&
    (!spec.object_types.length || (!!targetType && spec.object_types.includes(targetType)))
  );
  const recommendedKeys = new Set(recommended.map(([key]) => key));
  const other = entries.filter(([key]) => !recommendedKeys.has(key));
  const custom = !known.has(relation.relation_type);

  return <div className="relation-type-picker">
    <select aria-label="关系类型" value={custom ? "__CUSTOM__" : relation.relation_type} onChange={(event) => onChange(event.target.value === "__CUSTOM__" ? "" : event.target.value)}>
      <option value="" disabled>选择关系类型</option>
      {recommended.length > 0 && <optgroup label="推荐关系">{recommended.map(([key, spec]) => <option value={key} key={key}>{spec.label} · {key}</option>)}</optgroup>}
      {other.length > 0 && <optgroup label="全部关系">{other.map(([key, spec]) => <option value={key} key={key}>{spec.label} · {key}</option>)}</optgroup>}
      <option value="__CUSTOM__">自定义关系…</option>
    </select>
    {custom && <input autoFocus value={relation.relation_type} placeholder="输入自定义关系名称" onChange={(event) => onChange(event.target.value)}/>} 
  </div>;
}

function AnnotationPage({ document, ontology }: { document: DocumentItem; ontology: Ontology | null }) {
  const [sentences, setSentences] = useState<SentenceItem[]>([]);
  const [index, setIndex] = useState(0);
  const [detail, setDetail] = useState<SentenceDetail | null>(null);
  const [entities, setEntities] = useState<EditableEntity[]>([]);
  const [relations, setRelations] = useState<EditableRelation[]>([]);
  const [selected, setSelected] = useState<{ start: number; end: number; text: string } | null>(null);
  const [newType, setNewType] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => { api.sentences(document.id).then(setSentences); }, [document.id]);
  useEffect(() => {
    const item = sentences[index];
    if (!item) return;
    api.sentence(item.id).then((data) => {
      const hasHumanReview = data.status === "approved" || data.status === "uncertain";
      setDetail(data);
      setEntities(hasHumanReview ? data.entities.map((entity) => ({ ...entity, enabled: true })) : []);
      setRelations(hasHumanReview ? data.relations.map((relation) => ({ ...relation, enabled: true })) : []);
      setSelected(null);
    });
  }, [sentences, index]);

  function addSelected() {
    if (!selected || !newType) return;
    setEntities((items) => [...items, {
      id: crypto.randomUUID(), text: selected.text, entity_type: newType,
      start: selected.start, end: selected.end, vote_count: 0,
      boundary_conflict: false, type_conflict: false, enabled: true,
    }]);
    setSelected(null);
  }

  function addRelation() {
    const enabled = entities.filter((e) => e.enabled);
    const relationType = Object.keys(ontology?.relation_types || {})[0] || "RELATED_TO";
    if (enabled.length < 2 || !relationType) return;
    setRelations((items) => [...items, {
      id: crypto.randomUUID(), source_entity_id: enabled[0].id, target_entity_id: enabled[1].id,
      relation_type: relationType, vote_count: 0, enabled: true,
    }]);
  }

  async function save(status: "approved" | "uncertain" | "skipped") {
    if (!detail) return;
    const enabledEntities = entities.filter((e) => e.enabled);
    try {
      const correctedEntities = (status === "skipped" ? [] : enabledEntities).map((entity) => {
        if (detail.text.slice(entity.start, entity.end) === entity.text) return entity;
        const starts: number[] = [];
        let cursor = detail.text.indexOf(entity.text);
        while (cursor >= 0) {
          starts.push(cursor);
          cursor = detail.text.indexOf(entity.text, cursor + 1);
        }
        if (starts.length !== 1) throw new Error(`实体“${entity.text}”的字符位置无效，请在原文中重新划选`);
        return { ...entity, start: starts[0], end: starts[0] + entity.text.length };
      });
      const enabledIds = new Set(correctedEntities.map((entity) => entity.id));
      const enabledRelations = status === "skipped" ? [] : relations.filter((relation) => relation.enabled);
      if (enabledRelations.some((relation) => !enabledIds.has(relation.source_entity_id) || !enabledIds.has(relation.target_entity_id))) {
        throw new Error("存在引用已停用实体的关系，请重新选择关系两端");
      }
      if (enabledRelations.some((relation) => !relation.relation_type.trim())) {
        throw new Error("存在尚未选择关系类型的关系");
      }
      await api.annotate(detail.id, {
        status,
        entities: correctedEntities.map((e) => ({
          client_id: e.id, text: e.text, entity_type: e.entity_type, start: e.start, end: e.end,
          source: "manual", decision: "manual",
        })),
        relations: enabledRelations.map((r) => ({
          source_client_id: r.source_entity_id, target_client_id: r.target_entity_id,
          relation_type: r.relation_type, source: "manual",
        })),
      });
      setEntities(correctedEntities.map((entity) => ({ ...entity, enabled: true })));
      setMessage("已保存");
      setSentences((items) => items.map((s, i) => i === index ? { ...s, status } : s));
      if (index + 1 < sentences.length) setIndex(index + 1);
    } catch (error) {
      setMessage(error instanceof Error ? `保存失败：${error.message}` : "保存失败，请检查实体与关系");
    }
  }

  if (!detail) return <main className="page"><div className="empty">正在加载句子…</div></main>;
  const typeKeys = Object.keys(ontology?.entity_types || {});
  const enabledEntities = entities.filter((e) => e.enabled);

  return <main className="annotation-page">
    <datalist id="entity-type-options">{typeKeys.map((key) => <option value={key} key={key}>{ontology?.entity_types[key]?.label}</option>)}</datalist>
    <aside className="sentence-list">
      <div className="aside-title"><strong>{document.filename}</strong><span>{index + 1} / {sentences.length}</span></div>
      {sentences.map((sentence, i) => <button className={i === index ? "sentence-item active" : "sentence-item"} key={sentence.id} onClick={() => setIndex(i)}>
        <span>{sentence.ordinal + 1}</span><p className={sentence.content_type === "formula" ? "formula-preview" : ""}>{sentence.text}</p><StatusBadge status={sentence.status}/>
      </button>)}
    </aside>
    <section className="annotation-center">
      <div className="sentence-meta"><span>第 {detail.page_number} 页</span><span>{detail.content_type === "formula" ? "独立公式" : `句子 ${detail.ordinal + 1}`}</span><span>本体 v{ontology?.version}</span></div>
      <div className="manual-annotation-hint"><strong>人工实体标注</strong><span>请在当前句子或公式中拖动选择文本，再选择实体类型并添加。模型结果不会预填或显示。</span></div>
      <div className="context"><small>前文</small>{detail.context_before || "—"}</div>
      <div className={detail.content_type === "formula" ? "formula-unit" : ""}><HighlightedSentence text={detail.text} entities={entities} onSelection={(start, end, text) => { setSelected({ start, end, text }); setNewType(typeKeys[0] || ""); }}/></div>
      {detail.has_formula_image && <figure className="formula-source"><figcaption>PDF 原始公式</figcaption><img src={api.formulaImageUrl(detail.id)} alt="PDF 中的原始公式"/></figure>}
      <div className="context"><small>后文</small>{detail.context_after || "—"}</div>
      {selected && <div className="selection-bar"><span>新增实体：“{selected.text}”</span><input list="entity-type-options" value={newType} placeholder="选择或输入实体类型" onChange={(e) => setNewType(e.target.value)}/><button onClick={addSelected}>添加</button><button className="ghost" onClick={() => setSelected(null)}>取消</button></div>}
      <div className="annotation-actions"><button className="pass-button" onClick={() => save("skipped")} title="确认本句不需要进入知识图谱">Pass · 无需标注</button><button className="ghost" onClick={() => save("uncertain")}>标记不确定</button><span>{message}</span><button className="primary" onClick={() => save("approved")}>保存并进入下一句</button></div>
    </section>
    <aside className="candidate-panel">
      <div className="section-title"><h2>实体</h2><span>{enabledEntities.length}</span></div>
      <div className="candidate-list">{entities.length === 0 && <div className="manual-empty">尚未添加实体<br/><small>在正文中划选文字开始标注</small></div>}{entities.map((entity) => <div className={entity.enabled ? "candidate" : "candidate disabled"} key={entity.id}>
        <button className="toggle" onClick={() => setEntities((items) => items.map((x) => x.id === entity.id ? { ...x, enabled: !x.enabled } : x))}>{entity.enabled ? "✓" : "+"}</button>
        <div><strong>{entity.text}</strong><input list="entity-type-options" value={entity.entity_type} aria-label={`${entity.text} 的实体类型`} onChange={(e) => setEntities((items) => items.map((x) => x.id === entity.id ? { ...x, entity_type: e.target.value } : x))}/></div>
        <span className={`vote-badge vote-${entity.vote_count}`}>{entity.vote_count ? `${entity.vote_count}/3` : "人工"}</span>
      </div>)}</div>
      <div className="section-title relation-title"><h2>关系</h2><button className="small" disabled={enabledEntities.length < 2} title={enabledEntities.length < 2 ? "至少添加两个实体后才能建立关系" : "新增关系"} onClick={addRelation}>＋ 新增</button></div>
      <div className="relation-list">{relations.map((relation) => <div className={relation.enabled ? "relation-card" : "relation-card disabled"} key={relation.id}>
        <div className="relation-line"><select value={relation.source_entity_id} onChange={(e) => setRelations((items) => items.map((x) => x.id === relation.id ? { ...x, source_entity_id: e.target.value } : x))}>{enabledEntities.map((entity) => <option value={entity.id} key={entity.id}>{entity.text}</option>)}</select><span>→</span><select value={relation.target_entity_id} onChange={(e) => setRelations((items) => items.map((x) => x.id === relation.id ? { ...x, target_entity_id: e.target.value } : x))}>{enabledEntities.map((entity) => <option value={entity.id} key={entity.id}>{entity.text}</option>)}</select></div>
        <div className="relation-line"><RelationTypePicker relation={relation} entities={enabledEntities} ontology={ontology} onChange={(value) => setRelations((items) => items.map((x) => x.id === relation.id ? { ...x, relation_type: value } : x))}/><span className={`vote-badge vote-${relation.vote_count}`}>{relation.vote_count ? `${relation.vote_count}/3` : "人工"}</span><button className="icon-button" onClick={() => setRelations((items) => items.map((x) => x.id === relation.id ? { ...x, enabled: !x.enabled } : x))}>×</button></div>
      </div>)}</div>
    </aside>
  </main>;
}

function MergePage() {
  const [items, setItems] = useState<MergeCandidate[]>([]);
  const [preferredNames, setPreferredNames] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const refresh = () => api.mergeCandidates().then((nextItems) => {
    setItems(nextItems);
    setPreferredNames((current) => Object.fromEntries(nextItems.map((item) => [item.id, current[item.id] || item.left.name])));
  });
  useEffect(() => { void refresh(); }, []);
  async function generate() {
    setMessage("正在计算实体向量并执行去重…");
    try {
      const data = await api.generateMerges();
      setMessage(`已自动合并 ${data.auto_merged} 对，生成 ${data.candidates} 对人工候选`);
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "实体去重执行失败");
    }
  }
  async function decide(id: string, decision: string) {
    try {
      await api.decideMerge(id, decision, decision === "merge" ? preferredNames[id] : undefined);
      setMessage(decision === "merge" ? `已合并，规范名称为“${preferredNames[id]}”` : decision === "reject" ? "已保持为独立实体" : "已暂缓该候选");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "实体合并失败");
    }
  }
  return <main className="page"><section className="hero compact"><div><p className="eyebrow">ENTITY RESOLUTION</p><h1>跨文章实体去重</h1><p>仅名称完全相同且相似度 ≥99% 时自动合并；名称不同则由人工选择规范名称；85% 以下不处理。</p></div><button className="primary" onClick={generate}>执行实体去重</button></section>{message && <div className="notice">{message}</div>}
    <section className="merge-list">{items.length === 0 ? <div className="empty panel">目前没有待审核的合并候选</div> : items.map((item) => <article className="merge-card" key={item.id}>
      <div className="entity-compare"><div><span>规范实体</span><h2>{item.left.name}</h2><p>{item.left.type}</p><small>{item.left.aliases.join(" · ")}</small></div><div className="similarity"><strong>{Math.round(item.total_score * 100)}%</strong><span>综合相似度</span></div><div><span>待合并实体</span><h2>{item.right.name}</h2><p>{item.right.type}</p><small>{item.right.aliases.join(" · ")}</small></div></div>
      <div className="score-row"><span>名称 {item.name_score.toFixed(2)}</span><span>上下文 {item.context_score.toFixed(2)}</span><span>{item.reason}</span></div>
      <div className="merge-name-choice"><label>合并后的规范名称<select value={preferredNames[item.id] || item.left.name} onChange={(event) => setPreferredNames((current) => ({ ...current, [item.id]: event.target.value }))}><option value={item.left.name}>{item.left.name}</option>{item.right.name !== item.left.name && <option value={item.right.name}>{item.right.name}</option>}</select></label><div><span>aliases 将保留</span><strong>{[...new Set([...item.left.aliases, ...item.right.aliases, item.left.name, item.right.name])].join(" · ")}</strong></div></div>
      <div className="merge-actions"><button className="ghost" onClick={() => decide(item.id, "reject")}>保持独立</button><button className="ghost" onClick={() => decide(item.id, "defer")}>暂不确定</button><button className="primary" onClick={() => decide(item.id, "merge")}>确认合并</button></div>
    </article>)}</section>
  </main>;
}

const GRAPH_WIDTH = 960;
const GRAPH_HEIGHT = 520;
const GRAPH_NODE_LIMIT = 160;
const GRAPH_COLORS = ["#237a57", "#c67b2d", "#486f9b", "#9a5264", "#6f5a99", "#71843d", "#a25237", "#477b78"];

function typeColor(entityType: string) {
  let hash = 0;
  for (const character of entityType) hash = ((hash << 5) - hash + character.charCodeAt(0)) | 0;
  return GRAPH_COLORS[Math.abs(hash) % GRAPH_COLORS.length];
}

function graphLayout(graph: ArticleGraph) {
  const selectedNodes = graph.nodes.slice(0, GRAPH_NODE_LIMIT);
  const nodeIds = new Set(selectedNodes.map((node) => node.id));
  const edges = graph.edges.filter((edge) => nodeIds.has(edge.source_id) && nodeIds.has(edge.target_id));
  const positions = selectedNodes.map((node, index) => {
    const angle = (index / Math.max(selectedNodes.length, 1)) * Math.PI * 2;
    const radius = 130 + (index % 4) * 42;
    return { id: node.id, x: GRAPH_WIDTH / 2 + Math.cos(angle) * radius, y: GRAPH_HEIGHT / 2 + Math.sin(angle) * radius };
  });
  const indexById = new Map(positions.map((position, index) => [position.id, index]));
  for (let iteration = 0; iteration < 90; iteration += 1) {
    const forces = positions.map(() => ({ x: 0, y: 0 }));
    for (let left = 0; left < positions.length; left += 1) {
      for (let right = left + 1; right < positions.length; right += 1) {
        const dx = positions[left].x - positions[right].x || 0.01;
        const dy = positions[left].y - positions[right].y || 0.01;
        const distanceSquared = Math.max(dx * dx + dy * dy, 100);
        const force = 1050 / distanceSquared;
        const distance = Math.sqrt(distanceSquared);
        forces[left].x += (dx / distance) * force;
        forces[left].y += (dy / distance) * force;
        forces[right].x -= (dx / distance) * force;
        forces[right].y -= (dy / distance) * force;
      }
    }
    for (const edge of edges) {
      const sourceIndex = indexById.get(edge.source_id);
      const targetIndex = indexById.get(edge.target_id);
      if (sourceIndex === undefined || targetIndex === undefined) continue;
      const dx = positions[targetIndex].x - positions[sourceIndex].x;
      const dy = positions[targetIndex].y - positions[sourceIndex].y;
      const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
      const force = (distance - 105) * 0.0028;
      forces[sourceIndex].x += (dx / distance) * force;
      forces[sourceIndex].y += (dy / distance) * force;
      forces[targetIndex].x -= (dx / distance) * force;
      forces[targetIndex].y -= (dy / distance) * force;
    }
    positions.forEach((position, index) => {
      forces[index].x += (GRAPH_WIDTH / 2 - position.x) * 0.0008;
      forces[index].y += (GRAPH_HEIGHT / 2 - position.y) * 0.0008;
      position.x = Math.min(GRAPH_WIDTH - 32, Math.max(32, position.x + forces[index].x * 0.72));
      position.y = Math.min(GRAPH_HEIGHT - 32, Math.max(32, position.y + forces[index].y * 0.72));
    });
  }
  return { nodes: selectedNodes, edges, positions: Object.fromEntries(positions.map((position) => [position.id, position])) };
}

function KnowledgeGraphView({ graph }: { graph: ArticleGraph }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const layout = useMemo(() => graphLayout(graph), [graph]);
  const nodeById = Object.fromEntries(layout.nodes.map((node) => [node.id, node]));
  const selectedNode = selectedId ? nodeById[selectedId] : undefined;
  const neighborIds = new Set<string>();
  if (selectedId) {
    neighborIds.add(selectedId);
    layout.edges.forEach((edge) => {
      if (edge.source_id === selectedId) neighborIds.add(edge.target_id);
      if (edge.target_id === selectedId) neighborIds.add(edge.source_id);
    });
  }
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const types = [...new Set(layout.nodes.map((node) => node.entity_type))].sort();
  const visible = (id: string) => {
    const node = nodeById[id];
    const matchesQuery = !normalizedQuery || node.name.toLocaleLowerCase().includes(normalizedQuery) || node.entity_type.toLocaleLowerCase().includes(normalizedQuery);
    const matchesSelection = !selectedId || neighborIds.has(id);
    return matchesQuery && matchesSelection;
  };

  if (graph.nodes.length === 0) return <section className="panel graph-visual-panel"><div className="empty">审核并采用实体关系后，这里会显示网络图</div></section>;
  return <section className="panel graph-visual-panel">
    <div className="graph-toolbar"><div><h2>关系网络</h2><span>点击节点查看一阶关系</span></div><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索实体或类型"/>{selectedId && <button className="small" onClick={() => setSelectedId(null)}>清除选择</button>}</div>
    {graph.nodes.length > GRAPH_NODE_LIMIT && <div className="graph-limit">网页预览显示前 {GRAPH_NODE_LIMIT} 个节点；GEXF 导出包含完整图谱。</div>}
    <div className="graph-canvas-wrap">
      <svg className="graph-canvas" viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`} role="img" aria-label="知识图谱关系网络">
        <defs><marker id="graph-arrow" markerWidth="7" markerHeight="7" refX="13" refY="3.5" orient="auto"><path d="M0,0 L0,7 L7,3.5 z" fill="#a8b0aa"/></marker></defs>
        <g className="graph-links">{layout.edges.map((edge, index) => {
          const source = layout.positions[edge.source_id]; const target = layout.positions[edge.target_id];
          const active = visible(edge.source_id) && visible(edge.target_id);
          return <g key={`${edge.source_id}-${edge.relation_type}-${edge.target_id}-${index}`} className={active ? "graph-link active" : "graph-link"}>
            <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} markerEnd="url(#graph-arrow)"/>
            {active && (selectedId || layout.nodes.length <= 28) && <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 4}>{edge.relation_type}</text>}
          </g>;
        })}</g>
        <g className="graph-nodes">{layout.nodes.map((node) => {
          const position = layout.positions[node.id]; const active = visible(node.id); const selected = selectedId === node.id;
          return <g key={node.id} className={`graph-node ${active ? "active" : "muted"} ${selected ? "selected" : ""}`} transform={`translate(${position.x} ${position.y})`} onClick={() => setSelectedId(selected ? null : node.id)}>
            <circle r={Math.min(15, 7 + Math.log2(node.mention_count + 1) * 2)} fill={typeColor(node.entity_type)}/>
            {(active && (selectedId || layout.nodes.length <= 45 || normalizedQuery)) && <text y="-13">{node.name.length > 24 ? `${node.name.slice(0, 22)}…` : node.name}</text>}
          </g>;
        })}</g>
      </svg>
      {selectedNode && <aside className="graph-inspector"><span style={{ background: typeColor(selectedNode.entity_type) }}>{selectedNode.entity_type}</span><h3>{selectedNode.name}</h3><p>{selectedNode.aliases.join(" · ")}</p><small>{selectedNode.mention_count} 处证据 · {neighborIds.size - 1} 个相邻实体</small></aside>}
    </div>
    <div className="graph-legend">{types.map((type) => <span key={type}><i style={{ background: typeColor(type) }}/>{type}</span>)}</div>
  </section>;
}

function GraphPage({ document }: { document: DocumentItem }) {
  const [graph, setGraph] = useState<ArticleGraph | null>(null);
  const [agreement, setAgreement] = useState<AgreementResult | null>(null);
  const [sampleSize, setSampleSize] = useState(50);
  const [seed, setSeed] = useState(42);
  const [error, setError] = useState("");
  useEffect(() => {
    api.articleGraph(document.id).then(setGraph).catch((e) => setError(e.message));
    api.agreement(document.id, 50, 42).then(setAgreement).catch((e) => setError(e.message));
  }, [document.id]);
  async function calculateAgreement() {
    try {
      setAgreement(await api.agreement(document.id, sampleSize, seed));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (error) return <main className="page"><div className="notice">{error}</div></main>;
  if (!graph) return <main className="page"><div className="empty">正在构建文章知识图谱…</div></main>;
  const nodeById = Object.fromEntries(graph.nodes.map((node) => [node.id, node]));
  const completion = graph.stats.sentences ? Math.round(graph.stats.reviewed / graph.stats.sentences * 100) : 0;
  return <main className="page">
    <section className="hero compact"><div><p className="eyebrow">ARTICLE KNOWLEDGE GRAPH</p><h1>{document.filename}</h1><p>仅汇总已经人工确认的句子；当前采用名称规范化进行文章内基础去重。</p></div><div className="graph-hero-actions"><a className="gephi-button" href={api.exportUrl(document.id, "gexf")}>导出到 Gephi</a><div className="graph-progress"><strong>{completion}%</strong><span>人工审核完成度</span></div></div></section>
    <section className="graph-stats"><div><strong>{graph.stats.reviewed}</strong><span>已审核 / {graph.stats.sentences}</span></div><div><strong>{graph.stats.skipped}</strong><span>已 Pass</span></div><div><strong>{graph.stats.nodes}</strong><span>规范实体</span></div><div><strong>{graph.stats.edges}</strong><span>关系</span></div></section>
    <section className="panel agreement-panel">
      <div className="agreement-header"><div><h2>三轮抽取一致性 · Fleiss’ Kappa</h2><p>将三轮独立抽取视为 3 位标注者，在随机句子子集上比较实体/关系类别；该轮未标注的候选记为 NONE。</p></div><div className="agreement-controls"><label>样本句数<input type="number" min="1" max="1000" value={sampleSize} onChange={(event) => setSampleSize(Math.max(1, Number(event.target.value)))}/></label><label>随机种子<input type="number" min="0" value={seed} onChange={(event) => setSeed(Math.max(0, Number(event.target.value)))}/></label><button onClick={calculateAgreement}>重新抽样计算</button></div></div>
      {!agreement ? <div className="empty">正在计算三轮一致性…</div> : <><div className="agreement-metrics">{([['实体', agreement.entity], ['关系', agreement.relation], ['总体', agreement.overall]] as const).map(([label, metric]) => <div key={label}><span>{label}</span><strong>{metric.kappa === null ? "—" : metric.kappa.toFixed(3)}</strong><small>{metric.interpretation} · {metric.items} 个候选项</small></div>)}</div><div className="agreement-footnote">从 {agreement.eligible_sentences} 个具备完整三轮结果的句子中抽取 {agreement.sampled_sentences} 个 · seed={agreement.seed}{agreement.sampled_sentences > 0 && ` · 句子序号：${agreement.sampled_ordinals.join(", ")}`}</div></>}
    </section>
    <KnowledgeGraphView graph={graph}/>
    <section className="graph-grid">
      <div className="panel graph-panel"><div className="section-title"><h2>实体</h2><span>{graph.nodes.length}</span></div>{graph.nodes.length === 0 ? <div className="empty">完成句子审核后，这里会生成实体</div> : <div className="graph-rows">{graph.nodes.map((node) => <div className="graph-row" key={node.id}><span className="node-type">{node.entity_type}</span><div><strong>{node.name}</strong><small>{node.aliases.join(" · ")}</small></div><span>{node.mention_count} 处证据</span></div>)}</div>}</div>
      <div className="panel graph-panel"><div className="section-title"><h2>关系</h2><span>{graph.edges.length}</span></div>{graph.edges.length === 0 ? <div className="empty">尚无已审核关系</div> : <div className="graph-rows">{graph.edges.map((edge, index) => <div className="edge-row" key={`${edge.source_id}-${edge.relation_type}-${edge.target_id}-${index}`}><strong>{nodeById[edge.source_id]?.name || edge.source_id}</strong><span>{edge.relation_type}</span><strong>{nodeById[edge.target_id]?.name || edge.target_id}</strong><small>{edge.evidence_count} 处证据</small></div>)}</div>}</div>
    </section>
  </main>;
}

export default function App() {
  const [page, setPage] = useState<Page>("documents");
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [ontology, setOntology] = useState<Ontology | null>(null);
  useEffect(() => { api.ontology().then(setOntology); }, []);
  return <div className="app-shell">
    <header><button className="brand" onClick={() => setPage("documents")}><span>KG</span><strong>Annotator</strong></button><nav><button className={page === "documents" ? "active" : ""} onClick={() => setPage("documents")}>文档</button><button disabled={!document} className={page === "annotation" ? "active" : ""} onClick={() => setPage("annotation")}>句子标注</button><button disabled={!document} className={page === "graph" ? "active" : ""} onClick={() => setPage("graph")}>文章 KG</button><button className={page === "merge" ? "active" : ""} onClick={() => setPage("merge")}>实体去重</button></nav>{document && <div className="export-links"><a href={api.exportUrl(document.id, "jsonl")}>JSONL</a><a href={api.exportUrl(document.id, "csv")}>CSV</a><a href={api.exportUrl(document.id, "gexf")}>GEXF</a></div>}</header>
    {page === "documents" && <DocumentsPage onAnnotate={(doc) => { setDocument(doc); setPage("annotation"); }} onDeleted={(id) => setDocument((current) => current?.id === id ? null : current)}/>} 
    {page === "annotation" && document && <AnnotationPage document={document} ontology={ontology}/>} 
    {page === "graph" && document && <GraphPage document={document}/>} 
    {page === "merge" && <MergePage/>}
  </div>;
}
