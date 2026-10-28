def parse_angles(text: str) -> list[float]:
    """
    Parse angles from a string like "0, 5, 10", "0 5 10" or "0;5;10".

    Mirrors scripts/GUI.py's parse_angles(); duplicated on purpose instead of
    imported, since GUI.py pulls in tkinter and is legacy UI code the backend
    shouldn't depend on.
    """
    if not text.strip():
        return []

    normalized = (
        text.replace(",", " ")
            .replace(";", " ")
            .replace("\t", " ")
            .strip()
    )
    parts = [p for p in normalized.split(" ") if p.strip()]
    return [float(p) for p in parts]
