import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ["OPENROUTER_BASE_URL"],
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = os.environ["MODEL"]


CLUE_ARGS = {
    "person_block_eq": ("person", "block"),
    "person_block_ne": ("person", "block"),
    "person_station_eq": ("person", "station"),
    "person_station_ne": ("person", "station"),
    "station_holder_is": ("station", "person"),
    "station_holder_not": ("station", "person"),
    "person_before_person": ("first", "second"),
    "person_immediately_before": ("first", "second"),
    "person_between": ("middle", "endpoint_a", "endpoint_b"),
    "station_before_person": ("station", "person"),
    "person_before_station": ("person", "station"),
    "ignore": (),
    "unknown": (),
}



def clue_response_schema(statement_ids, header):
    people = header["people"]
    blocks = header["blocks"]
    stations = header["stations"]
    holders = header["station_people"]

    variants = []

    for kind, arg_names in CLUE_ARGS.items():
        args_properties = {}

        for name in arg_names:
            if name == "block":
                allowed_values = blocks
            elif name == "station":
                allowed_values = stations
            elif kind in {
                "person_station_eq", "person_station_ne",
                "station_holder_is", "station_holder_not",
            }:
                allowed_values = holders
            else:
                allowed_values = people

            args_properties[name] = {
                "type": "string",
                "enum": allowed_values,
            }

        variants.append({
            "type": "object",
            "properties": {
                "statement_id": {
                    "type": "integer",
                    "enum": statement_ids,
                },
                "kind": {"type": "string", "enum": [kind]},
                "args": {
                    "type": "object",
                    "properties": args_properties,
                    "required": list(arg_names),
                    "additionalProperties": False,
                },
            },
            "required": ["statement_id", "kind", "args"],
            "additionalProperties": False,
        })

    return {
        "type": "object",
        "properties": {
            "clues": {
                "type": "array",
                "minItems": len(statement_ids),
                "maxItems": len(statement_ids),
                "items": {"anyOf": variants},
            },
        },
        "required": ["clues"],
        "additionalProperties": False,
    }


def call_model(messages, item_id, statement_ids, header):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=1.0,
        top_p=0.95,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "clue_extraction",
                "strict": True,
                "schema": clue_response_schema(statement_ids, header),
            },
        },
        extra_body={
            "reasoning": {"enabled": False},
            "provider": {"require_parameters": True},
        },
        extra_headers={"X-Item-Id": item_id},
    )
    return response.choices[0].message.content
