"use client";

import { useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type Citation = {
  source: string;
  snippet: string;
  score: number;
};

export default function HomePage() {
  const [workspaceId, setWorkspaceId] = useState("default");
  const [message, setMessage] = useState("");
  const [context, setContext] = useState("");
  const [answer, setAnswer] = useState("");
  const [model, setModel] = useState("");
  const [traceId, setTraceId] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setAnswer("");
    setModel("");
    setTraceId("");
    setCitations([]);
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: workspaceId || "default",
          message,
          context: context || null
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Request failed.");
      }
      setAnswer(data.answer || "");
      setModel(data.model || "");
      setTraceId(data.trace_id || "");
      setCitations(Array.isArray(data.citations) ? data.citations : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>SaaS Support Copilot MVP</h1>
      <p>
        Ask support questions grounded by context. This is the initial UI for a production-oriented
        SaaS copilot.
      </p>

      <form className="panel" onSubmit={onSubmit}>
        <label htmlFor="workspace">Workspace ID</label>
        <input
          id="workspace"
          type="text"
          value={workspaceId}
          onChange={(e) => setWorkspaceId(e.target.value)}
          placeholder="default"
          className="text-input"
        />

        <label htmlFor="message">Question</label>
        <textarea
          id="message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="How should we respond to this billing ticket?"
          required
        />

        <label htmlFor="context">Context (optional)</label>
        <textarea
          id="context"
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Paste KB excerpt, ticket details, policy snippet..."
        />

        <button type="submit" disabled={loading || !message.trim()}>
          {loading ? "Generating..." : "Generate response"}
        </button>
      </form>

      {error ? (
        <div className="panel">
          <h3>Error</h3>
          <div className="answer">{error}</div>
        </div>
      ) : null}

      {answer ? (
        <div className="panel">
          <h3>Copilot Draft</h3>
          <div className="answer">{answer}</div>
          <hr />
          <p>
            <strong>Model:</strong> {model || "n/a"}
          </p>
          <p>
            <strong>Trace ID:</strong> {traceId || "n/a"}
          </p>
          <h4>Citations</h4>
          {citations.length === 0 ? (
            <p>No citations returned.</p>
          ) : (
            citations.map((citation, idx) => (
              <div key={`${citation.source}-${idx}`} className="panel">
                <p>
                  <strong>Source:</strong> {citation.source} ({Math.round(citation.score * 100)}%)
                </p>
                <div className="answer">{citation.snippet}</div>
              </div>
            ))
          )}
        </div>
      ) : null}
    </main>
  );
}
