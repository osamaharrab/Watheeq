import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { AuditPanel } from "@/components/ask/AuditPanel";
import { answered, auditRecord } from "./fixtures";

describe("AuditPanel", () => {
  it("hides generated Cypher until the analyst explicitly asks for it", async () => {
    render(
      <AuditPanel requestId={auditRecord.request_id} response={answered} audit={{ kind: "ok", record: auditRecord }} onRetry={() => {}} />,
    );
    expect(screen.getByText(auditRecord.request_id)).toBeInTheDocument();
    expect(screen.getByText("No conflicts found")).toBeInTheDocument();
    expect(screen.getByText("Technical details").closest("details")).not.toHaveAttribute("open");
    expect(screen.queryByTestId("generated-cypher")).not.toBeInTheDocument();
    expect(screen.queryByText(/MATCH \(holder\)/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("Technical details"));
    expect(screen.queryByTestId("generated-cypher")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "View generated Cypher" }));
    expect(screen.getByTestId("generated-cypher")).toHaveTextContent("MATCH (holder)");
  });

  it("flags a disagreement between audit outcome and response", () => {
    render(
      <AuditPanel
        requestId={auditRecord.request_id}
        response={answered}
        audit={{ kind: "ok", record: { ...auditRecord, outcome: "abstained" } }}
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText("The audit record doesn't match this result")).toBeInTheDocument();
  });
});
