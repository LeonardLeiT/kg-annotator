import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import type { AgreementResult, ArticleGraph, DocumentItem, EntityCandidate, MergeCandidate, Ontology, RelationCandidate, SentenceDetail, SentenceItem } from "./types";
import { formatMessage, humanizeOntologyKey, type Language, type MessageKey } from "./i18n";

type Page = "documents" | "annotation" | "graph" | "merge";
type ContextRole = "previous" | "current" | "next";
type EditableEntity = EntityCandidate & { enabled: boolean };
type EditableRelation = RelationCandidate & { enabled: boolean };

const I18nContext = createContext<{ language: Language; t: (key: MessageKey, values?: Record<string, string | number>) => string }>({
  language: "zh",
  t: (key, values) => formatMessage("zh", key, values),
});

function useI18n() { return useContext(I18nContext); }

function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n();
  const labels: Record<string, string> = {
    parsed: t("statusParsed"), queued: t("statusQueued"), extracting: t("statusExtracting"), reviewable: t("statusReviewable"),
    annotating: t("statusAnnotating"), completed: t("statusCompleted"), approved: t("statusApproved"), skipped: t("statusSkipped"), uncertain: t("statusUncertain"), predicted: t("statusPredicted"), pending: t("statusPending"),
  };
  return <span className={`status status-${status}`}>{labels[status] || status}</span>;
}

