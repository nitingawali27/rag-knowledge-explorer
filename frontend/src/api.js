const BASE_URL = "http://localhost:8000";

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
export const startIngest = () => request("/api/ingest", { method: "POST" });
export const getIngestProgress = () => request("/api/ingest/progress");
export const askQuestion = (question, topK) =>
  request("/api/query", {
    method: "POST",
    body: JSON.stringify({ question, top_k: topK }),
  });
