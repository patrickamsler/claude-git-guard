#!/usr/bin/env python3
"""PreToolUse hook: block any git subcommand that changes repo state or history."""
import json
import shlex
import sys

# Allowlist: everything NOT listed here is denied.
READ_ONLY = {
    "status", "log", "diff", "show", "blame", "add", "fetch", "remote",
    "ls-files", "ls-tree", "rev-parse", "rev-list", "describe", "shortlog",
    "show-ref", "for-each-ref", "cat-file", "symbolic-ref", "check-ignore",
    "grep", "whatchanged", "difftool", "version", "help",
}

# git global options that consume the following token as their value
OPTS_WITH_VALUE = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def git_subcommands(command: str):
    """Yield the subcommand of every `git ...` invocation in a shell command line."""
    try:
        lexer = shlex.shlex(command, punctuation_chars=True, posix=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:  # unbalanced quotes -> fail closed on a naive split
        tokens = command.replace("(", " ").replace(")", " ").split()

    i = 0
    while i < len(tokens):
        if tokens[i].rsplit("/", 1)[-1] == "git":
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 2 if tokens[i] in OPTS_WITH_VALUE else 1
            if i < len(tokens):
                yield tokens[i]
        i += 1


def deny(reason: str):
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}, sys.stdout)
    sys.exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    for sub in git_subcommands(command):
        if sub not in READ_ONLY:
            deny(
                f"Blocked by project policy: 'git {sub}' changes repository state "
                "or history. Committing, pushing, rebasing and resetting are done "
                "by the developer. Stage with 'git add' and propose a commit "
                "message instead."
            )
    sys.exit(0)


if __name__ == "__main__":
    main()
