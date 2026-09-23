import type { AskStatus } from "@/types/api";

type Tone = "success" | "neutral" | "info" | "danger" | "warning" | "caution";

// Plain-language framing for each backend /ask outcome.
// `label` is the official status name shown in the pill. `headline` and `helper`
// explain it to a non-technical analyst. The backend's own reason text is always
// kept and shown under "Technical details" for non-answers.
export const OUTCOMES: Record<AskStatus, { label: string; tone: Tone; headline: string; helper: string }> = {
  answered: {
    label: "Answered",
    tone: "success",
    headline: "Answer",
    helper: "Based on verified ownership records. Each numbered marker links to the evidence it comes from.",
  },
  abstained: {
    label: "Abstained",
    tone: "neutral",
    headline: "Watheeq couldn't answer this question safely.",
    helper:
      "Watheeq couldn't verify enough information to answer safely. Try asking a more specific ownership question or select an entity first.",
  },
  unsupported: {
    label: "Unsupported",
    tone: "info",
    headline: "This question is outside Watheeq's ownership-data scope.",
    helper: "Watheeq answers questions about who holds ownership interests in companies. Try one of the examples.",
  },
  refused: {
    label: "Refused",
    tone: "danger",
    headline: "Watheeq can't provide this type of assessment.",
    helper:
      "Watheeq reports recorded ownership facts only. It doesn't score, rate or recommend, and it never changes data.",
  },
  bounded_out: {
    label: "Bounded out",
    tone: "warning",
    headline: "This question is too broad to answer within Watheeq's safety limits.",
    helper: "No partial answer is shown. Try a narrower question, for example about a single entity.",
  },
  unavailable: {
    label: "Unavailable",
    tone: "caution",
    headline: "The required service or evidence is temporarily unavailable.",
    helper: "This is not an answer about the entity. Please try again in a moment.",
  },
};
