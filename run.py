#!/usr/bin/env python3
"""Model-based clue extraction followed by generic symbolic rota solving."""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def load_dotenv(path):
    if not os.path.exists(path): return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_dotenv(os.path.join(HERE, ".env")); load_dotenv(".env")
from model_client import call_model
from prompt import extraction_messages
from solver import validate_extraction, solve

CAPS = {"1x": 1, "3x": 3, "10x": 10}    
SYSTEM = "You extract typed clues from shift notes. Follow the requested JSON schema exactly."

def parse_header(text):
    head = text.split("\n\n", 1)[0]
    people = re.search(r"on the rota:\s*(.+?)\.\s", head).group(1)
    blocks = re.search(r"Blocks run\s*(.+?),\s*one person", head).group(1)
    stations = re.search(r"one person on each:\s*(.+?)\.\s", head).group(1)
    holders = re.search(r"on a station are\s*(.+?);", head).group(1)
    split = lambda s: [x.strip() for x in s.split(",") if x.strip()]
    return {"people": split(people), "blocks": split(blocks), "stations": split(stations), "station_people": split(holders)}

def statements(text):
    parts = text.split("\n\n", 1)
    return [x.strip() for x in parts[1].splitlines() if x.strip()] if len(parts) == 2 else []

class Budget:
    def __init__(self, cap):
        self.cap = cap
        self.used = {}

    def call(self, item_id, messages, statement_ids, header):
        n = self.used.get(item_id, 0)
        if n >= self.cap:
            raise RuntimeError(f"{item_id}: budget cap {self.cap} reached")

        self.used[item_id] = n + 1
        return call_model(messages, item_id, statement_ids, header)


def make_batches(lines, max_batches):
    records = [
        {"statement_id": i, "source": line}
        for i, line in enumerate(lines, start=1)
    ]

    # Don't waste calls if the puzzle has fewer statements.
    batch_count = min(max_batches, len(records))
    if batch_count == 0:
        return []

    # Balanced, contiguous batches preserve statement order.
    q, r = divmod(len(records), batch_count)
    batches = []
    start = 0

    for i in range(batch_count):
        size = q + (1 if i < r else 0)
        batches.append(records[start:start + size])
        start += size

    return batches

# def normalize_clue_keys(payload):
#     if not isinstance(payload, dict):
#         return payload

#     clues = payload.get("clues")
#     if not isinstance(clues, list):
#         return payload

#     allowed = {"statement_id", "kind", "args"}

#     payload["clues"] = [
#         {key: value for key, value in clue.items() if key in allowed}
#         if isinstance(clue, dict)
#         else clue
#         for clue in clues
#     ]
#     return payload

