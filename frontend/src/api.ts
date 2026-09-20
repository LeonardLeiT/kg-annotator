import type { AgreementResult, ArticleGraph, DocumentItem, MergeCandidate, Ontology, SentenceDetail, SentenceItem, SentenceSuggestion } from "./types";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail || "Request failed / 请求失败");
  }
  return response.json();
}

export const api = {
  documents: () => request<DocumentItem[]>("/documents"),
  deleteDocument: (id: string) => request<{ deleted: boolean }>(`/documents/${id}`, { method: "DELETE" }),
  ontology: () => request<Ontology>("/ontology"),
  upload: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<DocumentItem>("/documents", { method: "POST", body });
  },
  sentences: (id: string) => request<SentenceItem[]>(`/documents/${id}/sentences`),
  sentence: (id: string) => request<SentenceDetail>(`/sentences/${id}`),
  suggestions: (id: string) => request<SentenceSuggestion>(`/sentences/${id}/suggestions`, { method: "POST" }),
  formulaImageUrl: (id: string) => `${BASE}/sentences/${id}/formula-image`,
  cleanMarkdownUrl: (id: string) => `${BASE}/documents/${id}/clean-markdown`,
  articleGraph: (id: string) => request<ArticleGraph>(`/documents/${id}/graph`),
  globalGraph: () => request<ArticleGraph>("/graph/global"),
  globalGraphExportUrl: () => `${BASE}/export/global/gexf`,
  agreement: (id: string, sampleSize = 50, seed = 42, annotators = 2) => request<AgreementResult>(`/documents/${id}/agreement?sample_size=${sampleSize}&seed=${seed}&annotators=${annotators}`),
  annotate: (id: string, data: unknown) => request<{ status: string; revision: number }>(`/sentences/${id}/annotation`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  }),
  generateMerges: () => request<{ auto_merged: number; candidates: number; pairs_scored: number }>("/entity-resolution/generate", { method: "POST" }),
  mergeCandidates: () => request<MergeCandidate[]>("/entity-resolution/candidates"),
  decideMerge: (id: string, decision: string, preferredName?: string) => request(`/entity-resolution/candidates/${id}/${decision}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferredName ? { preferred_name: preferredName } : {}),
  }),
  exportUrl: (documentId: string, format: "jsonl" | "csv" | "gexf") => `${BASE}/documents/${documentId}/export/${format}`,
};
