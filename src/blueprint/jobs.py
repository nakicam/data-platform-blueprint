"""Jobs as configuration: a YAML task graph, validated and run in dependency order.

Modelled on the idea of declarative job bundles (tasks, depends_on, params) without any vendor runtime.
See docs/adr/ADR-006-jobs-as-configuration.md
"""
from pathlib import Path
from typing import Callable

import yaml


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def order(job: dict) -> list[str]:
    """Topological order; raises ValueError on duplicate keys, unknown dependencies or cycles."""
    tasks = {}
    for t in job["tasks"]:
        if t["key"] in tasks:
            raise ValueError(f"duplicate task: {t['key']}")
        tasks[t["key"]] = t
    for t in tasks.values():
        for d in t.get("depends_on", []):
            if d not in tasks:
                raise ValueError(f"task {t['key']} depends on unknown task {d}")
    result: list[str] = []
    pending = {k: set(t.get("depends_on", [])) for k, t in tasks.items()}
    while pending:
        ready = sorted(k for k, deps in pending.items() if not deps)
        if not ready:
            raise ValueError(f"dependency cycle among: {sorted(pending)}")
        for k in ready:
            result.append(k)
            del pending[k]
        for deps in pending.values():
            deps.difference_update(ready)
    return result


def run(job: dict, registry: dict[str, Callable[..., object]], ctx: dict) -> dict[str, object]:
    """Run tasks in order. A failing task stops the run; downstream tasks never start."""
    by_key = {t["key"]: t for t in job["tasks"]}
    for t in by_key.values():
        if t["type"] not in registry:
            raise ValueError(f"unknown task type: {t['type']}")
    results: dict[str, object] = {}
    for key in order(job):
        t = by_key[key]
        results[key] = registry[t["type"]](ctx, **t.get("params", {}))
    return results
