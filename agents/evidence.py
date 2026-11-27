def citation_label(doc: dict) -> str:
    section_ref = doc.get("section_ref", "")
    if section_ref and section_ref != "header":
        return f"{doc['source']}, Section {section_ref}"
    return f"{doc['source']}, Document header"


def format_context(docs: list[dict]) -> str:
    blocks = [f"[Source: {citation_label(d)}]\n{d['content']}" for d in docs]
    return "\n\n---\n\n".join(blocks)