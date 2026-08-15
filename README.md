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

### In a single repository

Settings in `.claude/settings.json` are checked into git, so the guard applies to everyone who
works on that repo.

1. Copy [`.claude/hooks/git-guard.py`](.claude/hooks/git-guard.py) into that repo's `.claude/hooks/`.
2. Merge the `hooks` and `permissions` blocks from [`.claude/settings.json`](.claude/settings.json)
   into that repo's `.claude/settings.json`.
3. Run `/hooks` to confirm the `PreToolUse` entry is registered. Edits to settings files are
   normally picked up by Claude Code's file watcher; if the entry does not show up, restart the
   session.

`${CLAUDE_PROJECT_DIR}` expands to the repo root, so the same settings block works for every
collaborator regardless of where they cloned it.

### Globally, for every project

User settings live in `~/.claude/settings.json` (`%USERPROFILE%\.claude\settings.json` on Windows)
and apply to all your projects, without being checked into any of them.

1. Copy the hook script to your user config directory:

   ```bash
   mkdir -p ~/.claude/hooks
   cp .claude/hooks/git-guard.py ~/.claude/hooks/
   ```

2. Merge this into `~/.claude/settings.json` — replacing `/Users/you` with your actual home
   directory:

   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Bash",
           "hooks": [
             {
               "type": "command",
               "command": "python3",
               "args": ["/Users/you/.claude/hooks/git-guard.py"],
               "statusMessage": "Checking git policy…"
             }
           ]
         }
       ]
     },
     "permissions": {
       "deny": ["Edit(**/.git/**)", "Write(**/.git/**)", "Bash(gh pr merge *)"]
     }
   }
   ```

3. Run `/hooks` in any project and check that the entry appears under `User Settings`.

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
