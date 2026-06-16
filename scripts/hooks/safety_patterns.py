"""Opt-in PreToolUse safety pattern corpus.

This module classifies risky tool payloads. It does not block, read stdin,
or write diagnostics. Runtime policy lives in pretool_dispatcher.py.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


@dataclass(frozen=True)
class SafetyFinding:
    pattern_id: str
    category: str
    severity: str
    confidence: str
    message: str
    evidence: str

    def to_record(self) -> dict[str, str]:
        return asdict(self)


_CURL_PIPE = re.compile(r"\bcurl\b[^\n|;&]*(?:\|\s*(?:sh|bash)\b)", re.IGNORECASE)
_WGET_PIPE = re.compile(r"\bwget\b[^\n|;&]*(?:\|\s*(?:sh|bash)\b)", re.IGNORECASE)
_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
    re.IGNORECASE,
)
_TOKEN_SHAPED_SECRET = re.compile(
    r"\b(?:sk|ghp|github_pat|xox[baprs]|AKIA)[A-Za-z0-9_\-]{10,}",
    re.IGNORECASE,
)

_SECRET_EXEMPT_PATH_MARKERS = (
    ".env.example",
    ".env.template",
    ".env.test",
    ".env.sample",
    "fixtures/",
    "tests/",
)
_PROTECTED_BRANCHES = {"main", "master"}


def _is_exempt_path(path: str) -> bool:
    lowered = path.replace("\\", "/").lower()
    return any(marker in lowered for marker in _SECRET_EXEMPT_PATH_MARKERS)


def classify_shell_command(command: str, *, branch: str | None = None) -> list[SafetyFinding]:
    findings: list[SafetyFinding] = []
    if _CURL_PIPE.search(command):
        findings.append(
            SafetyFinding(
                pattern_id="bash-curl-pipe-shell",
                category="shell",
                severity="high",
                confidence="medium",
                message="curl output is piped directly into a shell",
                evidence="curl|shell",
            )
        )
    if _WGET_PIPE.search(command):
        findings.append(
            SafetyFinding(
                pattern_id="bash-wget-pipe-shell",
                category="shell",
                severity="high",
                confidence="medium",
                message="wget output is piped directly into a shell",
                evidence="wget|shell",
            )
        )
    if branch in _PROTECTED_BRANCHES and re.search(r"\bgit\s+commit\b", command):
        findings.append(
            SafetyFinding(
                pattern_id="git-direct-commit-protected-branch",
                category="git",
                severity="medium",
                confidence="medium",
                message="git commit is running on a protected branch",
                evidence=f"branch={branch}",
            )
        )
    return findings


def classify_file_payload(tool_name: str, path: str, content: str | None) -> list[SafetyFinding]:
    if not content or _is_exempt_path(path):
        return []
    findings: list[SafetyFinding] = []
    if _PRIVATE_KEY.search(content):
        findings.append(
            SafetyFinding(
                pattern_id="write-private-key-material",
                category="secret",
                severity="high",
                confidence="high",
                message=f"{tool_name} payload contains private-key material",
                evidence=path,
            )
        )
    if _TOKEN_SHAPED_SECRET.search(content):
        findings.append(
            SafetyFinding(
                pattern_id="write-token-shaped-secret",
                category="secret",
                severity="medium",
                confidence="medium",
                message=f"{tool_name} payload contains a token-shaped secret",
                evidence=path,
            )
        )
    return findings


def classify_pretool_payload(payload: dict[str, Any], *, branch: str | None = None) -> list[SafetyFinding]:
    if not isinstance(payload, dict):
        return []
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return []
    if tool_name == "Bash":
        command = tool_input.get("command")
        return classify_shell_command(command, branch=branch) if isinstance(command, str) else []
    if tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        content = tool_input.get("content")
        return classify_file_payload(tool_name, str(path), content if isinstance(content, str) else None)
    return []
