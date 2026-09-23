import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AskWatheeq } from "@/components/ask/AskWatheeq";
import { answered } from "./fixtures";

const REQUEST_ID = "11111111-2222-4333-8444-555555555555";

function json(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), { ...init, headers: { "content-type": "application/json", ...init.headers } });
}

describe("Ask flow", () => {
  it("keeps a successful answer visible when audit retrieval fails, and reads X-Request-ID", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/api/ask") {
        expect(JSON.parse(String(init?.body))).toEqual({ question: "Who holds interests in LE-T1?" });
        return json(answered, { headers: { "x-request-id": REQUEST_ID } });
      }
      if (url === `/api/audit/${REQUEST_ID}`) {
        return json({ detail: "The ledger service could not be reached." }, { status: 502, headers: { "x-watheeq-bff-error": "unreachable" } });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(<AskWatheeq contextId={null} />);
    await userEvent.type(screen.getByLabelText("Your ownership question"), "Who holds interests in LE-T1?");
    await userEvent.click(screen.getByRole("button", { name: "Ask Watheeq" }));

    await screen.findByText(/audit record couldn't be loaded/);
    expect(screen.getByTestId("ask-result")).toHaveAttribute("data-status", "answered");
    expect(screen.getByText(REQUEST_ID)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(`/api/audit/${REQUEST_ID}`, expect.anything());
  });

  it("sends as_of only when a date is chosen", async () => {
    const bodies: unknown[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      bodies.push(JSON.parse(String(init?.body)));
      return json(answered);
    });
    render(<AskWatheeq contextId={null} />);
    await userEvent.type(screen.getByLabelText("Your ownership question"), "q");
    await userEvent.type(screen.getByLabelText(/^Date/), "2025-09-14");
    await userEvent.click(screen.getByRole("button", { name: "Ask Watheeq" }));
    await waitFor(() => expect(bodies).toEqual([{ question: "q", as_of: "2025-09-14" }]));
  });

  it("shows the fail-closed audit error instead of an answer", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ detail: "Audit persistence is unavailable" }, { status: 503 }));
    render(<AskWatheeq contextId={null} />);
    await userEvent.type(screen.getByLabelText("Your ownership question"), "q");
    await userEvent.click(screen.getByRole("button", { name: "Ask Watheeq" }));
    await screen.findByText("No answer was released");
    expect(screen.queryByTestId("ask-result")).not.toBeInTheDocument();
  });

  it("fills the question from an example without submitting", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<AskWatheeq contextId={null} />);
    const question = screen.getByLabelText("Your ownership question") as HTMLTextAreaElement;

    await userEvent.click(screen.getByRole("button", { name: "Who holds interests in LE-005?" }));
    expect(question.value).toBe("Who holds interests in LE-005?");
    await userEvent.click(screen.getByRole("button", { name: "Which entities does NP-001 hold interests in?" }));
    expect(question.value).toBe("Which entities does NP-001 hold interests in?");
    expect((screen.getByLabelText(/^Date/) as HTMLInputElement).value).toBe("");

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByTestId("ask-result")).not.toBeInTheDocument();
  });

  it("examples are keyboard accessible buttons", async () => {
    vi.spyOn(globalThis, "fetch");
    render(<AskWatheeq contextId={null} />);
    const chip = screen.getByRole("button", { name: "Who holds an interest in LE-001?" });
    chip.focus();
    await userEvent.keyboard("{Enter}");
    expect((screen.getByLabelText("Your ownership question") as HTMLTextAreaElement).value).toBe(
      "Who holds an interest in LE-001?",
    );
  });
});
