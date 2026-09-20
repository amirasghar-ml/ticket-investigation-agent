import { FormEvent, useMemo, useState } from "react";
import { investigateTicket } from "./api";
import { FlowDiagram } from "./components/FlowDiagram";
import { ReportPanel } from "./components/ReportPanel";
import { Timeline } from "./components/Timeline";
import type { AgentEvent, FlowNode, InvestigationReport } from "./types";

const SAMPLE =
  "User cannot login to the application. Getting 500 error since yesterday.";

function activeNodes(events: AgentEvent[]): Set<FlowNode> {
  const active = new Set<FlowNode>(["ticket"]);
  for (const event of events) {
    if (event.stage === "receive") active.add("receive");
    if (event.stage === "plan") {
      active.add("receive");
      active.add("plan");
    }
    if (event.type === "tool_started" || event.type === "tool_completed") {
      const tool = (event.detail as { tool?: string } | null)?.tool;
      if (tool === "database" || tool === "api" || tool === "github") {
        active.add(tool);
      }
    }
    if (event.type === "reasoning" || event.type === "iterating") {
      active.add("reasoning");
    }
    if (event.stage === "analyze") active.add("analyze");
    if (event.stage === "output") {
      active.add("analyze");
      active.add("output");
      active.add("reasoning");
    }
  }
  return active;
}

export default function App() {
  const [ticket, setTicket] = useState(SAMPLE);
  const [email, setEmail] = useState("jane.doe@acme.com");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [report, setReport] = useState<InvestigationReport | null>(null);

  const nodes = useMemo(() => activeNodes(events), [events]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setRunning(true);
    setError(null);
    setEvents([]);
    setReport(null);
    try {
      await investigateTicket(ticket, email, (agentEvent) => {
        setEvents((current) => [...current, agentEvent]);
        if (agentEvent.type === "report_ready") {
          setReport(agentEvent.detail as InvestigationReport);
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Investigation failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <div>
          <h1>Support Ticket Agent</h1>
          <p>
            Submit a ticket. The orchestrator investigates with database, API, and GitHub
            tools, then returns a root cause and a proposed fix.
          </p>
        </div>
        <div className="badge">Demo data is seeded for the login 500 scenario</div>
      </header>

      <div className="layout">
        <form className="card panel" onSubmit={onSubmit}>
          <h2>New ticket</h2>
          <label htmlFor="ticket">Ticket</label>
          <textarea
            id="ticket"
            value={ticket}
            onChange={(change) => setTicket(change.target.value)}
            required
          />
          <label htmlFor="email">Reporter email (optional)</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(change) => setEmail(change.target.value)}
          />
          <div className="actions">
            <button className="primary" type="submit" disabled={running}>
              {running ? "Investigating…" : "Investigate"}
            </button>
            <button
              className="ghost"
              type="button"
              onClick={() => {
                setTicket(SAMPLE);
                setEmail("jane.doe@acme.com");
              }}
            >
              Use sample
            </button>
          </div>
          {error ? <div className="error">{error}</div> : null}
          <Timeline events={events} />
        </form>

        <div>
          <FlowDiagram active={nodes} />
          {report ? <ReportPanel report={report} /> : null}
        </div>
      </div>
    </div>
  );
}
