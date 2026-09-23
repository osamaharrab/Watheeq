import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EntitySearch } from "@/components/search/EntitySearch";
import { SearchResults } from "@/components/search/SearchResults";
import { legalEntityA, legalEntityB, person } from "./fixtures";

describe("SearchResults", () => {
  it("renders every ambiguous candidate and never auto-selects one", () => {
    render(<SearchResults query="Shared Name Holdings" matches={[legalEntityA, legalEntityB, person]} />);
    expect(screen.getByText("More than one match — please choose")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    // Each candidate needs its own explicit action; nothing navigates on its own.
    expect(screen.getAllByRole("link", { name: "View ownership" })).toHaveLength(2);
    expect(window.location.pathname).toBe("/");
  });

  it("routes a natural person to Ask, not to the legal-entity workspace", () => {
    render(<SearchResults query="x" matches={[person]} />);
    expect(screen.getByRole("link", { name: "Ask about this person" })).toHaveAttribute("href", "/ask?entity=NP-T1");
    expect(screen.queryByRole("link", { name: "View ownership" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /\/entities\// })).not.toBeInTheDocument();
  });

  it("flags approximate (hybrid) candidates as not exact", () => {
    render(<SearchResults query="nonsense" matches={[{ ...legalEntityA, match_method: "hybrid" }]} />);
    expect(screen.getByText("No exact match — these are possible matches")).toBeInTheDocument();
    expect(screen.getByText("Possible match (not exact)")).toBeInTheDocument();
  });

  it("shows an explicit empty state for zero matches", () => {
    render(<SearchResults query="nothing" matches={[]} />);
    expect(screen.getByText("No matching company or person was found")).toBeInTheDocument();
  });

  it("search examples fill the field without running a search", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<EntitySearch />);
    await userEvent.click(screen.getByRole("button", { name: "Meridian Capital Partners" }));
    expect(screen.getByLabelText("Company or person")).toHaveValue("Meridian Capital Partners");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByText("Matches")).not.toBeInTheDocument();
  });
});
