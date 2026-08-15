#!/usr/bin/env python3
"""Re-run every row of command-matrix.txt through the hook and diff the verdicts."""
import json
import re
import subprocess
import sys

HOOK = "/Users/patrick/projects/claude-git-guard/.claude/hooks/git-guard.py"
MATRIX = "/Users/patrick/projects/claude-git-guard/tests/command-matrix.txt"

ROW = re.compile(r"^(ALLOWED|DENIED)\s+(.*?)(?:\s*#.*)?$")


def decide(command):
    payload = json.dumps({"tool_input": {"command": command}})
    proc = subprocess.run(
        [sys.executable, HOOK], input=payload, capture_output=True, text=True
    )
    if not proc.stdout.strip():
        return "ALLOWED"
    out = json.loads(proc.stdout)
    dec = out.get("hookSpecificOutput", {}).get("permissionDecision")
    return "DENIED" if dec == "deny" else "ALLOWED"


rows = mismatches = 0
for lineno, line in enumerate(open(MATRIX), 1):
    if line.startswith("#") or not line.strip():
        continue
    m = ROW.match(line.rstrip("\n"))
    if not m:
        continue
    expected, command = m.group(1), m.group(2)
    if not command:
        continue
    rows += 1
    actual = decide(command)
    if actual != expected:
        mismatches += 1
        print(f"  line {lineno}: says {expected}, hook returns {actual}: {command!r}")

print(f"\n{rows} rows checked, {mismatches} mismatches")
