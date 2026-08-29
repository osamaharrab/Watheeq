# AI use disclosure

## Tools and models used

I used OpenAI ChatGPT and OpenAI Codex as development-assistance tools. The exact ChatGPT and Codex model names were not recorded in the repository, so I do not state them here.

At runtime, the service uses the local Ollama model `qwen2.5-coder:7b`, pinned to digest `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`. This runtime model is separate from the development-assistance tools. The grounding index uses the local `all-MiniLM-L6-v2` embedding model.

## Runtime model experiment history

The initial local runtime model was `qwen3:4b`. I adopted `qwen2.5-coder:7b` after a final local experiment and also strengthened the planner contract during that work. The final 42/48 harness result must not be attributed to the model change alone. Invalid or incomplete model plans still fail closed; the application does not repair them automatically.

## How I used AI assistance

I made the final architecture, scope, schema, semantic, policy, evaluation, and implementation decisions.

I used Codex mainly to carry out specific implementation tasks that I described. I used ChatGPT to help turn my decisions into clear Codex prompts, discuss design alternatives, reason through bugs, inspect results I shared, and plan verification. Meaningful assistance included Text2Cypher behaviour, grounding and entity-resolution choices, policy edge cases, test-failure review, evaluation planning, and repository cleanup.

I reviewed AI-generated changes and ran the verification and tests myself. AI tools did not automatically define business truth, registry semantics, or evaluation ground truth.

The local runtime model is called once to plan ownership intent and Cypher. It does not write the final business answer; the application renders that answer deterministically from verified relationship facts and citations.

## AI behaviour I corrected

### Exact resolution before hybrid retrieval

Hybrid grounding was initially used directly for an exact legal-entity-name question. It returned several candidates and led to an incorrect ownership query. I changed the design so exact canonical ID or legal-name resolution runs first; hybrid lexical/vector discovery is only a fallback.

I verified the correction through `/api/v1/entities/resolve` and `/api/v1/ask` results, with focused grounding tests. This matters because a legal name can be non-unique, so an exact result may still correctly contain more than one entity rather than forcing a guess.

### Explicit ownership endpoint preservation

For a question naming both an ownership holder and a held legal entity, a planner could produce an incoming-ownership query and silently omit the holder. That would change the meaning of the question.

I kept exact named entities as planning hints and added fail-closed validation after mention resolution. If a supported ownership plan loses an explicit endpoint, it abstains before Neo4j executes rather than repairing the plan or returning a partial answer. Focused pipeline tests cover the preserved holder and target roles.

## My engineering judgment

I chose a narrow ownership slice and kept PostgreSQL as the source of truth, with Neo4j as a derived projection. I retained the supplied `bps` unit instead of creating percentage properties and interpreted effective dates with an inclusive `valid_to` upper bound.

I chose exact-first grounding, a fail-closed Cypher guard, explicit named-endpoint preservation, and distinct `answered`, `unsupported`, `abstained`, and `refused` outcomes. I also declined to add risk scores, credit scores, lending decisions, or recommendations because the supported facts do not justify them.

I did not alter evaluation ground truth to force a perfect result. The final evaluation recorded 42/48 passed outcome/citation/audit checks, with six retained failures, 48/48 audit records, and no unsupported assertions. One evaluation response was answered and passed its oracle and citation validation; several supported ownership formulations still abstain. Those limitations remain visible in `EVAL_REPORT.md`.
