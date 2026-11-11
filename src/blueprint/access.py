"""Render and validate an access policy. See docs/adr/ADR-002-access-as-code.md"""
from pathlib import Path

import yaml

ALLOWED = {"read"}
SCHEMAS = {"raw", "enriched", "product"}


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["roles"]


def validate(roles: dict) -> list[str]:
    errors = []
    for role, grants in roles.items():
        for schema, level in grants.items():
            if schema not in SCHEMAS:
                errors.append(f"{role}: unknown schema {schema}")
            if level not in ALLOWED:
                errors.append(f"{role}: unsupported level {level} on {schema}")
        if role == "analysts" and "raw" in grants:
            errors.append("analysts must never read raw")
    return errors


def render(roles: dict) -> list[str]:
    return [
        f"GRANT USAGE, SELECT ON SCHEMA {schema} TO {role};"
        for role, grants in sorted(roles.items())
        for schema in sorted(grants)
    ]
