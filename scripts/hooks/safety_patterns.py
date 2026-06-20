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
    stage: str
    source_ref: str
    risk: str
    promotion_condition: str

    def to_record(self) -> dict[str, str]:
        return asdict(self)


_CURL_PIPE = re.compile(r"\bcurl\b[^\n|;&]*(?:\|\s*(?:sh|bash)\b)", re.IGNORECASE)
_WGET_PIPE = re.compile(r"\bwget\b[^\n|;&]*(?:\|\s*(?:sh|bash)\b)", re.IGNORECASE)
_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
    re.IGNORECASE,
)
_TOKEN_SHAPED_SECRET = re.compile(
    r"\b(?:"
    r"sk[-_][A-Za-z0-9_\-]{8,}"
    r"|ghp_[A-Za-z0-9_]{10,}"
    r"|github_pat_[A-Za-z0-9_]{10,}"
    r"|xox[baprs]-[A-Za-z0-9\-]{10,}"
    r"|AKIA[A-Z0-9]{12,}"
    r")",
    re.IGNORECASE,
)
_RM_RF_BROAD_DELETE = re.compile(
    r"\brm\b(?=[^\n;&|]*-[A-Za-z]*r)(?=[^\n;&|]*-[A-Za-z]*f)"
    r"[^\n;&|]*(?:\./|\.\./|[A-Za-z0-9_.-]+/|\*)[^\s;&|]*",
    re.IGNORECASE,
)
_GIT_CLEAN_FORCE_DELETE = re.compile(
    r"\bgit\s+clean\b(?=[^\n;&|]*(?:\s-[A-Za-z]*f|\s--force\b))",
    re.IGNORECASE,
)
_ENV_SECRET_PATH = re.compile(
    r"(?:^|[/\\])\.env(?:\.local|\.production|\.secret)?$",
    re.IGNORECASE,
)
_SSH_PRIVATE_KEY_PATH = re.compile(
    r"(?:^|[/\\])\.ssh[/\\](?:id_rsa|id_ed25519|id_dsa|id_ecdsa)$",
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
_PROMOTION_CONDITION = (
    "Promotion requires live diagnostic evidence, false-positive review, "
    "replay coverage, and release-policy documentation."
)


def _is_exempt_path(path: str) -> bool:
    lowered = path.replace("\\", "/").lower()
    return any(marker in lowered for marker in _SECRET_EXEMPT_PATH_MARKERS)


def _finding(
    *,
    pattern_id: str,
    category: str,
    severity: str,
    confidence: str,
    message: str,
    evidence: str,
    source_ref: str,
    risk: str,
    promotion_condition: str = _PROMOTION_CONDITION,
    stage: str = "observe",
) -> SafetyFinding:
    return SafetyFinding(
        pattern_id=pattern_id,
        category=category,
        severity=severity,
        confidence=confidence,
        message=message,
        evidence=evidence,
        stage=stage,
        source_ref=source_ref,
        risk=risk,
        promotion_condition=promotion_condition,
    )


def classify_shell_command(command: str, *, branch: str | None = None) -> list[SafetyFinding]:
    findings: list[SafetyFinding] = []
    if _CURL_PIPE.search(command):
        findings.append(
            _finding(
                pattern_id="bash-curl-pipe-shell",
                category="shell",
                severity="high",
                confidence="medium",
                message="curl output is piped directly into a shell",
                evidence="curl|shell",
                source_ref="ref/karanb192-claude-code-hooks/README.md",
                risk="high",
            )
        )
    if _WGET_PIPE.search(command):
        findings.append(
            _finding(
                pattern_id="bash-wget-pipe-shell",
                category="shell",
                severity="high",
                confidence="medium",
                message="wget output is piped directly into a shell",
                evidence="wget|shell",
                source_ref="ref/disler-claude-code-hooks-mastery/README.md",
                risk="high",
            )
        )
    if _RM_RF_BROAD_DELETE.search(command):
        findings.append(
            _finding(
                pattern_id="shell-rm-rf-broad-delete",
                category="shell",
                severity="high",
                confidence="medium",
                message="rm -rf targets a broad local path or wildcard",
                evidence="rm-rf-broad-delete",
                source_ref="ref/karanb192-claude-code-hooks/README.md",
                risk="high",
            )
        )
    if _GIT_CLEAN_FORCE_DELETE.search(command):
        findings.append(
            _finding(
                pattern_id="git-clean-force-delete",
                category="git",
                severity="high",
                confidence="medium",
                message="git clean is running with force-delete flags",
                evidence="git-clean-force",
                source_ref="ref/disler-claude-code-hooks-mastery/README.md",
                risk="high",
            )
        )
    if branch in _PROTECTED_BRANCHES and re.search(r"\bgit\s+commit\b", command):
        findings.append(
            _finding(
                pattern_id="git-direct-commit-protected-branch",
                category="git",
                severity="medium",
                confidence="medium",
                message="git commit is running on a protected branch",
                evidence=f"branch={branch}",
                source_ref="ref/karanb192-claude-code-hooks/README.md",
                risk="medium",
            )
        )
    return findings


def classify_file_read(tool_name: str, path: str) -> list[SafetyFinding]:
    if tool_name not in {"Read", "NotebookRead"} or not path or _is_exempt_path(path):
        return []
    normalized = path.strip().strip("'\"").replace("\\", "/")
    findings: list[SafetyFinding] = []
    if _ENV_SECRET_PATH.search(normalized):
        findings.append(
            _finding(
                pattern_id="read-env-secret-path",
                category="secret",
                severity="high",
                confidence="high",
                message=f"{tool_name} targets a dotenv secret path",
                evidence=path,
                source_ref="ref/karanb192-claude-code-hooks/README.md",
                risk="high",
            )
        )
    if _SSH_PRIVATE_KEY_PATH.search(normalized):
        findings.append(
            _finding(
                pattern_id="read-ssh-private-key-path",
                category="secret",
                severity="high",
                confidence="high",
                message=f"{tool_name} targets an SSH private-key path",
                evidence=path,
                source_ref="ref/ElliotJLT-hooksmith/README.md",
                risk="high",
            )
        )
    return findings


def classify_file_payload(tool_name: str, path: str, content: str | None) -> list[SafetyFinding]:
    if not content or _is_exempt_path(path):
        return []
    findings: list[SafetyFinding] = []
    if _PRIVATE_KEY.search(content):
        findings.append(
            _finding(
                pattern_id="write-private-key-material",
                category="secret",
                severity="high",
                confidence="high",
                message=f"{tool_name} payload contains private-key material",
                evidence=path,
                source_ref="ref/karanb192-claude-code-hooks/README.md",
                risk="high",
            )
        )
    if _TOKEN_SHAPED_SECRET.search(content):
        findings.append(
            _finding(
                pattern_id="write-token-shaped-secret",
                category="secret",
                severity="medium",
                confidence="medium",
                message=f"{tool_name} payload contains a token-shaped secret",
                evidence=path,
                source_ref="ref/karanb192-claude-code-hooks/README.md",
                risk="medium",
            )
        )
    return findings


def _payload_text_values(tool_input: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("content", "new_string", "source", "cell_source"):
        value = tool_input.get(key)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(item for item in value if isinstance(item, str))
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if not isinstance(edit, dict):
                continue
            for key in ("new_string", "source", "cell_source"):
                value = edit.get(key)
                if isinstance(value, str):
                    values.append(value)
                elif isinstance(value, list):
                    values.extend(item for item in value if isinstance(item, str))
    return values


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
    if tool_name in {"Read", "NotebookRead"}:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        return classify_file_read(tool_name, str(path))
    if tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        findings: list[SafetyFinding] = []
        for content in _payload_text_values(tool_input):
            findings.extend(classify_file_payload(tool_name, str(path), content))
        return findings
    return []
