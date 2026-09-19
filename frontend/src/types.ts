export type DocumentItem = {
  id: string;
  filename: string;
  status: string;
  page_count: number;
  sentence_count: number;
};

export type SentenceItem = {
  id: string;
  ordinal: number;
  page_number: number;
  text: string;
  status: string;
  content_type: "sentence" | "formula";
};

export type EntityCandidate = {
  id: string;
  text: string;
  entity_type: string;
  start: number;
  end: number;
  vote_count: number;
  boundary_conflict: boolean;
  type_conflict: boolean;
  variants?: unknown[];
};

export type RelationCandidate = {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  relation_type: string;
  vote_count: number;
};

export type SentenceDetail = SentenceItem & {
  document_id: string;
  context_before?: string;
  context_after?: string;
  has_formula_image: boolean;
  entities: EntityCandidate[];
  relations: RelationCandidate[];
  runs: Array<{ run_index: number; model: string; output: unknown }>;
};

export type Ontology = {
  version: string;
  entity_types: Record<string, { label: string; description: string }>;
  relation_types: Record<string, { label: string; subject_types: string[]; object_types: string[] }>;
};

export type MergeCandidate = {
  id: string;
  status: string;
  name_score: number;
  context_score: number;
  total_score: number;
  reason: string;
  left: { id: string; name: string; type: string; aliases: string[] };
  right: { id: string; name: string; type: string; aliases: string[] };
};

export type ArticleGraph = {
  stats: { sentences: number; reviewed: number; approved: number; skipped: number; nodes: number; edges: number };
  nodes: Array<{
    id: string;
    name: string;
    entity_type: string;
    aliases: string[];
    mention_count: number;
    evidence: Array<{ sentence_id: string; page: number; text: string }>;
  }>;
  edges: Array<{
    source_id: string;
    relation_type: string;
    target_id: string;
    evidence_count: number;
    evidence: Array<{ sentence_id: string; page: number; text: string }>;
  }>;
};

export type AgreementMetric = {
  kappa: number | null;
  items: number;
  observed_agreement: number | null;
  expected_agreement: number | null;
  interpretation: string;
};

export type AgreementResult = {
  method: string;
  annotators: number;
  unit: string;
  seed: number;
  requested_sample_size: number;
  eligible_sentences: number;
  sampled_sentences: number;
  sampled_ordinals: number[];
  entity: AgreementMetric;
  relation: AgreementMetric;
  overall: AgreementMetric;
};
