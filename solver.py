"""Generic exhaustive symbolic solver for the small rota domain.

The solver contains no item IDs or puzzle-specific answers. It enumerates the
finite assignment space and evaluates only validated typed clues.
"""
from itertools import permutations

PERSON_BLOCK = {"person_block_eq", "person_block_ne"}
PERSON_STATION = {"person_station_eq", "person_station_ne"}
TWO_PEOPLE = {"person_before_person", "person_immediately_before"}
ALLOWED = PERSON_BLOCK | PERSON_STATION | TWO_PEOPLE | {
    "station_holder_is", "station_holder_not", "person_between",
    "station_before_person", "person_before_station", "ignore", "unknown",
}


def validate_extraction(payload, header, source_lines):
    """Validate model extraction structurally and restore canonical source lines.

    Raises ValueError on malformed/incomplete extraction. Unknown semantic clues
    are retained as unknown; they are not silently turned into constraints.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("clues"), list):
        raise ValueError("extraction must be an object with a clues list")
    clues = payload["clues"]
    if len(clues) != len(source_lines):
        raise ValueError(f"expected {len(source_lines)} clues, got {len(clues)}")
    out = []
    people, blocks, stations, holders = (set(header[k]) for k in
                                         ("people", "blocks", "stations", "station_people"))
    required = {
        "person_block_eq": {"person", "block"}, "person_block_ne": {"person", "block"},
        "person_station_eq": {"person", "station"}, "person_station_ne": {"person", "station"},
        "station_holder_is": {"station", "person"}, "station_holder_not": {"station", "person"},
        "person_before_person": {"first", "second"},
        "person_immediately_before": {"first", "second"},
        "person_between": {"middle", "endpoint_a", "endpoint_b"},
        "station_before_person": {"station", "person"},
        "person_before_station": {"person", "station"},
        "ignore": set(), "unknown": set(),
    }
    seen = set()
    for c in clues:
        if not isinstance(c, dict):
            raise ValueError("each clue must be an object")

        expected_keys = {"statement_id", "kind", "args"}
        if set(c) != expected_keys:
            raise ValueError(
                f"unexpected clue keys at statement "
                f"{c.get('statement_id')!r}: "
                f"{sorted(set(c) - expected_keys)}"
            )
        
        sid, kind, args = c.get("statement_id"), c.get("kind"), c.get("args")
        if not isinstance(sid, int) or sid < 1 or sid > len(source_lines) or sid in seen:
            raise ValueError(f"invalid or duplicate statement_id: {sid!r}")
        seen.add(sid)
        if kind not in ALLOWED or not isinstance(args, dict):
            raise ValueError(f"invalid kind/args at statement {sid}")
        if set(args) != required[kind]:
            raise ValueError(f"wrong argument keys for {kind} at statement {sid}")
        # if c.get("source") not in (source_lines[sid - 1], source_lines[sid - 1].split(": ", 1)[-1]):
        #     # Also allow removal of a leading hedge/restatement prefix, but only
        #     # when the remaining source is literally contained in the line.
        #     if not (isinstance(c.get("source"), str) and c["source"] and c["source"] in source_lines[sid - 1]):
        #         raise ValueError(f"source does not match statement {sid}")
        for key, val in args.items():
            if not isinstance(val, str) or not val:
                raise ValueError(f"empty/non-string {key} at statement {sid}")
        if kind in PERSON_BLOCK and (args["person"] not in people or args["block"] not in blocks):
            raise ValueError(f"unknown person/block at statement {sid}")
        if kind in PERSON_STATION and (args["person"] not in holders or args["station"] not in stations):
            raise ValueError(f"unknown station-holder/station at statement {sid}")
        if kind in TWO_PEOPLE and (args["first"] not in people or args["second"] not in people or args["first"] == args["second"]):
            raise ValueError(f"invalid people at statement {sid}")
        if kind in {"station_holder_is", "station_holder_not", "station_before_person"} and (args["station"] not in stations or args["person"] not in (holders if kind != "station_before_person" else people)):
            raise ValueError(f"unknown station/person at statement {sid}")
        if kind == "person_before_station" and (args["person"] not in people or args["station"] not in stations):
            raise ValueError(f"unknown person/station at statement {sid}")
        if kind == "person_between" and any(args[k] not in people for k in ("middle", "endpoint_a", "endpoint_b")):
            raise ValueError(f"unknown person in between clue at statement {sid}")
        out.append({"statement_id": sid, "source": source_lines[sid - 1], "kind": kind, "args": args})
    if seen != set(range(1, len(source_lines) + 1)):
        raise ValueError("every source statement must appear exactly once")
    return sorted(out, key=lambda x: x["statement_id"])


def assignments(header):
    people, blocks = header["people"], header["blocks"]
    holders, stations = header["station_people"], header["stations"]
    for block_order in permutations(blocks):
        pb = dict(zip(people, block_order))
        for station_order in permutations(stations):
            ps = dict(zip(holders, station_order))
            yield pb, ps


def clue_holds(clue, pb, ps, header):
    k, a = clue["kind"], clue["args"]
    if k in ("ignore", "unknown"):
        return True
    if k == "person_block_eq": return pb[a["person"]] == a["block"]
    if k == "person_block_ne": return pb[a["person"]] != a["block"]
    if k == "person_station_eq": return ps[a["person"]] == a["station"]
    if k == "person_station_ne": return ps[a["person"]] != a["station"]
    if k == "station_holder_is": return ps.get(a["person"]) == a["station"]
    if k == "station_holder_not": return ps.get(a["person"]) != a["station"]
    if k == "person_before_person": return header["blocks"].index(pb[a["first"]]) < header["blocks"].index(pb[a["second"]])
    if k == "person_immediately_before": return header["blocks"].index(pb[a["second"]]) == header["blocks"].index(pb[a["first"]]) + 1
    if k == "person_between":
        pos = {p: header["blocks"].index(pb[p]) for p in pb}
        m, x, y = (pos[a[q]] for q in ("middle", "endpoint_a", "endpoint_b"))
        return x < m < y or y < m < x
    if k == "station_before_person":
        holder = next((p for p, s in ps.items() if s == a["station"]), None)
        return holder is not None and header["blocks"].index(pb[holder]) < header["blocks"].index(pb[a["person"]])
    if k == "person_before_station":
        holder = next((p for p, s in ps.items() if s == a["station"]), None)
        return holder is not None and header["blocks"].index(pb[a["person"]]) < header["blocks"].index(pb[holder])
    raise ValueError(f"unsupported clue kind: {k}")


def find_solutions(header, clues, limit=None):
    active = [c for c in clues if c["kind"] not in ("ignore", "unknown")]
    found = []
    for pb, ps in assignments(header):
        if all(clue_holds(c, pb, ps, header) for c in active):
            out = {p: {"block": pb[p]} for p in header["people"]}
            for p in header["station_people"]: out[p]["station"] = ps[p]
            found.append(out)
            if limit is not None and len(found) >= limit: break
    return found


def minimal_conflict(header, clues):
    """Deletion-minimal unsatisfiable set of extracted asserted clues."""
    core = [c for c in clues if c["kind"] not in ("ignore", "unknown")]
    if find_solutions(header, core, limit=1):
        return []
    i = 0
    while i < len(core):
        trial = core[:i] + core[i + 1:]
        if not find_solutions(header, trial, limit=1): core = trial
        else: i += 1
    return [c["source"] for c in core]


def solve(header, clues):
    # An unparsed statement may contain a real constraint. Do not prove a case
    # from an incomplete extraction; higher-budget repair can resolve unknowns.
    unknowns = [c for c in clues if c["kind"] == "unknown"]
    if unknowns:
        return {"case": "unknown", "reason": f"{len(unknowns)} statement(s) need extraction repair"}
    sols = find_solutions(header, clues)
    if not sols:
        core = minimal_conflict(header, clues)
        if core: return {"case": "inconsistent", "conflicts": core}
        return {"case": "unknown", "reason": "no solution from extracted asserted clues; no source-grounded conflict"}
    if len(sols) == 1: return {"case": "unique", "assignment": sols[0]}
    return {"case": "ambiguous", "assignments": sols}
