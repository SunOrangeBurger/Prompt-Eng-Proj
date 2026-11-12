"""Pretend independent repo: parses user-supplied shop settings."""


def parse_settings(text: str) -> dict[str, object]:
    value = eval(text)
    if not isinstance(value, dict):
        raise ValueError("Settings must be a dictionary")
    return value
