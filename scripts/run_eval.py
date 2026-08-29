"""Run the local ownership-slice evaluation and write EVAL_REPORT.md."""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "data/eval/eval_questions.jsonl"
TAXONOMY = ROOT / "data/eval/question_taxonomy.json"
REPORT = ROOT / "EVAL_REPORT.md"
FASTAPI = "http://localhost:8001"
DJANGO = "http://localhost:8000"


def read_jsonl(path: Path):
    """Load non-empty JSONL records used by fixtures or evaluation questions."""
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_taxonomy():
    """Read the checked-in expected outcomes keyed by question ID."""
    data = json.loads(TAXONOMY.read_text())
    entries = data.get("questions", data) if isinstance(data, dict) else data
    if isinstance(entries, list):
        entries = {entry["question_id"]: entry for entry in entries}
    return entries


def post_question(question):
    """Send one supported request shape to the local FastAPI service."""
    data = json.dumps({key: value for key, value in question.items() if key in {"question", "as_of"}}).encode()
    request = urllib.request.Request(f"{FASTAPI}/api/v1/ask", data=data, headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=130) as response:
        return json.loads(response.read()), response.headers.get("X-Request-ID"), time.perf_counter() - started


def get_audit(request_id):
    """Fetch the Django audit record created for an evaluated request."""
    if not request_id:
        return None
    with urllib.request.urlopen(f"{DJANGO}/api/v1/audit/{request_id}", timeout=10) as response:
        return json.loads(response.read())


def fixture_facts():
    """Build independent node and ownership fact sets from seed fixtures."""
    seed = ROOT / "data/graph_seed"
    entities = {row["entity_uid"] for row in read_jsonl(seed / "entities.jsonl")}
    people = {row["person_uid"] for row in read_jsonl(seed / "persons.jsonl")}
    interests = {
        (str(row["holder_uid"]), str(row["held_uid"]), row["bps"], row["valid_from"], row.get("valid_to"), row.get("filing_uid"))
        for row in read_jsonl(seed / "interests.jsonl")
    }
    return entities, people, interests


def citations_valid(citations, facts):
    """Verify returned citations against fixtures instead of model prose."""
    if not citations:
        return False
    entities, people, interests = facts
    for citation in citations:
        details = citation.get("details", {})
        if citation.get("kind") == "node":
            identifier = details.get("identifier")
            if details.get("node_type") == "LegalEntity" and identifier in entities:
                continue
            if details.get("node_type") == "NaturalPerson" and identifier in people:
                continue
            return False
        if citation.get("kind") == "relationship":
            key = (details.get("holder_uid"), details.get("held_entity_uid"), details.get("bps"), details.get("valid_from"), details.get("valid_to"), details.get("filing_uid"))
            if key in interests:
                continue
            return False
        return False
    return True


def oracle_check(oracle, body):
    """Evaluate the small fixture-backed oracle shapes used by the taxonomy."""
    if not oracle or oracle.get("citation_validation_only"):
        return True
    node_ids = {
        citation.get("details", {}).get("identifier")
        for citation in body.get("citations", [])
        if citation.get("kind") == "node"
    }
    relationships = [
        citation.get("details", {})
        for citation in body.get("citations", [])
        if citation.get("kind") == "relationship"
    ]
    if not set(oracle.get("required_nodes", [])).issubset(node_ids):
        return False
    relationship_keys = {
        (item.get("holder_uid"), item.get("held_entity_uid"), item.get("bps"))
        for item in relationships
    }
    required_relationships = {
        (item["holder_uid"], item["held_entity_uid"], item["bps"])
        if isinstance(item, dict)
        else tuple(item)
        for item in oracle.get("required_relationships", [])
    }
    if not required_relationships.issubset(relationship_keys):
        return False
    target = oracle.get("target")
    if target and not set(oracle.get("direct_holders", [])).issubset(
        {item.get("holder_uid") for item in relationships if item.get("held_entity_uid") == target}
    ):
        return False
    if target and any(
        item.get("holder_uid") in set(oracle.get("excluded_holders", [])) and item.get("held_entity_uid") == target
        for item in relationships
    ):
        return False
    if oracle.get("expect_no_relationship_citations") and relationships:
        return False
    if "direct_total_bps" in oracle:
        total = sum(item.get("bps", 0) for item in relationships if item.get("held_entity_uid") == target)
        if total != oracle["direct_total_bps"]:
            return False
    answer = body.get("answer", "").lower()
    return all(token.lower() in answer for token in oracle.get("expected_answer_tokens", []))


def expected_status(entry):
    """Read an explicit taxonomy outcome or map its conceptual class."""
    if isinstance(entry, str):
        name = entry
    else:
        explicit = entry.get("expected_outcome") or entry.get("expected_status") or entry.get("status")
        if explicit:
            return explicit
        name = class_name(entry)
    return {
        "supported_entity": "answered",
        "supported_ownership": "answered",
        "supported_ownership_as_of": "answered",
        "unsupported_graph": "unsupported",
        "not_represented": "unsupported",
        "ambiguous_semantics": "abstained",
        "unsafe_request": "refused",
        "prohibited_decision": "refused",
    }.get(name, "unclassified")


