import { useEffect, useRef, useState } from "react";
import "./App.css";
import PipelineStepper from "./components/PipelineStepper";
import IngestPanel from "./components/IngestPanel";
import QueryPanel from "./components/QueryPanel";
import ResultsPanel from "./components/ResultsPanel";
import { askQuestion, getIngestProgress, getStatus, startIngest } from "./api";

function App() {
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [asking, setAsking] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    getStatus().then(setStatus).catch(() => {});
    getIngestProgress()
      .then((p) => {
        if (p.status === "running") {
          setProgress(p);
          pollProgress();
        } else if (p.status === "done") {
          setProgress(p);
        }
      })
      .catch(() => {});
  }, []);

  const pollProgress = () => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const p = await getIngestProgress();
        setProgress(p);
        if (p.status !== "running") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          const s = await getStatus();
          setStatus(s);
        }
      } catch {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }, 1000);
  };

  const handleIngest = async () => {
    setErrorMsg(null);
    setResult(null);
    try {
      await startIngest();
      pollProgress();
    } catch (e) {
      setErrorMsg(e.message);
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
