import type { FlowNode } from "../types";

const NODES: Record<
  FlowNode,
  { title: string; body: string[]; tone: string }
> = {
  ticket: {
    title: "Support Ticket",
    body: ["Incoming customer issue text is the starting point for the investigation."],
    tone: "blue",
  },
  receive: {
    title: "1  Agent Receives Ticket",
    body: ["Understands the issue", "Extracts key details", "Creates an investigation plan"],
    tone: "purple",
  },
  plan: {
    title: "2  Plan & Decide Next Steps",
    body: [
      "Search database for logs/data",
      "Call relevant APIs",
      "Check GitHub for code changes",
      "Analyze results and propose a fix",
    ],
    tone: "green",
  },
  database: {
    title: "Database Tool",
    body: ["Query application logs", "Check user data", "Look for related errors"],
    tone: "red",
  },
  api: {
    title: "API Tool",
    body: ["Call internal/external APIs", "Get service status", "Fetch additional data"],
    tone: "green",
  },
  github: {
    title: "GitHub Tool",
    body: ["Search recent code changes", "Find related pull requests", "Check commits / diffs"],
    tone: "purple",
  },
  reasoning: {
    title: "Analysis & Reasoning",
    body: ["Combine information", "Identify root cause", "Generate fix proposal"],
    tone: "navy",
  },
  analyze: {
    title: "3  Analyze & Create Proposed Fix",
    body: [
      "Summarize the findings",
      "Identify the root cause",
      "Suggest code or configuration updates",
      "Provide steps to verify the fix",
    ],
    tone: "purple",
  },
  output: {
    title: "Final Output",
    body: [
      "Issue summary",
      "Root cause based on data, logs, and code",
      "Proposed fix and verification steps",
      "References from DB, APIs, and GitHub",
    ],
    tone: "green",
  },
};

function NodeCard({
  id,
  active,
  numbered,
}: {
  id: FlowNode;
  active: boolean;
  numbered?: boolean;
}) {
  const node = NODES[id];
  return (
    <article className={`node ${node.tone} ${active ? "active" : ""}`}>
      <h3>
        <span className={`status-dot ${active ? "on" : ""}`} />
        {node.title}
      </h3>
      {numbered ? (
        <ol>
          {node.body.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
      ) : (
        <ul>
          {node.body.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
    </article>
  );
}

export function FlowDiagram({ active }: { active: Set<FlowNode> }) {
  return (
    <section className="card flow">
      <div className="row three">
        <NodeCard id="ticket" active={active.has("ticket")} />
        <NodeCard id="receive" active={active.has("receive")} />
        <NodeCard id="plan" active={active.has("plan")} numbered />
      </div>
      <div className="arrow">↓</div>
      <div className="orchestrator">
        <div className="orchestrator-head">
          <div>
            <h3>Agent (Orchestrator)</h3>
            <p>Manages the workflow, calls tools, collects results, and reasons over the information.</p>
          </div>
        </div>
        <div className="row four">
          <NodeCard id="database" active={active.has("database")} />
          <NodeCard id="api" active={active.has("api")} />
          <NodeCard id="github" active={active.has("github")} />
          <NodeCard id="reasoning" active={active.has("reasoning")} />
        </div>
        <p className="iterate">Iterate if more information is needed</p>
      </div>
      <div className="arrow">↓</div>
      <NodeCard id="analyze" active={active.has("analyze")} />
      <div className="arrow">↓</div>
      <NodeCard id="output" active={active.has("output")} />
    </section>
  );
}