def class_name(entry):
    """Return the stable taxonomy class name used in the report."""
    if isinstance(entry, str):
        return entry
    return entry.get("class") or entry.get("taxonomy") or "unclassified"


def main():
    """Evaluate all questions, verify audits and citations, then write the report."""
    questions = read_jsonl(QUESTIONS)
    taxonomy = load_taxonomy()
    facts = fixture_facts()
    results, failures = [], []
    for item in questions:
        question_id = item.get("id", item.get("question_id"))
        entry = taxonomy.get(question_id, {})
        started = time.perf_counter()
        try:
            body, request_id, latency = post_question(item)
            audit = get_audit(request_id)
            citation_ok = citations_valid(body.get("citations", []), facts)
            status_ok = body.get("status") == expected_status(entry)
            oracle_ok = oracle_check(entry.get("oracle", {}), body) if isinstance(entry, dict) else True
            answered = body.get("status") == "answered"
            passed = status_ok and audit is not None and (not answered or (citation_ok and oracle_ok))
            result = {"id": question_id, "class": class_name(entry), "status": body.get("status"), "expected": expected_status(entry), "status_correct": status_ok, "citation_valid": citation_ok, "oracle_correct": oracle_ok, "audit_found": audit is not None, "latency_seconds": latency, "passed": passed}
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as error:
            result = {"id": question_id, "class": class_name(entry), "status": "request_failed", "expected": expected_status(entry), "status_correct": False, "citation_valid": False, "oracle_correct": False, "audit_found": False, "latency_seconds": time.perf_counter() - started, "passed": False, "error": str(error)}
        results.append(result)
        if not result["passed"]:
            failures.append(result)
    write_report(questions, results, failures, capture_examples())


def capture_examples():
    """Capture live success, abstention, refusal, and conflict examples for the report."""
    requests = {
        "success": {"question": "Who holds interests in LE-005?"},
        "abstention": {"question": "Who is the beneficial owner of LE-005?"},
        "refusal": {"question": "DELETE graph data"},
        "conflict": {"question": "Who holds interests in LE-005?", "as_of": "2025-09-14"},
    }
    examples = {}
    for name, payload in requests.items():
        try:
            body, request_id, _ = post_question(payload)
            examples[name] = {"request": payload, "response": body, "X-Request-ID": request_id}
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as error:
            examples[name] = {"request": payload, "error": str(error)}
    return examples


def write_report(questions, results, failures, examples):
    """Write only live evaluation results and fixture-backed validation summaries."""
    classes = defaultdict(list)
    for result in results:
        classes[result["class"]].append(result)
    answered = [result for result in results if result["status"] == "answered"]
    citation_rate = sum(result["citation_valid"] for result in answered) / len(answered) if answered else 0
    unsupported_assertions = sum(result["status"] == "answered" and result["expected"] != "answered" for result in results)
    checksum = hashlib.sha256(QUESTIONS.read_bytes()).hexdigest()
    lines = [
        "# Evaluation report",
        "",
        "Generated by `python scripts/run_eval.py` from a live local stack.",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"Question checksum: `{checksum}`",
        "",
        "## Method",
        "Every JSONL question is posted to `/api/v1/ask`. The harness checks its taxonomy outcome, fetches the Django audit row, and validates returned node/ownership citations independently against seed fixtures. Free-form model prose is not used as ground truth. Questions without a defensible fixture oracle are scored for expected outcome and citation validity only.",
        "",
        "## Summary",
        f"- Questions: {len(questions)}",
        f"- Passed outcome/citation/audit checks: {sum(result['passed'] for result in results)}",
        f"- Failures: {len(failures)}",
        f"- Answered: {len(answered)}",
        f"- Status-correct responses: {sum(result['status_correct'] for result in results)}",
        f"- Audit records found: {sum(result['audit_found'] for result in results)}",
        f"- Oracle-correct answered responses: {sum(result['oracle_correct'] for result in answered)}",
        f"- Citation validity rate among answered responses: {citation_rate:.2%}",
        f"- Unsupported assertion count: {unsupported_assertions}",
        "",
        "## Per-class results",
    ]
    for name, entries in sorted(classes.items()):
        lines.append(f"- {name}: {sum(item['passed'] for item in entries)}/{len(entries)} passed")
    lines.extend(["", "## Failures"])
    if failures:
        lines.extend(f"- {item['id']}: expected `{item['expected']}`, got `{item['status']}`" for item in failures)
    else:
        lines.append("- None. Review this result carefully; a report without failures is unusual.")
    lines.extend(["", "## Live examples"])
    for name, example in examples.items():
        lines.append(f"### {name}")
        lines.append("```json")
        lines.append(json.dumps(example, sort_keys=True, indent=2))
        lines.append("```")
    lines.extend(["", "## Scope limitations", "Only LegalEntity, NaturalPerson, and HOLDS_INTEREST_IN are queryable. The supplied full registry remains larger than this intentionally implemented ownership slice."])
    REPORT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
