from typing import Any, Optional


MEMORY_SCHEMA = {
    "@type": "Class",
    "@id": "Memory",
    "memory_id": "xsd:string",
    "memory_type": "xsd:string",
    "subtype": {"@type": "Optional", "@class": "xsd:string"},
    "content": "xsd:string",
    "summary": {"@type": "Optional", "@class": "xsd:string"},
    "confidence": "xsd:decimal",
    "salience": "xsd:decimal",
    "maturity": "xsd:integer",
    "access_scope": "xsd:string",
    "created_at": "xsd:dateTime",
    "session_id": {"@type": "Optional", "@class": "xsd:string"},
    "task_id": {"@type": "Optional", "@class": "xsd:string"},
}

CLAIM_SCHEMA = {
    "@type": "Class",
    "@id": "Claim",
    "claim_id": "xsd:string",
    "claim_text": "xsd:string",
    "claim_type": "xsd:string",
    "confidence": "xsd:decimal",
    "decontextualized": "xsd:boolean",
    "ambiguity_flag": "xsd:boolean",
    "extracted_at": "xsd:dateTime",
}

ALL_SCHEMAS = [MEMORY_SCHEMA, CLAIM_SCHEMA]


def encode_document(data: dict) -> dict:
    doc = {}
    for k, v in data.items():
        if v is None:
            continue
        doc[k] = str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v
    return doc


def decode_document(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if not k.startswith("@")}
