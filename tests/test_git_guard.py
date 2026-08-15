"""Tests for the git-guard PreToolUse hook.

The hook lives at `.claude/hooks/git-guard.py` — a dotted directory and a
hyphenated filename — so it cannot be imported by name and is loaded by path.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

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
