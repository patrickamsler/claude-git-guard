# claude-git-guard

A Claude Code `PreToolUse` hook that blocks any `git` subcommand which changes repository state or
history.

## What it does

[`.claude/hooks/git-guard.py`](.claude/hooks/git-guard.py) inspects the Bash command Claude wants to
run, tokenizes it, and finds the subcommand of each `git` invocation on the line — including inside
compound commands (`cd sub && git commit …`), pipelines, and subshells. Anything not in the
`READ_ONLY` allowlist is denied with an explanation. The policy: Claude may inspect and stage, but
committing, pushing, rebasing and resetting stay with the developer.

The hook is wired up in [`.claude/settings.json`](.claude/settings.json) and runs on every Bash
call.

The accompanying `permissions.deny` rules also stop Claude from editing `.git/` directly or running
`gh pr merge`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
pytest
```

The venv exists for the test suite only — see the note below.

## Configuring the Claude Code hook

To use the guard in repository:

1. Copy [`.claude/hooks/git-guard.py`](.claude/hooks/git-guard.py) into that repo's `.claude/hooks/`.
2. Merge the `hooks` and `permissions` blocks from [`.claude/settings.json`](.claude/settings.json)
   into that repo's `.claude/settings.json`.
3. Restart Claude Code — settings changes are read at session start.
4. Run `/hooks` to confirm the `PreToolUse` entry is registered.

## Notes

- **The hook runs under system `python3`, not `.venv/bin/python`.** Claude Code spawns it directly
  and knows nothing about the virtualenv. That is fine because the script imports only `json`,
  `shlex`, and `sys` from the standard library. **Do not add third-party imports to the hook** — it
  would break in every environment where the venv is not active.
- **`git add` is allowed on purpose**, so Claude can stage changes and propose a commit message for
  you to run yourself.

## Customizing

Edit the `READ_ONLY` set in `.claude/hooks/git-guard.py` to loosen or tighten the policy. Everything
not listed there is denied. If you add a global option that consumes the token after it, add it to
`OPTS_WITH_VALUE` too, or the parser will mistake that value for the subcommand.
