import json
import subprocess
import sys
import tomllib
from pathlib import Path


def test_backend_lint_rejects_frontend_imports():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--stdin-filename",
            "src/probe.py",
            "--output-format",
            "json",
            "-",
        ],
        input="import frontend\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert any(message["code"] == "TID251" for message in json.loads(result.stdout))


def test_backend_has_no_workspace_or_sibling_dependencies():
    manifest = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    assert "workspace" not in manifest.get("tool", {}).get("uv", {})
    for dependency in manifest["project"]["dependencies"]:
        assert "frontend" not in dependency.lower()
        assert "file:" not in dependency
        assert "../" not in dependency
