import { useState } from "react";

const SAMPLE_QUESTIONS = [
  "What payment methods does the Checkout & Payment module support?",
  "How does the platform calculate taxes at checkout for India and UAE?",
  "What is the return policy window for electronics?",
  "What SLA applies to refund turnaround time?",
  "How does the platform prevent overselling during flash sales?",
  "What happens when a warehouse can't fulfill an entire order?",
  "What multi-factor authentication is required for high-risk logins?",
  "What business rule governs SKU uniqueness in the product catalog?",
  "How long before an abandoned cart triggers a reminder notification?",
  "What qualifies a review for the Verified Purchase badge?",
  "What admin roles are supported for role-based access control?",
  "Which channels does the Notification Service use for order updates?",
];

export default function QueryPanel({ onAsk, loading, disabled }) {
  const [question, setQuestion] = useState("");

  const submit = (e) => {
    e.preventDefault();
    if (question.trim()) onAsk(question.trim());
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>5 &middot; 6 — Retrieve &amp; Generate</h2>
      </div>

      {disabled && (
        <p className="muted">Run ingestion first to enable the query interface.</p>
      )}

      <form className="query-form" onSubmit={submit}>
        <input
          type="text"
          placeholder="Ask a question about the ingested BRDs…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || loading || !question.trim()}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      <div className="sample-questions">
        {SAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            className="chip"
            disabled={disabled}
            onClick={() => setQuestion(q)}
          >
            {q}
          </button>
        ))}
      </div>
    </section>
  );
}
