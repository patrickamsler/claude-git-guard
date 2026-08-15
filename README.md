# claude-git-guard

A Claude Code `PreToolUse` hook that blocks any `git` subcommand which changes repository state or
history.

## What it does

`.claude/hooks/git-guard.py` inspects every Bash command Claude wants to run, tokenizes it, and
finds the subcommand of each `git` invocation on the line — including inside compound commands
(`cd sub && git commit …`), pipelines, and subshells. Anything not in the `READ_ONLY` allowlist is
denied with an explanation. The policy: Claude may inspect and stage, but committing, pushing,
rebasing and resetting stay with the developer.

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

`.claude/settings.json` in this directory is picked up automatically when you run Claude Code here.
No further action is needed for this project.

To use the guard in **another** repository:

1. Copy `.claude/hooks/git-guard.py` into that repo's `.claude/hooks/`.
2. Merge the `hooks` and `permissions` blocks from `.claude/settings.json` into that repo's
   `.claude/settings.json`.
3. Restart Claude Code — settings changes are read at session start.
4. Run `/hooks` to confirm the `PreToolUse` entry is registered.

The hook entry looks like this:

```json
{
  "type": "command",
  "command": "python3",
  "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/git-guard.py"],
  "statusMessage": "Checking git policy…"
}
```

Because `args` is present, `command` is resolved as an executable and spawned **directly, with no
shell**, and `${CLAUDE_PROJECT_DIR}` is substituted per-element as a plain string. That means paths
containing quotes, `$`, or backticks never reach a shell parser.

### Why there is no `if` filter

Claude Code supports an `"if": "Bash(git *)"` key to skip spawning the hook for non-git commands.
It is deliberately omitted here: `if` uses permission-rule **prefix** matching, so
`cd sub && git commit -m x` would not match and the hook would never run — defeating the whole point
of the script's compound-command parsing. Without the filter the hook runs on every Bash call and
exits in milliseconds when no `git` token is present.

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
