"""Generic model-based clue extraction prompt for M2."""
import json


def extraction_messages(item, header, statement_records=None):
    body = item["text"].split("\n\n", 1)[1]
    all_lines = [x.strip() for x in body.splitlines() if x.strip()]

    if statement_records is None:
        statement_records = [
            {"statement_id": i, "source": line}
            for i, line in enumerate(all_lines, 1)
        ]


    system = """Extract formal constraints from staffing-rota statements. Do not solve the puzzle.

Return exactly one JSON object with a top-level "clues" array. Include exactly one clue for each input statement, in original order, using its original 1-based statement_id. Do not repeat, omit, combine, or invent statements. Each clue must contain exactly the keys "statement_id", "kind", and "args".

Classify the proposition expressed by each statement(Treat each statement independently):
- Use a constraint clue when the statement asserts a constraint on the current rota.
- Use "ignore" when it does not assert a current-rota constraint, including unrelated facts, historical events, counterfactuals, declined/rejected/failed requests, and unresolved questions about whether an assignment occurred.
- Qualifiers such as "speaking from memory" or "going off roster" do not by themselves cancel an assertion. Interpret the actual proposition.
- Use the allowed clue kind that directly represents the proposition. Use "unknown" only when its meaning cannot be safely represented by any allowed kind without guessing; do not use it merely because wording is indirect or qualified. If a statement expresses a disjunction or a relationship that no single allowed clue can represent exactly, use "unknown" rather than approximating it with a different constraint.

Do not infer unstated facts. Copy names, blocks, and stations exactly from the input. Each "args" value must be a JSON object containing exactly the arguments required by its clue kind; for "ignore" and "unknown", use an empty object. Follow the allowed kinds, semantics, and output shape in the user message exactly."""

    schema = {
        "clues": [{
            "statement_id": 1,
            "kind": "one of the kinds listed below",
            "args": {},
        }]
    }

    user = f"""HEADER FACTS
People: {json.dumps(header['people'])}
Blocks in chronological order: {json.dumps(header['blocks'])}
Stations: {json.dumps(header['stations'])}
People assigned to stations: {json.dumps(header['station_people'])}

BODY STATEMENTS (statement_id is the 1-based line order):
{json.dumps(statement_records, ensure_ascii=False)}

Return JSON matching this shape:
{json.dumps(schema, ensure_ascii=False)}

Allowed kinds and exact args:
- person_block_eq: {{"person": name, "block": time}}
- person_block_ne: {{"person": name, "block": time}}
- person_station_eq: {{"person": name, "station": station}}
- person_station_ne: {{"person": name, "station": station}}
- station_holder_is: {{"station": station, "person": name}}
- station_holder_not: {{"station": station, "person": name}}
- person_before_person: {{"first": name, "second": name}}
- person_immediately_before: {{"first": name, "second": name}}
- person_between: {{"middle": name, "endpoint_a": name, "endpoint_b": name}}
- station_before_person: {{"station": station, "person": name}}
- person_before_station: {{"person": name, "station": station}}
- ignore: {{}}
- unknown: {{}}

Semantics:
- person_before_person: first's block is earlier than second's.
- person_immediately_before: second is in the block immediately following first.
- person_between: middle is strictly between the two endpoints, in either endpoint order; not necessarily adjacent.
- station_before_person: the person holding that station works earlier than the named person.
- person_before_station: the named person works earlier than the person holding that station.
- person_station_eq / person_station_ne: refer to this week's/current roster, not historical rosters.

Classification examples:
- "Nobody could remember whether Ayesha was down for the 09:00 block." -> ignore.
- "Speaking from memory, Meera is on the block directly after Samuel." -> person_immediately_before with first="Samuel", second="Meera".
- "Meera has not been put on intake." -> person_station_ne with person="Meera", station="intake".
- "Rohan is done before Ayesha starts." -> person_before_person with first="Rohan", second="Ayesha".

"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
