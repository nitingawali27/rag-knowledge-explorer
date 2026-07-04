const STEPS = [
  { key: "ingest", label: "PDF Ingestion" },
  { key: "chunk", label: "Chunking" },
  { key: "embed", label: "Embedding" },
  { key: "store", label: "Vector Storage" },
  { key: "retrieve", label: "Retrieval" },
  { key: "generate", label: "Answer Generation" },
];

export default function PipelineStepper({ activeStep, completedSteps }) {
  return (
    <div className="stepper">
      {STEPS.map((step, i) => {
        const isActive = step.key === activeStep;
        const isDone = completedSteps.has(step.key) && !isActive;
        const state = isActive ? "active" : isDone ? "done" : "pending";
        return (
          <div className="stepper-item" key={step.key}>
            <div className={`stepper-dot ${state}`}>{isDone ? "✓" : i + 1}</div>
            <div className={`stepper-label ${state}`}>{step.label}</div>
            {i < STEPS.length - 1 && <div className={`stepper-line ${isDone ? "done" : ""}`} />}
          </div>
        );
      })}
    </div>
  );
}
