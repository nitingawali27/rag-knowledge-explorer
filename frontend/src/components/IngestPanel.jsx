export default function IngestPanel({ progress, onIngest, disabled }) {
  const running = progress?.status === "running";
  const done = progress?.status === "done";
  const error = progress?.status === "error";
  const pct =
    progress && progress.total_chunks > 0
      ? Math.round((progress.chunks_embedded / progress.total_chunks) * 100)
      : 0;

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>1 &middot; 2 &middot; 3 &middot; 4 — Ingest, Chunk, Embed &amp; Store</h2>
        <button onClick={onIngest} disabled={disabled || running}>
          {running ? "Ingesting…" : done ? "Re-run Ingestion" : "Run Ingestion"}
        </button>
      </div>

      {!progress && (
        <p className="muted">
          Click "Run Ingestion" to read every PDF in <code>data/data</code>, split it into
          chunks, embed each chunk with Nomic Embed, and store the vectors in ChromaDB.
        </p>
      )}

      {progress && (
        <>
          {(running || done) && (
            <div className="progress-bar-track">
              <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
              <span className="progress-bar-text">
                {progress.chunks_embedded} / {progress.total_chunks} chunks embedded ({pct}%)
              </span>
            </div>
          )}

          {error && <div className="error-box">Ingestion failed: {progress.error}</div>}

          {progress.current_document && (
            <p className="muted">Currently embedding: {progress.current_document}</p>
          )}

          {progress.documents.length > 0 && (
            <table className="doc-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Pages</th>
                  <th>Chunks</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {progress.documents.map((d) => (
                  <tr key={d.filename}>
                    <td>{d.filename}</td>
                    <td>{d.pages}</td>
                    <td>{d.chunks}</td>
                    <td>
                      <span className={`badge badge-${d.status}`}>{d.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {progress.embedding_dimension > 0 && (
            <p className="muted">
              Embedding dimension: <strong>{progress.embedding_dimension}</strong>{" "}
              (nomic-embed-text)
            </p>
          )}

          {progress.sample_chunks.length > 0 && (
            <div className="sample-chunks">
              <h3>Sample chunks</h3>
              {progress.sample_chunks.map((c) => (
                <div className="chunk-card" key={c.id}>
                  <div className="chunk-meta">
                    {c.source} · page {c.page_number} · chunk #{c.chunk_index} ·{" "}
                    {c.word_count} words
                  </div>
                  <div className="chunk-text">{c.preview}…</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
