from pydantic import ValidationError

from agents.tools import ARG_MODELS, assess_impact, validate_action

UPPERCASE_FIELDS = {"priority", "level", "ticket_id"}


def describe_error(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors())
    return str(error)


def build_edited_action(action: dict, changes: dict) -> dict:
    """Apply a human's edits to a proposed action, validated like the original."""
    name = action["tool_name"]
    unknown = sorted(set(changes) - set(ARG_MODELS[name].model_fields))
    if unknown:
        raise ValueError(f"Unknown field(s) for {name}: {', '.join(unknown)}")

    cleaned = {
        key: value.strip().upper() if key in UPPERCASE_FIELDS and isinstance(value, str) else value
        for key, value in changes.items()
    }
    validated = validate_action(name, {**action["args"], **cleaned})
    impact = assess_impact(name, validated)
    return {**action, "args": validated, "risk": impact["risk"], "impact_summary": impact["summary"]}