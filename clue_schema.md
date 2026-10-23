# Generic clue extraction schema (M2)

The extractor emits one JSON object:
{
  "clues": [
    {
      "statement_id": 1,
      "source": "verbatim statement, excluding a hedge opener if present",
      "kind": "person_block_eq",
      "args": {"person": "A", "block": "09:00"}
    }
  ]
}

Every body statement must appear exactly once in `clues`, including ignored or uncertain statements. `source` must be the exact corresponding body line after optionally removing only a leading hedge/restatement wrapper; do not paraphrase it. `statement_id` is the 1-based order of the body statement.

Kinds and arguments:
- `person_block_eq`: `person`, `block`
- `person_block_ne`: `person`, `block`
- `person_station_eq`: `person`, `station` (person must be a station-holder)
- `person_station_ne`: `person`, `station` (person must be a station-holder)
- `station_holder_is`: `station`, `person`
- `station_holder_not`: `station`, `person`
- `person_before_person`: `first`, `second`
- `person_immediately_before`: `first`, `second`
- `person_between`: `middle`, `endpoint_a`, `endpoint_b` (strictly between; endpoints may occur in either order)
- `station_before_person`: `station`, `person`
- `person_before_station`: `person`, `station`
- `ignore`: `reason` (no current-roster constraint asserted)
- `unknown`: `reason` (meaning cannot be safely mapped to the schema)

Interpretation:
- Blocks have a total order given by the header.
- `person_immediately_before` means the second person occupies the next block after the first.
- `person_between` means position(endpoint_a) < position(middle) < position(endpoint_b), OR the reverse; adjacency is not implied.
- `station_before_person` compares the block of the station-holder with the named person's block.
- `person_before_station` is the converse relation.
- Only statements about the current roster create constraints. Past arrangements, counterfactuals, requests that were rejected, and mere reports of uncertainty/disagreement do not assert a current assignment.
- Hedges such as "I'm fairly sure" do not weaken an assertion.
- Restatements are separate source statements, even when logically redundant.
- Never infer a clue from world knowledge or from other statements.
