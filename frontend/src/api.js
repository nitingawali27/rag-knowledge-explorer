const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed: ${res.status}`);
  }
  return data;
}

export const getConfig = () => request("/api/config");
export const getStatus = () => request("/api/status");

export const startIngest = () => request("/api/ingest/start", { method: "POST" });
export const ingestStep = (offset, batchSize) =>
  request("/api/ingest/step", {
    method: "POST",
    body: JSON.stringify({ offset, batch_size: batchSize }),
  });

export const askQuestion = (question, topK) =>
  request("/api/query", {
    method: "POST",
    body: JSON.stringify({ question, top_k: topK }),
  });