def solve_item(budget, item):
    header = parse_header(item["text"])
    lines = statements(item["text"])
    batches = make_batches(lines, budget.cap)

    extracted = []

    # print(
    # f"\n[{item['id']}] RAW MODEL RESPONSE:\n{raw!r}\n",
    # file=sys.stderr,
    # flush=True,
    # )

    # if not isinstance(raw, str) or not raw.strip():
    #     raise ValueError("model returned an empty or non-text response")

    # try:
    #     payload = json.loads(raw)
    # except (json.JSONDecodeError, TypeError) as exc:
    #     raise ValueError(
    #         "Model response was not valid JSON despite "
    #         "structured-output constraints"
    #     ) from exc

    # try:
    #     payload = json.loads(raw)
    #     parse_path = "json.loads"
    # except (json.JSONDecodeError, TypeError) as exc:
    #     print(
    #         f"[{item['id']}] JSON parsing failed: "
    #         f"{type(exc).__name__}: {exc}",
    #         file=sys.stderr,
    #         flush=True,
    #     )

    #     from json_repair import repair_json
    #     payload = repair_json(raw, return_objects=True)
    #     parse_path = "json_repair"

    # print(
    #     f"[{item['id']}] Parse path: {parse_path}",
    #     file=sys.stderr,
    #     flush=True,
    # )
    # print(
    #     f"[{item['id']}] Parsed clue count: "
    #     f"{len(payload['clues']) if isinstance(payload, dict) and isinstance(payload.get('clues'), list) else 'invalid payload'}",
    #     file=sys.stderr,
    #     flush=True,
    # )

    # print(
    # f"[{item['id']}] PARSED MODEL PAYLOAD "
    # f"(before validation):\n"
    # f"{json.dumps(payload, indent=2, ensure_ascii=False)}",
    # file=sys.stderr,
    # flush=True,
    # )

    for batch in batches:
        ids = [record["statement_id"] for record in batch]
        messages = extraction_messages(item, header, batch)

        raw = budget.call(
            item["id"],
            messages,
            ids,
            header,
        )

        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("model returned an empty or non-text response")

        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("model response was not valid JSON") from exc

        if not isinstance(payload, dict) or not isinstance(
            payload.get("clues"), list
        ):
            raise ValueError("model response did not contain a clues list")

        # Check each batch's IDs before combining results.
        returned_ids = [
            c.get("statement_id")
            for c in payload["clues"]
            if isinstance(c, dict)
        ]
        if sorted(returned_ids) != sorted(ids):
            raise ValueError(
                f"batch expected statement IDs {ids}, got {returned_ids}"
            )

        extracted.extend(payload["clues"])
    # payload = normalize_clue_keys(payload)

    # from collections import Counter

    # if isinstance(payload, dict) and isinstance(payload.get("clues"), list):
    #     clues = payload["clues"]
    #     ids = [
    #         c.get("statement_id")
    #         for c in clues
    #         if isinstance(c, dict)
    #     ]
    #     counts = Counter(ids)

    #     print(f"[{item['id']}] Expected statements: {len(lines)}", file=sys.stderr)
    #     print(f"[{item['id']}] Returned clues: {len(clues)}", file=sys.stderr)
    #     print(f"[{item['id']}] Statement IDs: {ids}", file=sys.stderr)
    #     print(
    #         f"[{item['id']}] Duplicate IDs: "
    #         f"{ {sid: count for sid, count in counts.items() if count > 1} }",
    #         file=sys.stderr,
    #     )
    #     print(
    #         f"[{item['id']}] Missing IDs: "
    #         f"{sorted(set(range(1, len(lines) + 1)) - set(ids))}",
    #         file=sys.stderr,
    #     )


    # Downgrade impossible self-relations to explicit unknown clues.
    # Do not let one invalid semantic extraction invalidate the whole item.
    for clue in extracted:
        if not isinstance(clue, dict):
            continue

        kind = clue.get("kind")
        args = clue.get("args", {})

        if kind in {"person_before_person", "person_immediately_before"}:
            if args.get("first") == args.get("second"):
                clue["kind"] = "unknown"
                clue["args"] = {}

        elif kind == "person_between":
            names = [
                args.get("middle"),
                args.get("endpoint_a"),
                args.get("endpoint_b"),
            ]
            if len(set(names)) < 3:
                clue["kind"] = "unknown"
                clue["args"] = {}

    clues = validate_extraction(
        {"clues": extracted},
        header,
        lines,
    )

    # unknown_ids = [
    #     clue["statement_id"]
    #     for clue in clues
    #     if clue["kind"] == "unknown"    
    # ]

    # if unknown_ids:
    #     print(
    #         f"[{item['id']}] Unknown statement IDs: {unknown_ids}",
    #         file=sys.stderr,
    #         flush=True,
    #     )

    answer = solve(header, clues)

    # if answer["case"] == "unknown": raise ValueError(answer["reason"])

    return answer

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("items"); ap.add_argument("--budget", choices=list(CAPS), required=True); ap.add_argument("--out", required=True)
    args = ap.parse_args()
    with open(args.items, encoding="utf-8") as f: items = json.load(f)
    budget, answers = Budget(CAPS[args.budget]), {}
    for item in items:
        try: answers[item["id"]] = solve_item(budget, item)
        except Exception as e:
            print(f"[{item['id']}] extraction/solve failed: {e!r}", file=sys.stderr)
            # Explicit error object is preferable to fabricating an answer. This
            # is a diagnostic intermediate format; inspect failures before scoring.
            answers[item["id"]] = {"case": "unknown", "reason": str(e)}
        print(f"{item['id']}: {answers[item['id']]['case']} ({budget.used.get(item['id'], 0)} call(s))", file=sys.stderr)
        with open(args.out, "w", encoding="utf-8") as f: json.dump(answers, f, indent=2, ensure_ascii=False)
if __name__ == "__main__": main()
