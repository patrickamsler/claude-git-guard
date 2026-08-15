"""Tests for the git-guard PreToolUse hook.

The hook lives at `.claude/hooks/git-guard.py` — a dotted directory and a
hyphenated filename — so it cannot be imported by name and is loaded by path.
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "git-guard.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("git_guard", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


git_guard = _load_hook()


def subs(command):
    return list(git_guard.git_subcommands(command))


# --- parser -----------------------------------------------------------------

def test_plain_invocation():
    assert subs("git status") == ["status"]


def test_compound_command():
    """The case a prefix-matching `if: Bash(git *)` filter would have missed."""
    assert subs('cd sub && git commit -m "wip"') == ["commit"]


def test_pipeline():
    assert subs("git log | head") == ["log"]


def test_subshell():
    assert subs("(git push)") == ["push"]


def test_value_consuming_global_option():
    assert subs("git -c user.name=x commit") == ["commit"]


def test_flag_option_does_not_consume_value():
    assert subs("git --no-pager log") == ["log"]


def test_absolute_path_to_git():
    assert subs("/usr/bin/git reset") == ["reset"]


def test_quoted_argument_containing_git():
    assert subs('git commit -m "git push later"') == ["commit"]


def test_unbalanced_quotes_fails_closed():
    assert "commit" in subs('git commit -m "oops')


def test_bare_git_yields_nothing():
    assert subs("git") == []


def test_multiple_invocations():
    assert subs("git status && git push") == ["status", "push"]


# --- end to end -------------------------------------------------------------

def _run(command):
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
    )


def test_denies_push():
    result = _run("git push origin main")
    assert result.returncode == 0
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "git push" in decision["permissionDecisionReason"]


def test_allows_status():
    result = _run("git status")
    assert result.returncode == 0
    assert result.stdout == ""


# --- command matrix ---------------------------------------------------------
# One test per row of command-matrix.txt. The file records what the hook
# ACTUALLY returns, gaps and false positives included, so every row is expected
# to pass as written — a failure means the hook's behaviour moved.

MATRIX_PATH = Path(__file__).resolve().parent / "command-matrix.txt"

ROW = re.compile(r"^(ALLOWED|DENIED)\s+(.*?)(?:\s*#.*)?$")


def _parse_matrix():
    """Return (rows, malformed) — rows are (lineno, expected, command) triples."""
    rows, malformed = [], []
    for lineno, line in enumerate(MATRIX_PATH.read_text().splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        match = ROW.match(line)
        if not match or not match.group(2):
            malformed.append(f"line {lineno}: {line!r}")
            continue
        rows.append((lineno, match.group(1), match.group(2)))
    return rows, malformed


MATRIX_ROWS, MATRIX_MALFORMED = _parse_matrix()


def _decision(command):
    """ALLOWED or DENIED — the verdict the hook returns for `command`."""
    stdout = _run(command).stdout.strip()
    if not stdout:
        return "ALLOWED"
    decision = json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]
    return "DENIED" if decision == "deny" else "ALLOWED"


def test_matrix_parses():
    """A matrix row that silently fails to parse would never be checked."""
    assert MATRIX_MALFORMED == []
    assert MATRIX_ROWS


@pytest.mark.parametrize(
    "expected,command",
    [pytest.param(exp, cmd, id=f"L{lineno}:{cmd}") for lineno, exp, cmd in MATRIX_ROWS],
)
def test_matrix_row(expected, command):
    assert _decision(command) == expected
