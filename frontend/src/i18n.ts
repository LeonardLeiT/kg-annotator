export type Language = "zh" | "en";

export const messages = {
  zh: {
    navDocuments: "文档", navAnnotation: "句子标注", navGraph: "跨文档 KG", navMerge: "实体去重",
    uploadPdf: "上传 PDF", documents: "文档", papers: "篇", pages: "页", sentences: "个句子",
    workspaceTitle: "从论文到可审核的知识图谱", workspaceIntro: "PDF 只解析和分句一次；实体与关系完全由人工标注，首轮完成即可使用，并可不限次数继续修订。",
    emptyDocuments: "上传一篇文本型 PDF 开始标注", runExtraction: "执行抽取", startAnnotation: "开始标注", viewAnnotation: "查看标注", continueAnnotation: "继续标注", delete: "删除",
    parsingPdf: "正在解析 PDF 并划分句子…", parsedPdf: "PDF 解析与分句完成", extractionProgress: "正在处理 {percent}%", deleting: "正在删除 {name}…", deleted: "已删除 {name}",
    deleteConfirm: "确定删除“{name}”吗？\n\n对应的句子、人工标注版本和图谱记录也会删除，此操作无法撤销。",
    statusParsed: "待标注", statusQueued: "排队中", statusExtracting: "处理中", statusReviewable: "待标注", statusAnnotating: "标注中", statusCompleted: "首轮已完成", statusApproved: "已采用", statusSkipped: "已 Pass", statusUncertain: "不确定", statusPredicted: "待审核", statusPending: "未处理", documentProgress: "已处理 {reviewed}/{total}", highestVersion: "最高版本 {count}",
    chooseRelation: "选择关系类型", recommendedRelations: "推荐关系", allRelations: "全部关系", customRelation: "自定义关系…", customRelationPlaceholder: "输入自定义关系名称", relationType: "关系类型",
    entityPositionInvalid: "实体“{name}”的字符位置无效，请在原文中重新划选", inactiveRelation: "存在引用已停用实体的关系，请重新选择关系两端", missingRelationType: "存在尚未选择关系类型的关系",
    saved: "已保存", savedRevision: "已保存第 {count} 个标注版本", saveFailed: "保存失败：{message}", saveFailedGeneric: "保存失败，请检查实体与关系", loadingSentence: "正在加载句子…",
    page: "第 {number} 页", formula: "独立公式", sentenceNumber: "句子 {number}", revisionCount: "已保存 {count} 次", ontology: "本体", manualAnnotation: "人工实体标注", manualHint: "可在前文、本句、后文中划选实体，并跨句建立关系。每次保存都会形成新版本，KG 使用最新版本。",
    previousContext: "前文", currentSentence: "本句", nextContext: "后文", originalFormula: "PDF 原始公式", newEntity: "新增实体：“{text}”", newContextEntity: "从{scope}新增实体：“{text}”", entityTypePlaceholder: "选择或输入实体类型", add: "添加", cancel: "取消",
    pass: "Pass · 无需标注", passTitle: "确认本句不需要进入知识图谱", markUncertain: "标记不确定", saveNext: "保存并进入下一句", entities: "实体", relations: "关系", deleteRelation: "删除关系", manual: "人工",
    noEntities: "尚未添加实体", selectTextHint: "在正文中划选文字开始标注", addRelation: "＋ 新增", needTwoEntities: "至少添加两个实体后才能建立关系", entityTypeLabel: "{name} 的实体类型",
    resolving: "正在计算实体向量并执行去重…", resolutionResult: "已自动合并 {auto} 对，生成 {manual} 对人工候选", resolutionFailed: "实体去重执行失败", mergeFailed: "实体合并失败",
    mergedAs: "已合并，规范名称为“{name}”", keptSeparate: "已保持为独立实体", deferred: "已暂缓该候选", mergeTitle: "跨文章实体去重", mergeIntro: "仅名称完全相同且相似度 ≥99% 时自动合并；名称不同则由人工选择规范名称；85% 以下不处理。", runResolution: "执行实体去重", noCandidates: "目前没有待审核的合并候选",
    canonicalEntity: "规范实体", candidateEntity: "待合并实体", similarity: "综合相似度", nameScore: "名称", contextScore: "上下文", preferredName: "合并后的规范名称", aliasesKept: "aliases 将保留", rejectMerge: "保持独立", deferMerge: "暂不确定", confirmMerge: "确认合并",
    graphEmpty: "审核并采用实体关系后，这里会显示网络图", relationNetwork: "关系网络", graphHint: "点击节点查看一阶关系", searchGraph: "搜索实体或类型", clearSelection: "清除选择", graphLimit: "网页预览显示前 {count} 个节点；GEXF 导出包含完整图谱。", graphAria: "知识图谱关系网络", evidenceNeighbors: "{evidence} 处证据 · {neighbors} 个相邻实体",
    buildingGraph: "正在构建跨文档知识图谱…", globalGraphTitle: "跨文档知识图谱", graphIntro: "汇总所有文章中已人工确认的实体和关系，并按去重后的规范实体形成统一网络。", exportGephi: "导出全局 GEXF", reviewProgress: "全部文档审核完成度", sourceDocuments: "来源文档", reviewed: "已审核 / {total}", passed: "已 Pass", canonicalEntities: "规范实体", evidence: "{count} 处证据", globalEvidence: "{mentions} 处证据 · {documents} 篇文档", noGraphEntities: "完成句子审核后，这里会生成实体", noGraphRelations: "尚无已审核关系",
    agreementTitle: "人工标注一致性 · Fleiss’ Kappa", agreementIntro: "比较同一句子的多次人工标注版本；未标注的候选记为 NONE。至少需要 2 次标注，可按需要增加次数。", annotationRounds: "参与版本数", sampleSize: "样本句数", randomSeed: "随机种子", recalculate: "重新抽样计算", calculatingAgreement: "正在计算人工标注一致性…", overall: "总体", candidateItems: "{count} 个候选项", agreementFootnote: "使用最近 {rounds} 个版本，从 {eligible} 个满足次数的句子中抽取 {sampled} 个 · seed={seed}", sentenceOrdinals: "句子序号：{ordinals}",
    agreementUndefined: "无法计算", agreementBelowChance: "低于随机一致", agreementSlight: "轻微一致", agreementFair: "一般一致", agreementModerate: "中等一致", agreementSubstantial: "较强一致", agreementAlmostPerfect: "高度一致",
    languageLabel: "语言",
  },
  en: {
    navDocuments: "Documents", navAnnotation: "Annotation", navGraph: "Global KG", navMerge: "Entity Resolution",
    uploadPdf: "Upload PDF", documents: "Documents", papers: "papers", pages: "pages", sentences: "sentences",
    workspaceTitle: "From papers to an auditable knowledge graph", workspaceIntro: "Each PDF is parsed and segmented once. Entities and relations are fully manual; the first pass is immediately usable and revisions are unlimited.",
    emptyDocuments: "Upload a text-based PDF to begin", runExtraction: "Run extraction", startAnnotation: "Start annotation", viewAnnotation: "View annotation", continueAnnotation: "Continue annotation", delete: "Delete",
    parsingPdf: "Parsing and segmenting PDF…", parsedPdf: "PDF parsed and segmented", extractionProgress: "Processing {percent}%", deleting: "Deleting {name}…", deleted: "Deleted {name}",
    deleteConfirm: "Delete “{name}”?\n\nIts sentences, manual annotation versions, and graph records will also be deleted. This cannot be undone.",
    statusParsed: "Ready to annotate", statusQueued: "Queued", statusExtracting: "Processing", statusReviewable: "Ready to annotate", statusAnnotating: "In progress", statusCompleted: "First pass complete", statusApproved: "Accepted", statusSkipped: "Passed", statusUncertain: "Uncertain", statusPredicted: "Pending review", statusPending: "Pending", documentProgress: "Reviewed {reviewed}/{total}", highestVersion: "Highest version {count}",
    chooseRelation: "Choose a relation type", recommendedRelations: "Recommended", allRelations: "All relations", customRelation: "Custom relation…", customRelationPlaceholder: "Enter a custom relation", relationType: "Relation type",
    entityPositionInvalid: "The character offsets for “{name}” are invalid. Select it again in the source text.", inactiveRelation: "A relation references a disabled entity. Select its endpoints again.", missingRelationType: "A relation has no selected type.",
    saved: "Saved", savedRevision: "Saved annotation version {count}", saveFailed: "Save failed: {message}", saveFailedGeneric: "Save failed. Check the entities and relations.", loadingSentence: "Loading sentence…",
    page: "Page {number}", formula: "Display formula", sentenceNumber: "Sentence {number}", revisionCount: "{count} saved versions", ontology: "Ontology", manualAnnotation: "Manual entity annotation", manualHint: "Select entities in the previous sentence, current sentence, or next sentence, and create cross-sentence relations. Every save creates a new version; the KG uses the latest version.",
    previousContext: "Previous context", currentSentence: "Current sentence", nextContext: "Next context", originalFormula: "Original PDF formula", newEntity: "New entity: “{text}”", newContextEntity: "New entity from {scope}: “{text}”", entityTypePlaceholder: "Choose or enter an entity type", add: "Add", cancel: "Cancel",
    pass: "Pass · No annotation", passTitle: "Confirm that this sentence should not enter the knowledge graph", markUncertain: "Mark uncertain", saveNext: "Save and continue", entities: "Entities", relations: "Relations", deleteRelation: "Delete relation", manual: "Manual",
    noEntities: "No entities yet", selectTextHint: "Select text in the source to begin", addRelation: "+ Add", needTwoEntities: "Add at least two entities before creating a relation", entityTypeLabel: "Entity type for {name}",
    resolving: "Embedding entities and resolving duplicates…", resolutionResult: "Automatically merged {auto} pairs; created {manual} review candidates", resolutionFailed: "Entity resolution failed", mergeFailed: "Entity merge failed",
    mergedAs: "Merged with preferred name “{name}”", keptSeparate: "Kept as separate entities", deferred: "Candidate deferred", mergeTitle: "Cross-document entity resolution", mergeIntro: "Only exactly identical names with ≥99% similarity are merged automatically. Different names require a human choice; scores below 85% are ignored.", runResolution: "Run entity resolution", noCandidates: "No merge candidates awaiting review",
    canonicalEntity: "Canonical entity", candidateEntity: "Candidate entity", similarity: "Overall similarity", nameScore: "Name", contextScore: "Context", preferredName: "Preferred name after merge", aliasesKept: "Aliases retained", rejectMerge: "Keep separate", deferMerge: "Defer", confirmMerge: "Confirm merge",
    graphEmpty: "The network will appear after entity and relation annotations are accepted.", relationNetwork: "Relation network", graphHint: "Select a node to inspect first-degree relations", searchGraph: "Search entities or types", clearSelection: "Clear selection", graphLimit: "The web preview shows the first {count} nodes; the GEXF export contains the complete graph.", graphAria: "Knowledge graph relation network", evidenceNeighbors: "{evidence} evidence items · {neighbors} neighboring entities",
    buildingGraph: "Building the cross-document knowledge graph…", globalGraphTitle: "Cross-document knowledge graph", graphIntro: "Combines manually approved entities and relations from every paper into one network using resolved canonical entity IDs.", exportGephi: "Export global GEXF", reviewProgress: "All-document review completion", sourceDocuments: "Source documents", reviewed: "Reviewed / {total}", passed: "Passed", canonicalEntities: "Canonical entities", evidence: "{count} evidence items", globalEvidence: "{mentions} evidence items · {documents} documents", noGraphEntities: "Entities will appear after sentence review", noGraphRelations: "No reviewed relations yet",
    agreementTitle: "Manual annotation agreement · Fleiss’ Kappa", agreementIntro: "Compares multiple manual versions of the same sentence; an unmarked candidate is NONE. At least two versions are required, with no upper annotation limit.", annotationRounds: "Versions used", sampleSize: "Sample size", randomSeed: "Random seed", recalculate: "Resample and calculate", calculatingAgreement: "Calculating manual annotation agreement…", overall: "Overall", candidateItems: "{count} candidate items", agreementFootnote: "Using the latest {rounds} versions; sampled {sampled} of {eligible} eligible sentences · seed={seed}", sentenceOrdinals: "Sentence numbers: {ordinals}",
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
