// Illustrative inputs shown as "Try an example" chips.
// They reference records in the supplied seed data so a first-time user sees how
// to phrase a search or question. They ONLY pre-fill form fields: nothing is
// submitted automatically, and every result still comes from the live backend.

export const SEARCH_EXAMPLES = ["Aqaba Logistics Park Company", "Meridian Capital Partners", "LE-005"];

export interface AskExample {
  question: string;
  // The backend requires historical dates as a structured as_of field (a year in
  // the question text alone makes it abstain), so date examples also fill as_of.
  asOf?: string;
}

const DEFAULT_EXAMPLE_ENTITY = "LE-005";

// Onboarding examples should show the product working. Each phrasing below returned
// "answered" with citations in 3 of 3 runs against the live backend (local planner,
// supplied seed data). Phrasings that repeatedly abstained were deliberately left out.
const VERIFIED_EXAMPLES = [
  "Who holds interests in LE-005?",
  "Who holds an interest in LE-001?",
  "Who holds interests in LE-010?",
  "Which entities does NP-001 hold interests in?",
];

/** Examples adapt to the selected context so the first chip names the entity the analyst chose. */
export function askExamples(context: { id: string; type: "LegalEntity" | "NaturalPerson" } | null): AskExample[] {
  // Same verified sentence shapes, with the selected ID substituted in.
  const contextQuestion =
    context?.type === "NaturalPerson"
      ? `Which entities does ${context.id} hold interests in?`
      : `Who holds interests in ${context?.id ?? DEFAULT_EXAMPLE_ENTITY}?`;
  const questions = [contextQuestion, ...VERIFIED_EXAMPLES.filter((question) => question !== contextQuestion)];
  return questions.slice(0, 4).map((question) => ({ question }));
}
