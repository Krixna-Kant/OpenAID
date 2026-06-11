"use client";

import { useMemo, useState } from "react";

type StepStatus =
  | "pending"
  | "running"
  | "waiting_approval"
  | "completed"
  | "failed"
  | "skipped";

type AgentStep = {
  id: string;
  label: string;
  status: StepStatus;
  detail?: string | null;
  tool?: string | null;
};

type ApprovalRequest = {
  session_id: string;
  step_id: string;
  title: string;
  summary: string;
  plan: Record<string, unknown>;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DEFAULT_PROMPT =
  "We need the latest medical supply data for flooded regions in Kenya, but our dashboard is empty.";

export default function HomePage() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [approval, setApproval] = useState<ApprovalRequest | null>(null);
  const [briefing, setBriefing] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const running = useMemo(
    () => steps.some((s) => s.status === "running" || s.status === "waiting_approval"),
    [steps]
  );

  async function startMission() {
    setLoading(true);
    setError(null);
    setSteps([]);
    setApproval(null);
    setBriefing(null);

    try {
      const res = await fetch(`${API_URL}/api/missions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSessionId(data.session_id);
      listen(data.session_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start mission");
      setLoading(false);
    }
  }

  function listen(session: string) {
    const source = new EventSource(`${API_URL}/api/missions/${session}/stream`);

    source.addEventListener("step", (event) => {
      const step = JSON.parse(event.data) as AgentStep;
      setSteps((prev) => {
        const idx = prev.findIndex((s) => s.id === step.id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = step;
          return next;
        }
        return [...prev, step];
      });
    });

    source.addEventListener("approval", (event) => {
      const req = JSON.parse(event.data) as ApprovalRequest;
      setApproval(req);
    });

    source.addEventListener("done", (event) => {
      const payload = JSON.parse(event.data) as {
        briefing?: string;
        steps?: AgentStep[];
      };
      if (payload.briefing) setBriefing(payload.briefing);
      if (payload.steps) setSteps(payload.steps);
      setLoading(false);
      source.close();
    });

    source.onerror = () => {
      setError("Lost connection to agent stream");
      setLoading(false);
      source.close();
    };
  }

  async function decide(approved: boolean) {
    if (!sessionId) return;
    await fetch(`${API_URL}/api/missions/${sessionId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved }),
    });
    setApproval(null);
  }

  return (
    <main className="container">
      <section className="hero">
        <h1>OpenAid Provisioner</h1>
        <p>
          Turns chaotic humanitarian data requests into governed Fivetran pipelines.
          Search HDX, plan connector strategy, approve writes, sync to BigQuery,
          and deliver field briefings.
          <span className="badge">Fivetran Track</span>
        </p>
      </section>

      <section className="panel">
        <form
          className="prompt-form"
          onSubmit={(e) => {
            e.preventDefault();
            startMission();
          }}
        >
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the humanitarian data need..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !prompt.trim()}>
            {loading ? "Running..." : "Start mission"}
          </button>
        </form>
        {error && <p style={{ color: "var(--danger)", marginTop: "0.75rem" }}>{error}</p>}
      </section>

      {approval && (
        <section className="panel approval">
          <h3 style={{ marginTop: 0 }}>{approval.title}</h3>
          <p>{approval.summary}</p>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem" }}>
            {JSON.stringify(approval.plan, null, 2)}
          </pre>
          <div className="approval-actions">
            <button className="approve" onClick={() => decide(true)}>
              Approve provisioning
            </button>
            <button onClick={() => decide(false)}>Reject</button>
          </div>
        </section>
      )}

      {steps.length > 0 && (
        <section className="panel">
          <h3 style={{ marginTop: 0 }}>Agent execution</h3>
          <div className="steps">
            {steps.map((step) => (
              <div key={step.id} className={`step ${step.status}`}>
                <div className="dot" />
                <div>
                  <div className="step-title">{step.label}</div>
                  <div className="step-meta">
                    {step.tool && <span>{step.tool} · </span>}
                    {step.status}
                    {step.detail ? ` — ${step.detail}` : ""}
                  </div>
                </div>
              </div>
            ))}
          </div>
          {running && (
            <p style={{ color: "var(--muted)", marginBottom: 0 }}>
              Streaming live steps from FastAPI orchestrator...
            </p>
          )}
        </section>
      )}

      {briefing && (
        <section className="panel briefing">
          <h3 style={{ marginTop: 0 }}>Field briefing</h3>
          <pre>{briefing}</pre>
        </section>
      )}
    </main>
  );
}