function DocumentsPage({ onAnnotate, onDeleted }: { onAnnotate: (doc: DocumentItem) => void; onDeleted: (id: string) => void }) {
  const { t } = useI18n();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const refresh = () => api.documents().then((items) => { setDocuments(items); setMessage(""); }).catch((e) => setMessage(e.message));
  useEffect(() => { void refresh(); }, []);

  async function upload(file?: File) {
    if (!file) return;
    setBusy(true); setMessage(t("parsingPdf"));
    try { await api.upload(file); setMessage(t("parsedPdf")); await refresh(); }
    catch (e) { setMessage((e as Error).message); }
    finally { setBusy(false); }
  }

  async function remove(doc: DocumentItem) {
    const confirmed = window.confirm(t("deleteConfirm", { name: doc.filename }));
    if (!confirmed) return;
    setBusy(true);
    setMessage(t("deleting", { name: doc.filename }));
    try {
      await api.deleteDocument(doc.id);
      onDeleted(doc.id);
      await refresh();
      setMessage(t("deleted", { name: doc.filename }));
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return <main className="page">
    <section className="hero">
      <div><p className="eyebrow">DOCUMENT WORKSPACE</p><h1>{t("workspaceTitle")}</h1><p>{t("workspaceIntro")}</p></div>
      <label className={`upload-button ${busy ? "disabled" : ""}`}>{t("uploadPdf")}<input type="file" accept="application/pdf" disabled={busy} onChange={(e) => upload(e.target.files?.[0])}/></label>
    </section>
    {message && <div className="notice">{message}</div>}
    <section className="panel">
      <div className="section-title"><h2>{t("documents")}</h2><span>{documents.length} {t("papers")}</span></div>
      {documents.length === 0 ? <div className="empty">{t("emptyDocuments")}</div> :
        <div className="document-list">{documents.map((doc) => <article className="document-row" key={doc.id}>
          <div className="doc-icon">PDF</div>
          <div className="doc-main"><strong>{doc.filename}</strong><span>{doc.page_count} {t("pages")} · {doc.sentence_count} {t("sentences")}</span>{doc.reviewed_count > 0 && <span>{t("documentProgress", { reviewed: doc.reviewed_count, total: doc.sentence_count })} · {t("highestVersion", { count: doc.max_revision })}</span>}</div>
          <StatusBadge status={doc.reviewed_count > 0 && doc.status === "reviewable" ? "annotating" : doc.status}/>
          {["parsed", "reviewable"].includes(doc.status) && <button className="primary" onClick={() => onAnnotate(doc)}>{doc.reviewed_count > 0 ? t("continueAnnotation") : t("startAnnotation")}</button>}
          {doc.status === "completed" && <button onClick={() => onAnnotate(doc)}>{t("continueAnnotation")}</button>}
          <button className="danger-button" disabled={busy || ["queued", "extracting"].includes(doc.status)} onClick={() => remove(doc)}>{t("delete")}</button>
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
  const { language, t } = useI18n();
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
    <select aria-label={t("relationType")} value={custom ? "__CUSTOM__" : relation.relation_type} onChange={(event) => onChange(event.target.value === "__CUSTOM__" ? "" : event.target.value)}>
      <option value="" disabled>{t("chooseRelation")}</option>
      {recommended.length > 0 && <optgroup label={t("recommendedRelations")}>{recommended.map(([key, spec]) => <option value={key} key={key}>{language === "zh" ? spec.label : humanizeOntologyKey(key)} · {key}</option>)}</optgroup>}
      {other.length > 0 && <optgroup label={t("allRelations")}>{other.map(([key, spec]) => <option value={key} key={key}>{language === "zh" ? spec.label : humanizeOntologyKey(key)} · {key}</option>)}</optgroup>}
      <option value="__CUSTOM__">{t("customRelation")}</option>
    </select>
    {custom && <input autoFocus value={relation.relation_type} placeholder={t("customRelationPlaceholder")} onChange={(event) => onChange(event.target.value)}/>}
  </div>;
}

function AnnotationPage({ document, ontology }: { document: DocumentItem; ontology: Ontology | null }) {
  const { language, t } = useI18n();
  const [sentences, setSentences] = useState<SentenceItem[]>([]);
  const [index, setIndex] = useState(0);
  const [detail, setDetail] = useState<SentenceDetail | null>(null);
  const [entities, setEntities] = useState<EditableEntity[]>([]);
  const [relations, setRelations] = useState<EditableRelation[]>([]);
  const [selected, setSelected] = useState<{ start: number; end: number; text: string; context_role: ContextRole } | null>(null);
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
      start: selected.start, end: selected.end, context_role: selected.context_role, vote_count: 0,
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
        const sourceText = entity.context_role === "previous" ? (detail.context_before || "") : entity.context_role === "next" ? (detail.context_after || "") : detail.text;
        if (sourceText.slice(entity.start, entity.end) === entity.text) return entity;
        const starts: number[] = [];
        let cursor = sourceText.indexOf(entity.text);
        while (cursor >= 0) {
          starts.push(cursor);
          cursor = sourceText.indexOf(entity.text, cursor + 1);
        }
        if (starts.length !== 1) throw new Error(t("entityPositionInvalid", { name: entity.text }));
        return { ...entity, start: starts[0], end: starts[0] + entity.text.length };
      });
      const enabledIds = new Set(correctedEntities.map((entity) => entity.id));
      const enabledRelations = status === "skipped" ? [] : relations.filter((relation) => relation.enabled);
      if (enabledRelations.some((relation) => !enabledIds.has(relation.source_entity_id) || !enabledIds.has(relation.target_entity_id))) {
        throw new Error(t("inactiveRelation"));
      }
      if (enabledRelations.some((relation) => !relation.relation_type.trim())) {
        throw new Error(t("missingRelationType"));
      }
      const result = await api.annotate(detail.id, {
        status,
        entities: correctedEntities.map((e) => ({
          client_id: e.id, text: e.text, entity_type: e.entity_type, start: e.start, end: e.end,
          context_role: e.context_role, source: "manual", decision: "manual",
        })),
        relations: enabledRelations.map((r) => ({
          source_client_id: r.source_entity_id, target_client_id: r.target_entity_id,
          relation_type: r.relation_type, source: "manual",
        })),
      });
      setEntities(correctedEntities.map((entity) => ({ ...entity, enabled: true })));
      setDetail((item) => item ? { ...item, status, revision_count: result.revision } : item);
      setMessage(t("savedRevision", { count: result.revision }));
      setSentences((items) => items.map((s, i) => i === index ? { ...s, status } : s));
      if (index + 1 < sentences.length) setIndex(index + 1);
    } catch (error) {
      setMessage(error instanceof Error ? t("saveFailed", { message: error.message }) : t("saveFailedGeneric"));
    }
  }

  if (!detail) return <main className="page"><div className="empty">{t("loadingSentence")}</div></main>;
  const typeKeys = Object.keys(ontology?.entity_types || {});
  const enabledEntities = entities.filter((e) => e.enabled);

  return <main className="annotation-page">
    <datalist id="entity-type-options">{typeKeys.map((key) => <option value={key} key={key}>{language === "zh" ? ontology?.entity_types[key]?.label : humanizeOntologyKey(key)}</option>)}</datalist>
    <aside className="sentence-list">
      <div className="aside-title"><strong>{document.filename}</strong><span>{index + 1} / {sentences.length}</span></div>
      {sentences.map((sentence, i) => <button className={i === index ? "sentence-item active" : "sentence-item"} key={sentence.id} onClick={() => setIndex(i)}>
        <span>{sentence.ordinal + 1}</span><p className={sentence.content_type === "formula" ? "formula-preview" : ""}>{sentence.text}</p><StatusBadge status={sentence.status}/>
      </button>)}
    </aside>
    <section className="annotation-center">
      <div className="sentence-meta"><span>{t("page", { number: detail.page_number })}</span><span>{detail.content_type === "formula" ? t("formula") : t("sentenceNumber", { number: detail.ordinal + 1 })}</span><span>{t("revisionCount", { count: detail.revision_count })}</span><span>{t("ontology")} v{ontology?.version}</span></div>
      <div className="manual-annotation-hint"><strong>{t("manualAnnotation")}</strong><span>{t("manualHint")}</span></div>
      <div className="context selectable-context"><small>{t("previousContext")}</small>{detail.context_before ? <HighlightedSentence text={detail.context_before} entities={entities.filter((entity) => entity.context_role === "previous")} onSelection={(start, end, text) => { setSelected({ start, end, text, context_role: "previous" }); setNewType(typeKeys[0] || ""); }}/> : "—"}</div>
      <div className={detail.content_type === "formula" ? "formula-unit" : ""}><HighlightedSentence text={detail.text} entities={entities.filter((entity) => entity.context_role === "current")} onSelection={(start, end, text) => { setSelected({ start, end, text, context_role: "current" }); setNewType(typeKeys[0] || ""); }}/></div>
      {detail.has_formula_image && <figure className="formula-source"><figcaption>{t("originalFormula")}</figcaption><img src={api.formulaImageUrl(detail.id)} alt={t("originalFormula")}/></figure>}
      <div className="context selectable-context"><small>{t("nextContext")}</small>{detail.context_after ? <HighlightedSentence text={detail.context_after} entities={entities.filter((entity) => entity.context_role === "next")} onSelection={(start, end, text) => { setSelected({ start, end, text, context_role: "next" }); setNewType(typeKeys[0] || ""); }}/> : "—"}</div>
      {selected && <div className="selection-bar"><span>{t("newContextEntity", { scope: t(selected.context_role === "previous" ? "previousContext" : selected.context_role === "next" ? "nextContext" : "currentSentence"), text: selected.text })}</span><input list="entity-type-options" value={newType} placeholder={t("entityTypePlaceholder")} onChange={(e) => setNewType(e.target.value)}/><button onClick={addSelected}>{t("add")}</button><button className="ghost" onClick={() => setSelected(null)}>{t("cancel")}</button></div>}
      <div className="annotation-actions"><button className="pass-button" onClick={() => save("skipped")} title={t("passTitle")}>{t("pass")}</button><button className="ghost" onClick={() => save("uncertain")}>{t("markUncertain")}</button><span>{message}</span><button className="primary" onClick={() => save("approved")}>{t("saveNext")}</button></div>
    </section>
    <aside className="candidate-panel">
      <div className="section-title"><h2>{t("entities")}</h2><span>{enabledEntities.length}</span></div>
      <div className="candidate-list">{entities.length === 0 && <div className="manual-empty">{t("noEntities")}<br/><small>{t("selectTextHint")}</small></div>}{entities.map((entity) => <div className={entity.enabled ? "candidate" : "candidate disabled"} key={entity.id}>
        <button className="toggle" onClick={() => setEntities((items) => items.map((x) => x.id === entity.id ? { ...x, enabled: !x.enabled } : x))}>{entity.enabled ? "✓" : "+"}</button>
        <div><strong>{entity.text}</strong><small>{t(entity.context_role === "previous" ? "previousContext" : entity.context_role === "next" ? "nextContext" : "currentSentence")}</small><input list="entity-type-options" value={entity.entity_type} aria-label={t("entityTypeLabel", { name: entity.text })} onChange={(e) => setEntities((items) => items.map((x) => x.id === entity.id ? { ...x, entity_type: e.target.value } : x))}/></div>
        <span className={`vote-badge vote-${entity.vote_count}`}>{entity.vote_count ? `${entity.vote_count}/3` : t("manual")}</span>
      </div>)}</div>
      <div className="section-title relation-title"><h2>{t("relations")}</h2><button className="small" disabled={enabledEntities.length < 2} title={enabledEntities.length < 2 ? t("needTwoEntities") : t("addRelation")} onClick={addRelation}>{t("addRelation")}</button></div>
      <div className="relation-list">{relations.map((relation) => <div className="relation-card" key={relation.id}>
        <div className="relation-line"><select value={relation.source_entity_id} onChange={(e) => setRelations((items) => items.map((x) => x.id === relation.id ? { ...x, source_entity_id: e.target.value } : x))}>{enabledEntities.map((entity) => <option value={entity.id} key={entity.id}>{entity.text}</option>)}</select><span>→</span><select value={relation.target_entity_id} onChange={(e) => setRelations((items) => items.map((x) => x.id === relation.id ? { ...x, target_entity_id: e.target.value } : x))}>{enabledEntities.map((entity) => <option value={entity.id} key={entity.id}>{entity.text}</option>)}</select></div>
        <div className="relation-line"><RelationTypePicker relation={relation} entities={enabledEntities} ontology={ontology} onChange={(value) => setRelations((items) => items.map((x) => x.id === relation.id ? { ...x, relation_type: value } : x))}/><span className={`vote-badge vote-${relation.vote_count}`}>{relation.vote_count ? `${relation.vote_count}/3` : t("manual")}</span><button className="icon-button" aria-label={t("deleteRelation")} title={t("deleteRelation")} onClick={() => setRelations((items) => items.filter((x) => x.id !== relation.id))}>×</button></div>
      </div>)}</div>
    </aside>
  </main>;
}

function MergePage() {
  const { t } = useI18n();
  const [items, setItems] = useState<MergeCandidate[]>([]);
  const [preferredNames, setPreferredNames] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const refresh = () => api.mergeCandidates().then((nextItems) => {
    setItems(nextItems);
    setPreferredNames((current) => Object.fromEntries(nextItems.map((item) => [item.id, current[item.id] || item.left.name])));
  });
  useEffect(() => { void refresh(); }, []);
  async function generate() {
    setMessage(t("resolving"));
    try {
      const data = await api.generateMerges();
      setMessage(t("resolutionResult", { auto: data.auto_merged, manual: data.candidates }));
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("resolutionFailed"));
    }
  }
  async function decide(id: string, decision: string) {
    try {
      await api.decideMerge(id, decision, decision === "merge" ? preferredNames[id] : undefined);
      setMessage(decision === "merge" ? t("mergedAs", { name: preferredNames[id] }) : decision === "reject" ? t("keptSeparate") : t("deferred"));
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t("mergeFailed"));
    }
  }
  return <main className="page"><section className="hero compact"><div><p className="eyebrow">ENTITY RESOLUTION</p><h1>{t("mergeTitle")}</h1><p>{t("mergeIntro")}</p></div><button className="primary" onClick={generate}>{t("runResolution")}</button></section>{message && <div className="notice">{message}</div>}
    <section className="merge-list">{items.length === 0 ? <div className="empty panel">{t("noCandidates")}</div> : items.map((item) => <article className="merge-card" key={item.id}>
      <div className="entity-compare"><div><span>{t("canonicalEntity")}</span><h2>{item.left.name}</h2><p>{item.left.type}</p><small>{item.left.aliases.join(" · ")}</small></div><div className="similarity"><strong>{Math.round(item.total_score * 100)}%</strong><span>{t("similarity")}</span></div><div><span>{t("candidateEntity")}</span><h2>{item.right.name}</h2><p>{item.right.type}</p><small>{item.right.aliases.join(" · ")}</small></div></div>
      <div className="score-row"><span>{t("nameScore")} {item.name_score.toFixed(2)}</span><span>{t("contextScore")} {item.context_score.toFixed(2)}</span></div>
      <div className="merge-name-choice"><label>{t("preferredName")}<select value={preferredNames[item.id] || item.left.name} onChange={(event) => setPreferredNames((current) => ({ ...current, [item.id]: event.target.value }))}><option value={item.left.name}>{item.left.name}</option>{item.right.name !== item.left.name && <option value={item.right.name}>{item.right.name}</option>}</select></label><div><span>{t("aliasesKept")}</span><strong>{[...new Set([...item.left.aliases, ...item.right.aliases, item.left.name, item.right.name])].join(" · ")}</strong></div></div>
      <div className="merge-actions"><button className="ghost" onClick={() => decide(item.id, "reject")}>{t("rejectMerge")}</button><button className="ghost" onClick={() => decide(item.id, "defer")}>{t("deferMerge")}</button><button className="primary" onClick={() => decide(item.id, "merge")}>{t("confirmMerge")}</button></div>
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
  const { t } = useI18n();
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

  if (graph.nodes.length === 0) return <section className="panel graph-visual-panel"><div className="empty">{t("graphEmpty")}</div></section>;
  return <section className="panel graph-visual-panel">
    <div className="graph-toolbar"><div><h2>{t("relationNetwork")}</h2><span>{t("graphHint")}</span></div><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("searchGraph")}/>{selectedId && <button className="small" onClick={() => setSelectedId(null)}>{t("clearSelection")}</button>}</div>
    {graph.nodes.length > GRAPH_NODE_LIMIT && <div className="graph-limit">{t("graphLimit", { count: GRAPH_NODE_LIMIT })}</div>}
    <div className="graph-canvas-wrap">
      <svg className="graph-canvas" viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`} role="img" aria-label={t("graphAria")}>
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
      {selectedNode && <aside className="graph-inspector"><span style={{ background: typeColor(selectedNode.entity_type) }}>{selectedNode.entity_type}</span><h3>{selectedNode.name}</h3><p>{selectedNode.aliases.join(" · ")}</p><small>{t("evidenceNeighbors", { evidence: selectedNode.mention_count, neighbors: neighborIds.size - 1 })}</small></aside>}
    </div>
    <div className="graph-legend">{types.map((type) => <span key={type}><i style={{ background: typeColor(type) }}/>{type}</span>)}</div>
  </section>;
}

function GraphPage({ document }: { document: DocumentItem | null }) {
  const { language, t } = useI18n();
  const [graph, setGraph] = useState<ArticleGraph | null>(null);
  const [agreement, setAgreement] = useState<AgreementResult | null>(null);
  const [sampleSize, setSampleSize] = useState(50);
  const [seed, setSeed] = useState(42);
  const [annotators, setAnnotators] = useState(2);
  const [error, setError] = useState("");
  useEffect(() => {
    api.globalGraph().then(setGraph).catch((e) => setError(e.message));
    if (document) api.agreement(document.id, 50, 42, 2).then(setAgreement).catch((e) => setError(e.message));
  }, [document?.id]);
  async function calculateAgreement() {
    if (!document) return;
    try {
      setAgreement(await api.agreement(document.id, sampleSize, seed, annotators));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (error) return <main className="page"><div className="notice">{error}</div></main>;
  if (!graph) return <main className="page"><div className="empty">{t("buildingGraph")}</div></main>;
  const nodeById = Object.fromEntries(graph.nodes.map((node) => [node.id, node]));
  const completion = graph.stats.sentences ? Math.round(graph.stats.reviewed / graph.stats.sentences * 100) : 0;
  return <main className="page">
    <section className="hero compact"><div><p className="eyebrow">CROSS-DOCUMENT KNOWLEDGE GRAPH</p><h1>{t("globalGraphTitle")}</h1><p>{t("graphIntro")}</p></div><div className="graph-hero-actions"><a className="gephi-button" href={api.globalGraphExportUrl()}>{t("exportGephi")}</a><div className="graph-progress"><strong>{completion}%</strong><span>{t("reviewProgress")}</span></div></div></section>
    <section className="graph-stats"><div><strong>{graph.stats.documents || 0}</strong><span>{t("sourceDocuments")}</span></div><div><strong>{graph.stats.reviewed}</strong><span>{t("reviewed", { total: graph.stats.sentences })}</span></div><div><strong>{graph.stats.nodes}</strong><span>{t("canonicalEntities")}</span></div><div><strong>{graph.stats.edges}</strong><span>{t("relations")}</span></div></section>
    {document && <section className="panel agreement-panel">
      <div className="agreement-header"><div><h2>{t("agreementTitle")}</h2><p>{t("agreementIntro")}</p></div><div className="agreement-controls"><label>{t("annotationRounds")}<input type="number" min="2" max="100" value={annotators} onChange={(event) => setAnnotators(Math.max(2, Number(event.target.value)))}/></label><label>{t("sampleSize")}<input type="number" min="1" max="1000" value={sampleSize} onChange={(event) => setSampleSize(Math.max(1, Number(event.target.value)))}/></label><label>{t("randomSeed")}<input type="number" min="0" value={seed} onChange={(event) => setSeed(Math.max(0, Number(event.target.value)))}/></label><button onClick={calculateAgreement}>{t("recalculate")}</button></div></div>
      {!agreement ? <div className="empty">{t("calculatingAgreement")}</div> : <><div className="agreement-metrics">{([[t("entities"), agreement.entity], [t("relations"), agreement.relation], [t("overall"), agreement.overall]] as const).map(([label, metric]) => {
        const interpretation = language === "zh" ? metric.interpretation : ({ "无法计算": t("agreementUndefined"), "低于随机一致": t("agreementBelowChance"), "轻微一致": t("agreementSlight"), "一般一致": t("agreementFair"), "中等一致": t("agreementModerate"), "较强一致": t("agreementSubstantial"), "高度一致": t("agreementAlmostPerfect") }[metric.interpretation] || metric.interpretation);
        return <div key={label}><span>{label}</span><strong>{metric.kappa === null ? "—" : metric.kappa.toFixed(3)}</strong><small>{interpretation} · {t("candidateItems", { count: metric.items })}</small></div>;
      })}</div><div className="agreement-footnote">{t("agreementFootnote", { rounds: agreement.annotators, eligible: agreement.eligible_sentences, sampled: agreement.sampled_sentences, seed: agreement.seed })}{agreement.sampled_sentences > 0 && ` · ${t("sentenceOrdinals", { ordinals: agreement.sampled_ordinals.join(", ") })}`}</div></>}
    </section>}
    <KnowledgeGraphView graph={graph}/>
    <section className="graph-grid">
      <div className="panel graph-panel"><div className="section-title"><h2>{t("entities")}</h2><span>{graph.nodes.length}</span></div>{graph.nodes.length === 0 ? <div className="empty">{t("noGraphEntities")}</div> : <div className="graph-rows">{graph.nodes.map((node) => <div className="graph-row" key={node.id}><span className="node-type">{node.entity_type}</span><div><strong>{node.name}</strong><small>{node.aliases.join(" · ")}</small></div><span>{t("globalEvidence", { mentions: node.mention_count, documents: node.document_count || 1 })}</span></div>)}</div>}</div>
      <div className="panel graph-panel"><div className="section-title"><h2>{t("relations")}</h2><span>{graph.edges.length}</span></div>{graph.edges.length === 0 ? <div className="empty">{t("noGraphRelations")}</div> : <div className="graph-rows">{graph.edges.map((edge, index) => <div className="edge-row" key={`${edge.source_id}-${edge.relation_type}-${edge.target_id}-${index}`}><strong>{nodeById[edge.source_id]?.name || edge.source_id}</strong><span>{edge.relation_type}</span><strong>{nodeById[edge.target_id]?.name || edge.target_id}</strong><small>{t("evidence", { count: edge.evidence_count })}</small></div>)}</div>}</div>
    </section>
  </main>;
}

export default function App() {
  const [page, setPage] = useState<Page>("documents");
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [ontology, setOntology] = useState<Ontology | null>(null);
  const [language, setLanguage] = useState<Language>(() => localStorage.getItem("kg-annotator-language") === "en" ? "en" : "zh");
  const t = (key: MessageKey, values?: Record<string, string | number>) => formatMessage(language, key, values);
  useEffect(() => { api.ontology().then(setOntology); }, []);
  useEffect(() => { localStorage.setItem("kg-annotator-language", language); globalThis.document.documentElement.lang = language === "zh" ? "zh-CN" : "en"; }, [language]);
  return <I18nContext.Provider value={{ language, t }}><div className="app-shell">
    <header><button className="brand" onClick={() => setPage("documents")}><span>KG</span><strong>Annotator</strong></button><nav><button className={page === "documents" ? "active" : ""} onClick={() => setPage("documents")}>{t("navDocuments")}</button><button disabled={!document} className={page === "annotation" ? "active" : ""} onClick={() => setPage("annotation")}>{t("navAnnotation")}</button><button className={page === "graph" ? "active" : ""} onClick={() => setPage("graph")}>{t("navGraph")}</button><button className={page === "merge" ? "active" : ""} onClick={() => setPage("merge")}>{t("navMerge")}</button></nav><div className="header-actions">{document && <div className="export-links"><a href={api.exportUrl(document.id, "jsonl")}>JSONL</a><a href={api.exportUrl(document.id, "csv")}>CSV</a><a href={api.exportUrl(document.id, "gexf")}>GEXF</a></div>}<div className="language-toggle" aria-label={t("languageLabel")}><button className={language === "zh" ? "active" : ""} onClick={() => setLanguage("zh")}>中文</button><button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>EN</button></div></div></header>
    {page === "documents" && <DocumentsPage onAnnotate={(doc) => { setDocument(doc); setPage("annotation"); }} onDeleted={(id) => setDocument((current) => current?.id === id ? null : current)}/>} 
    {page === "annotation" && document && <AnnotationPage document={document} ontology={ontology}/>} 
    {page === "graph" && <GraphPage document={document}/>}
    {page === "merge" && <MergePage/>}
  </div></I18nContext.Provider>;
}
