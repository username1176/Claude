"""JSON-based project persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from gumbo.models import Project

PROJECTS_DIR = Path("projects")


def _ensure_dir() -> Path:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECTS_DIR


def _project_path(project_id: str) -> Path:
    return _ensure_dir() / f"{project_id}.json"


def save_project(project: Project) -> Path:
    """Persist a project to a JSON file.  Returns the file path."""
    project.touch()
    path = _project_path(project.id)
    path.write_text(project.model_dump_json(indent=2))
    return path


def load_project(project_id: str) -> Optional[Project]:
    """Load a project by its id.  Returns None when the file is missing."""
    path = _project_path(project_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return Project(**data)


def list_projects() -> list[dict[str, str]]:
    """Return a list of ``{id, name}`` dicts for every saved project."""
    _ensure_dir()
    results: list[dict[str, str]] = []
    for fname in sorted(PROJECTS_DIR.iterdir()):
        if fname.suffix != ".json":
            continue
        try:
            data = json.loads(fname.read_text())
            results.append({
                "id": data["id"],
                "name": data.get("name", fname.stem),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def delete_project(project_id: str) -> bool:
    """Delete the JSON file for the given project id."""
    path = _project_path(project_id)
    if path.exists():
        os.remove(path)
        return True
    return False
