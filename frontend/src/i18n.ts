export type Language = "zh" | "en";

export const messages = {
  zh: {
    navDocuments: "文档", navAnnotation: "句子标注", navGraph: "文章 KG", navMerge: "实体去重",
    uploadPdf: "上传 PDF", documents: "文档", papers: "篇", pages: "页", sentences: "个句子",
    workspaceTitle: "从论文到可审核的知识图谱", workspaceIntro: "模型在后台完成三轮独立抽取用于一致性评估；实体和关系由人工标注。",
    emptyDocuments: "上传一篇文本型 PDF 开始标注", runExtraction: "执行三轮抽取", startAnnotation: "开始标注", viewAnnotation: "查看标注", delete: "删除",
    parsingPdf: "正在解析 PDF…", parsedPdf: "PDF 解析完成", extractionProgress: "正在执行三轮抽取 {percent}%", deleting: "正在删除 {name}…", deleted: "已删除 {name}",
    deleteConfirm: "确定删除“{name}”吗？\n\n对应的句子、抽取结果、人工标注和图谱记录也会删除，此操作无法撤销。",
    statusParsed: "待抽取", statusQueued: "排队中", statusExtracting: "抽取中", statusReviewable: "待标注", statusApproved: "已采用", statusSkipped: "已 Pass", statusUncertain: "不确定", statusPredicted: "待审核", statusPending: "未处理",
    chooseRelation: "选择关系类型", recommendedRelations: "推荐关系", allRelations: "全部关系", customRelation: "自定义关系…", customRelationPlaceholder: "输入自定义关系名称", relationType: "关系类型",
    entityPositionInvalid: "实体“{name}”的字符位置无效，请在原文中重新划选", inactiveRelation: "存在引用已停用实体的关系，请重新选择关系两端", missingRelationType: "存在尚未选择关系类型的关系",
    saved: "已保存", saveFailed: "保存失败：{message}", saveFailedGeneric: "保存失败，请检查实体与关系", loadingSentence: "正在加载句子…",
    page: "第 {number} 页", formula: "独立公式", sentenceNumber: "句子 {number}", ontology: "本体", manualAnnotation: "人工实体标注", manualHint: "请在当前句子或公式中拖动选择文本，再选择实体类型并添加。模型结果不会预填或显示。",
    previousContext: "前文", nextContext: "后文", originalFormula: "PDF 原始公式", newEntity: "新增实体：“{text}”", entityTypePlaceholder: "选择或输入实体类型", add: "添加", cancel: "取消",
    pass: "Pass · 无需标注", passTitle: "确认本句不需要进入知识图谱", markUncertain: "标记不确定", saveNext: "保存并进入下一句", entities: "实体", relations: "关系", manual: "人工",
    noEntities: "尚未添加实体", selectTextHint: "在正文中划选文字开始标注", addRelation: "＋ 新增", needTwoEntities: "至少添加两个实体后才能建立关系", entityTypeLabel: "{name} 的实体类型",
    resolving: "正在计算实体向量并执行去重…", resolutionResult: "已自动合并 {auto} 对，生成 {manual} 对人工候选", resolutionFailed: "实体去重执行失败", mergeFailed: "实体合并失败",
    mergedAs: "已合并，规范名称为“{name}”", keptSeparate: "已保持为独立实体", deferred: "已暂缓该候选", mergeTitle: "跨文章实体去重", mergeIntro: "仅名称完全相同且相似度 ≥99% 时自动合并；名称不同则由人工选择规范名称；85% 以下不处理。", runResolution: "执行实体去重", noCandidates: "目前没有待审核的合并候选",
    canonicalEntity: "规范实体", candidateEntity: "待合并实体", similarity: "综合相似度", nameScore: "名称", contextScore: "上下文", preferredName: "合并后的规范名称", aliasesKept: "aliases 将保留", rejectMerge: "保持独立", deferMerge: "暂不确定", confirmMerge: "确认合并",
    graphEmpty: "审核并采用实体关系后，这里会显示网络图", relationNetwork: "关系网络", graphHint: "点击节点查看一阶关系", searchGraph: "搜索实体或类型", clearSelection: "清除选择", graphLimit: "网页预览显示前 {count} 个节点；GEXF 导出包含完整图谱。", graphAria: "知识图谱关系网络", evidenceNeighbors: "{evidence} 处证据 · {neighbors} 个相邻实体",
    buildingGraph: "正在构建文章知识图谱…", graphIntro: "仅汇总已经人工确认的句子；当前采用名称规范化进行文章内基础去重。", exportGephi: "导出到 Gephi", reviewProgress: "人工审核完成度", reviewed: "已审核 / {total}", passed: "已 Pass", canonicalEntities: "规范实体", evidence: "{count} 处证据", noGraphEntities: "完成句子审核后，这里会生成实体", noGraphRelations: "尚无已审核关系",
    agreementTitle: "三轮抽取一致性 · Fleiss’ Kappa", agreementIntro: "将三轮独立抽取视为 3 位标注者，在随机句子子集上比较实体/关系类别；该轮未标注的候选记为 NONE。", sampleSize: "样本句数", randomSeed: "随机种子", recalculate: "重新抽样计算", calculatingAgreement: "正在计算三轮一致性…", overall: "总体", candidateItems: "{count} 个候选项", agreementFootnote: "从 {eligible} 个具备完整三轮结果的句子中抽取 {sampled} 个 · seed={seed}", sentenceOrdinals: "句子序号：{ordinals}",
    agreementUndefined: "无法计算", agreementBelowChance: "低于随机一致", agreementSlight: "轻微一致", agreementFair: "一般一致", agreementModerate: "中等一致", agreementSubstantial: "较强一致", agreementAlmostPerfect: "高度一致",
    languageLabel: "语言",
  },
  en: {
    navDocuments: "Documents", navAnnotation: "Annotation", navGraph: "Article KG", navMerge: "Entity Resolution",
    uploadPdf: "Upload PDF", documents: "Documents", papers: "papers", pages: "pages", sentences: "sentences",
    workspaceTitle: "From papers to an auditable knowledge graph", workspaceIntro: "Three independent model runs are retained for agreement evaluation; entities and relations are annotated manually.",
    emptyDocuments: "Upload a text-based PDF to begin", runExtraction: "Run three extractions", startAnnotation: "Start annotation", viewAnnotation: "View annotation", delete: "Delete",
    parsingPdf: "Parsing PDF…", parsedPdf: "PDF parsed", extractionProgress: "Running three extractions {percent}%", deleting: "Deleting {name}…", deleted: "Deleted {name}",
    deleteConfirm: "Delete “{name}”?\n\nIts sentences, extraction runs, annotations, and graph records will also be deleted. This cannot be undone.",
    statusParsed: "Ready to extract", statusQueued: "Queued", statusExtracting: "Extracting", statusReviewable: "Ready to annotate", statusApproved: "Accepted", statusSkipped: "Passed", statusUncertain: "Uncertain", statusPredicted: "Pending review", statusPending: "Pending",
    chooseRelation: "Choose a relation type", recommendedRelations: "Recommended", allRelations: "All relations", customRelation: "Custom relation…", customRelationPlaceholder: "Enter a custom relation", relationType: "Relation type",
    entityPositionInvalid: "The character offsets for “{name}” are invalid. Select it again in the source text.", inactiveRelation: "A relation references a disabled entity. Select its endpoints again.", missingRelationType: "A relation has no selected type.",
    saved: "Saved", saveFailed: "Save failed: {message}", saveFailedGeneric: "Save failed. Check the entities and relations.", loadingSentence: "Loading sentence…",
    page: "Page {number}", formula: "Display formula", sentenceNumber: "Sentence {number}", ontology: "Ontology", manualAnnotation: "Manual entity annotation", manualHint: "Select text in the current sentence or formula, choose an entity type, and add it. Model candidates are neither prefilled nor shown.",
    previousContext: "Previous context", nextContext: "Next context", originalFormula: "Original PDF formula", newEntity: "New entity: “{text}”", entityTypePlaceholder: "Choose or enter an entity type", add: "Add", cancel: "Cancel",
    pass: "Pass · No annotation", passTitle: "Confirm that this sentence should not enter the knowledge graph", markUncertain: "Mark uncertain", saveNext: "Save and continue", entities: "Entities", relations: "Relations", manual: "Manual",
    noEntities: "No entities yet", selectTextHint: "Select text in the source to begin", addRelation: "+ Add", needTwoEntities: "Add at least two entities before creating a relation", entityTypeLabel: "Entity type for {name}",
    resolving: "Embedding entities and resolving duplicates…", resolutionResult: "Automatically merged {auto} pairs; created {manual} review candidates", resolutionFailed: "Entity resolution failed", mergeFailed: "Entity merge failed",
    mergedAs: "Merged with preferred name “{name}”", keptSeparate: "Kept as separate entities", deferred: "Candidate deferred", mergeTitle: "Cross-document entity resolution", mergeIntro: "Only exactly identical names with ≥99% similarity are merged automatically. Different names require a human choice; scores below 85% are ignored.", runResolution: "Run entity resolution", noCandidates: "No merge candidates awaiting review",
    canonicalEntity: "Canonical entity", candidateEntity: "Candidate entity", similarity: "Overall similarity", nameScore: "Name", contextScore: "Context", preferredName: "Preferred name after merge", aliasesKept: "Aliases retained", rejectMerge: "Keep separate", deferMerge: "Defer", confirmMerge: "Confirm merge",
    graphEmpty: "The network will appear after entity and relation annotations are accepted.", relationNetwork: "Relation network", graphHint: "Select a node to inspect first-degree relations", searchGraph: "Search entities or types", clearSelection: "Clear selection", graphLimit: "The web preview shows the first {count} nodes; the GEXF export contains the complete graph.", graphAria: "Knowledge graph relation network", evidenceNeighbors: "{evidence} evidence items · {neighbors} neighboring entities",
    buildingGraph: "Building article knowledge graph…", graphIntro: "Only manually reviewed sentences are included; basic within-document resolution currently uses normalized names.", exportGephi: "Export to Gephi", reviewProgress: "Manual review completion", reviewed: "Reviewed / {total}", passed: "Passed", canonicalEntities: "Canonical entities", evidence: "{count} evidence items", noGraphEntities: "Entities will appear after sentence review", noGraphRelations: "No reviewed relations yet",
    agreementTitle: "Three-run agreement · Fleiss’ Kappa", agreementIntro: "The three independent runs are treated as three annotators. Entity and relation categories are compared on a random sentence subset; an unmarked candidate is NONE.", sampleSize: "Sample size", randomSeed: "Random seed", recalculate: "Resample and calculate", calculatingAgreement: "Calculating three-run agreement…", overall: "Overall", candidateItems: "{count} candidate items", agreementFootnote: "Sampled {sampled} of {eligible} sentences with complete three-run results · seed={seed}", sentenceOrdinals: "Sentence numbers: {ordinals}",
    agreementUndefined: "Undefined", agreementBelowChance: "Below chance", agreementSlight: "Slight", agreementFair: "Fair", agreementModerate: "Moderate", agreementSubstantial: "Substantial", agreementAlmostPerfect: "Almost perfect",
    languageLabel: "Language",
  },
} as const;

export type MessageKey = keyof typeof messages.zh;

export function formatMessage(language: Language, key: MessageKey, values: Record<string, string | number> = {}) {
  let text: string = messages[language][key];
  for (const [name, value] of Object.entries(values)) text = text.split(`{${name}}`).join(String(value));
  return text;
}

export function humanizeOntologyKey(key: string) {
  return key.toLowerCase().split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}
