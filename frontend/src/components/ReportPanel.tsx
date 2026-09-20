import type { InvestigationReport } from "../types";

export function ReportPanel({ report }: { report: InvestigationReport }) {
  const fix = report.proposed_fix;
  return (
    <section className="card report">
      <h2>Investigation report</h2>
      <p>{report.issue_summary}</p>

      <h3>Root cause</h3>
      <p>{report.root_cause}</p>

      <h3>Findings</h3>
      <ul>
        {report.findings.map((finding) => (
          <li key={finding.title}>
            <strong>{finding.source}</strong> — {finding.detail}
          </li>
        ))}
      </ul>

      <h3>Proposed fix</h3>
      <p>{fix.summary}</p>
      {fix.file_path ? <p>File: <code>{fix.file_path}</code></p> : null}
      {fix.current_code ? (
        <>
          <h3>Current / related code</h3>
          <pre>{fix.current_code}</pre>
        </>
      ) : null}
      {fix.suggested_code ? (
        <>
          <h3>Suggested change</h3>
          <pre>{fix.suggested_code}</pre>
        </>
      ) : null}

      {fix.configuration_changes.length > 0 ? (
        <>
          <h3>Configuration</h3>
          <ul>
            {fix.configuration_changes.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}

      <h3>Verification steps</h3>
      <ol>
        {fix.verification_steps.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ol>

      <h3>References</h3>
      <div className="refs">
        {report.references.map((ref) =>
          ref.startsWith("http") ? (
            <a key={ref} href={ref} target="_blank" rel="noreferrer">
              {ref}
            </a>
          ) : (
            <span key={ref}>{ref}</span>
          ),
        )}
      </div>
    </section>
  );
}
