import { useEffect, useState } from "react";
import "./App.css";
import PipelineStepper from "./components/PipelineStepper";
import IngestPanel from "./components/IngestPanel";
import QueryPanel from "./components/QueryPanel";
import ResultsPanel from "./components/ResultsPanel";
import { askQuestion, getStatus, ingestStep, startIngest } from "./api";

const STEP_BATCH_SIZE = 20;

function withDocumentStatuses(documents, chunksEmbedded) {
  let cumulative = 0;
  let currentDocument = null;
  const documentsWithStatus = documents.map((d) => {
    const start = cumulative;
    cumulative += d.chunks;
    let status = "pending";
    if (chunksEmbedded >= cumulative) status = "done";
    else if (chunksEmbedded >= start) status = "embedding";
    if (status === "embedding") currentDocument = d.filename;
    return { ...d, status };
  });
  return { documentsWithStatus, currentDocument };
}

function App() {
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [asking, setAsking] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    getStatus().then(setStatus).catch(() => {});
  }, []);

  // Ingestion is driven entirely from the browser: each call to /api/ingest/step
  // is an independent, stateless serverless invocation, so the client owns the
  // progress loop instead of polling a server-side background job.
  const handleIngest = async () => {
    setErrorMsg(null);
    setResult(null);

    try {
      const { documents, total_chunks } = await startIngest();
      const { documentsWithStatus, currentDocument } = withDocumentStatuses(documents, 0);
      setProgress({
        status: "running",
        documents: documentsWithStatus,
        total_chunks,
        chunks_embedded: 0,
        current_document: currentDocument,
        sample_chunks: [],
        embedding_dimension: 0,
      });

      let offset = 0;
      while (offset < total_chunks) {
        const step = await ingestStep(offset, STEP_BATCH_SIZE);
        offset = step.next_offset;

        setProgress((prev) => {
          const { documentsWithStatus: docs, currentDocument: current } =
            withDocumentStatuses(documents, offset);
          return {
            ...prev,
            documents: docs,
            chunks_embedded: offset,
            current_document: current,
            embedding_dimension: step.embedding_dimension || prev.embedding_dimension,
            sample_chunks:
              prev.sample_chunks.length < 6
                ? [...prev.sample_chunks, ...step.sample_chunks].slice(0, 6)
                : prev.sample_chunks,
          };
        });

        if (step.done) break;
      }

      setProgress((prev) => ({ ...prev, status: "done", current_document: null }));
      const s = await getStatus();
      setStatus(s);
    } catch (e) {
      setErrorMsg(e.message);
      setProgress((prev) => (prev ? { ...prev, status: "error", error: e.message } : prev));
    }
  };

  const handleAsk = async (question) => {
    setAsking(true);
    setErrorMsg(null);
    setResult(null);
    try {
      const r = await askQuestion(question);
      setResult(r);
    } catch (e) {
      setErrorMsg(e.message);
    } finally {
      setAsking(false);
    }
  };

  const ready = status?.ready_to_query || progress?.status === "done";

  const completedSteps = new Set();
  let activeStep = "ingest";

  if (ready) {
    completedSteps.add("ingest");
    completedSteps.add("chunk");
    completedSteps.add("embed");
    completedSteps.add("store");
    activeStep = "retrieve";
  }
  if (progress?.status === "running") {
    activeStep = progress.chunks_embedded > 0 ? "embed" : "chunk";
    completedSteps.add("ingest");
    if (progress.chunks_embedded > 0) completedSteps.add("chunk");
  }
  if (asking) {
    activeStep = result ? "generate" : "retrieve";
  }
  if (result) {
    completedSteps.add("retrieve");
    completedSteps.add("generate");
    activeStep = "generate";
  }

  return (
    <div className="app">
      <header>
        <h1>RAG Explorer</h1>
        <p className="subtitle">
          A visual walkthrough of Retrieval-Augmented Generation: PDF ingestion → chunking →
          Nomic embeddings → ChromaDB storage → retrieval → Groq answer generation.
        </p>
      </header>

      <PipelineStepper activeStep={activeStep} completedSteps={completedSteps} />

      {errorMsg && <div className="error-box">{errorMsg}</div>}

      <IngestPanel progress={progress} onIngest={handleIngest} disabled={false} />
      <QueryPanel onAsk={handleAsk} loading={asking} disabled={!ready} />
      <ResultsPanel result={result} />
    </div>
  );
}

export default App;
