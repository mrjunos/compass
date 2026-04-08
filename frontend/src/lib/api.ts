const BASE = '/api';

const API_KEY = import.meta.env.VITE_COMPASS_API_KEY as string | undefined;

function headers(extra: Record<string, string> = {}): Record<string, string> {
  const h: Record<string, string> = { ...extra };
  if (API_KEY) h['X-API-Key'] = API_KEY;
  return h;
}

export async function checkHealth(): Promise<{ status: string; documents_indexed: number }> {
  const res = await fetch(`${BASE}/health`, { headers: headers() });
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export interface ChatResponse {
  answer: string;
  sources: { doc_name: string; doc_id: string }[];
  suggestion: string | null;
  session_id: string;
}

export async function sendMessage(question: string, sessionId: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: headers({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Chat request failed');
  }
  return res.json();
}

export interface Document {
  doc_id: string;
  doc_name: string;
}

export async function getDocuments(): Promise<Document[]> {
  const res = await fetch(`${BASE}/documents`, { headers: headers() });
  if (!res.ok) throw new Error('Failed to fetch documents');
  const data = await res.json();
  return data.documents;
}

export interface UploadResponse {
  filename: string;
  doc_id: string;
  message: string;
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/upload`, {
    method: 'POST',
    headers: headers(),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}
