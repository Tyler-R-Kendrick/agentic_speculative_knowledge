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
    "observed_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "asserted_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "effective_from": {"@type": "Optional", "@class": "xsd:dateTime"},
    "effective_to": {"@type": "Optional", "@class": "xsd:dateTime"},
    "created_at": "xsd:dateTime",
    "verified_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "superseded_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "source_file": {"@type": "Optional", "@class": "xsd:string"},
    "source_commit": {"@type": "Optional", "@class": "xsd:string"},
    "source_branch": {"@type": "Optional", "@class": "xsd:string"},
    "source_terminus_commit": {"@type": "Optional", "@class": "xsd:string"},
    "source_terminus_branch": {"@type": "Optional", "@class": "xsd:string"},
    "session_id": {"@type": "Optional", "@class": "xsd:string"},
    "task_id": {"@type": "Optional", "@class": "xsd:string"},
    "claim_ids": {"@type": "Optional", "@class": "xsd:string"},
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
    "observed_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "asserted_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "effective_from": {"@type": "Optional", "@class": "xsd:dateTime"},
    "effective_to": {"@type": "Optional", "@class": "xsd:dateTime"},
    "verified_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "superseded_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "source_file": {"@type": "Optional", "@class": "xsd:string"},
    "source_commit": {"@type": "Optional", "@class": "xsd:string"},
    "source_branch": {"@type": "Optional", "@class": "xsd:string"},
    "generating_model_id": {"@type": "Optional", "@class": "xsd:string"},
    "generation_run_id": {"@type": "Optional", "@class": "xsd:string"},
    "prompt_template_id": {"@type": "Optional", "@class": "xsd:string"},
    "policy_version": {"@type": "Optional", "@class": "xsd:string"},
    "extracted_at": "xsd:dateTime",
}

INFERENCE_NODE_SCHEMA = {
    "@type": "Class",
    "@id": "InferenceNode",
    "inference_id": "xsd:string",
    "text": "xsd:string",
    "status": "xsd:string",
    "truth_status": "xsd:string",
    "forecast_status": {"@type": "Optional", "@class": "xsd:string"},
    "inference_mode": "xsd:string",
    "generation_strategy": "xsd:string",
    "generator": "xsd:string",
    "confidence": "xsd:decimal",
    "verification_state": "xsd:string",
    "observed_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "asserted_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "inferred_at": "xsd:dateTime",
    "effective_from": {"@type": "Optional", "@class": "xsd:dateTime"},
    "effective_to": {"@type": "Optional", "@class": "xsd:dateTime"},
    "about_time": {"@type": "Optional", "@class": "xsd:string"},
    "forecast_horizon": {"@type": "Optional", "@class": "xsd:string"},
    "retrodiction_window": {"@type": "Optional", "@class": "xsd:string"},
    "verified_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "superseded_at": {"@type": "Optional", "@class": "xsd:dateTime"},
    "source_branch": "xsd:string",
    "source_commit": "xsd:string",
    "model_id": "xsd:string",
    "prompt_template_id": "xsd:string",
    "policy_version": "xsd:string",
    "ranking_score": {"@type": "Optional", "@class": "xsd:decimal"},
    "ranking_model_id": {"@type": "Optional", "@class": "xsd:string"},
    "ranking_run_id": {"@type": "Optional", "@class": "xsd:string"},
    "geometry_version": {"@type": "Optional", "@class": "xsd:string"},
}

FACET_RELATION_SCHEMA = {
    "@type": "Class",
    "@id": "FacetRelation",
    "relation_id": "xsd:string",
    "source_node_id": "xsd:string",
    "target_node_id": "xsd:string",
    "facet_type": "xsd:string",
    "same_proposition": "xsd:boolean",
    "shared_core_claim": {"@type": "Optional", "@class": "xsd:string"},
    "directionality": "xsd:string",
    "created_at": "xsd:dateTime",
    "created_by": "xsd:string",
    "source_inference_id": {"@type": "Optional", "@class": "xsd:string"},
    "provenance_commit": "xsd:string",
    "ranking_model_id": "xsd:string",
    "ranking_run_id": "xsd:string",
    "geometry_version": {"@type": "Optional", "@class": "xsd:string"},
    "relatedness_score": "xsd:decimal",
    "distance_score": "xsd:decimal",
    "facet_strength": "xsd:decimal",
    "uncertainty": {"@type": "Optional", "@class": "xsd:decimal"},
}

ALL_SCHEMAS = [MEMORY_SCHEMA, CLAIM_SCHEMA, INFERENCE_NODE_SCHEMA, FACET_RELATION_SCHEMA]


def encode_document(data: dict) -> dict:
    doc = {}
    for key, value in data.items():
        if value is None:
            continue
        doc[key] = str(value) if not isinstance(value, (str, int, float, bool, list, dict)) else value
    return doc


def decode_document(doc: dict) -> dict:
    return {key: value for key, value in doc.items() if not key.startswith("@")}
