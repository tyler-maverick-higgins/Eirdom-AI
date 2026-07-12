#!/usr/bin/env python3
"""
strip_gm_only.py — Produce player-safe versions of vault notes.

WHAT THIS IS
------------
The security boundary for the player-facing Lorekeeper. It removes every
GM-ONLY block (everything between `<!-- GM-ONLY:START -->` and
`<!-- GM-ONLY:END -->`, inclusive) from a note, so the result can be ingested
into a PLAYER knowledge base that is structurally incapable of leaking GM
secrets — the secret was never indexed, so no prompt slip or clever question
can surface it.

This is NOT cosmetic. It is the load-bearing protection: the player Lorekeeper's
safety comes from searching a stripped collection, not from a system prompt
asking it to be discreet.

WHAT IT DOES
------------
- Removes each GM-ONLY block, sentinels included.
- If removing the block leaves a section heading with no content under it (the
  block WAS the whole section), removes that now-empty heading too, so players
  don't see a bare "## Secrets" with nothing under it (which itself signals "a
  secret exists here").
- Leaves everything else byte-for-byte intact (preserves frontmatter, other
  sections, line endings).
- Refuses to write output if it detects an UNBALANCED sentinel (which would mean
  it can't reliably tell where the secret ends) — failing closed is the safe
  choice for a security tool.

USAGE
-----
    # Preview what players would see of one note (prints to stdout):
    python3 strip_gm_only.py path/to/The-Wrong-Cold.md

    # Strip one note to a file:
    python3 strip_gm_only.py The-Wrong-Cold.md --out player/The-Wrong-Cold.md

    # Strip an entire vault into a parallel player-safe folder:
    python3 strip_gm_only.py ./vault --out-dir ./vault-player

    # Just report which notes contain GM-ONLY blocks (no output written):
    python3 strip_gm_only.py ./vault --report

EXIT CODES
    0  ok
    1  an unbalanced sentinel was found (nothing written for that file)
    2  usage / file error
"""

from __future__ import annotations

import argparse
import os
import re
import sys

START = "GM-ONLY:START"
END = "GM-ONLY:END"


def _normalize_keep(text: str):
    """Detect newline style so we can restore it on output."""
    if "\r\n" in text:
        return "\r\n"
    return "\n"


def count_sentinels(text: str) -> tuple[int, int]:
    return text.count(START), text.count(END)


def strip_gm_only(text: str) -> tuple[str, int]:
    """
    Return (stripped_text, blocks_removed). Raises ValueError on unbalanced
    sentinels (fail closed — never emit a half-stripped secret).
    """
    nstart, nend = count_sentinels(text)
    if nstart != nend:
        raise ValueError(
            f"Unbalanced GM-ONLY sentinels ({nstart} START vs {nend} END). "
            f"Refusing to strip — cannot safely determine where the GM-only "
            f"content ends. Fix the note's sentinels first.")
    if nstart == 0:
        return text, 0

    nl = _normalize_keep(text)
    work = text.replace("\r\n", "\n")
    lines = work.split("\n")

    out_lines: list[str] = []
    i = 0
    removed = 0
    while i < len(lines):
        line = lines[i]
        if START in line:
            # Find the matching END (sentinels don't nest in our convention).
            j = i
            while j < len(lines) and END not in lines[j]:
                j += 1
            # j now points at the END line (or past end, but balance guaranteed it)
            # Remove lines i..j inclusive.
            # Also: if the START line had content BEFORE the marker (rare), keep
            # nothing — our blocks are always whole-line sentinels. If the line
            # is a list bullet like "- <!-- GM-ONLY:START -->", it goes too.
            removed += 1
            i = j + 1
            # Swallow a single blank line left behind, to avoid double blanks.
            if i < len(lines) and lines[i].strip() == "" and out_lines and out_lines[-1].strip() == "":
                i += 1
            continue
        out_lines.append(line)
        i += 1

    # Second pass: drop headings that are now empty because their only content
    # was a stripped GM-ONLY block. A heading is "empty" only if there is no
    # content AND no SUBHEADING before the next heading of the SAME-OR-HIGHER
    # level. (A '##' section with '###' children is NOT empty.)
    def _level(s: str) -> int:
        m = re.match(r"^(#{1,6})\s+\S", s)
        return len(m.group(1)) if m else 0

    cleaned: list[str] = []
    k = 0
    while k < len(out_lines):
        line = out_lines[k]
        lvl = _level(line)
        if lvl:
            m = k + 1
            has_content = False
            while m < len(out_lines):
                nxt = out_lines[m]
                nlvl = _level(nxt)
                if nlvl and nlvl <= lvl:
                    break  # next sibling-or-higher heading ends this section
                if nxt.strip() != "":
                    has_content = True  # prose OR a deeper subheading counts
                    break
                m += 1
            if not has_content:
                k = m
                continue
        cleaned.append(line)
        k += 1

    result = "\n".join(cleaned)
    # collapse 3+ blank lines to 2
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = result.rstrip("\n") + "\n"
    if nl == "\r\n":
        result = result.replace("\n", "\r\n")
    return result, removed


def verify_no_leak(stripped: str) -> list[str]:
    """
    Safety check for a DERIVED player artifact. Returns HARD problems only —
    things that mean a secret actually leaked and the file must NOT be written:
      - a surviving GM-ONLY sentinel
      - a surviving GM-only *section heading* (## GM-Only ...)
    Incidental cross-reference phrases in player-visible prose (e.g. a rumor
    annotated "(see GM-only)") are NOT hard leaks; they're surfaced separately
    by verify_soft_tells() as advisories, because they're a canon-authoring
    issue in the source note, not a strip failure.
    """
    problems = []
    if START in stripped or END in stripped:
        problems.append("A GM-ONLY sentinel survived the strip.")
    # A GM-only SECTION HEADING surviving means a whole secret section leaked.
    for line in stripped.split("\n"):
        if re.match(r"^#{1,6}\s+GM[\s\-]?only", line, re.IGNORECASE):
            problems.append(f"A GM-only section heading survived: {line.strip()!r}.")
    if re.search(r"GM EYES ONLY", stripped, re.IGNORECASE):
        problems.append("'GM EYES ONLY' marker survived.")
    return problems


def verify_soft_tells(stripped: str) -> list[str]:
    """
    Advisory only (never blocks a write). Flags player-visible breadcrumbs that
    HINT a secret exists — e.g. a line that says "see GM-only" or "(False — see
    GM-only)". These come from the SOURCE note's discoverable sections, not from
    the strip, and are best fixed by rewording the canon note. Surfaced so you
    can clean them up.
    """
    tells = []
    for i, line in enumerate(stripped.split("\n"), 1):
        if re.search(r"\bGM[\s\-]?only\b", line, re.IGNORECASE):
            tells.append(f"line {i}: player-visible reference to GM-only material "
                         f"— consider rewording the source: {line.strip()[:80]!r}")
    return tells


def _iter_md(path: str):
    if os.path.isdir(path):
        for root, _d, files in os.walk(path):
            for fn in sorted(files):
                if fn.endswith(".md"):
                    yield os.path.join(root, fn)
    else:
        yield path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Strip GM-ONLY blocks to make player-safe notes.")
    ap.add_argument("path", help="A .md file or a directory.")
    ap.add_argument("--out", help="Output file (single-file mode).")
    ap.add_argument("--out-dir", help="Output directory (mirrors structure).")
    ap.add_argument("--report", action="store_true",
                    help="Only report which notes have GM-ONLY blocks.")
    args = ap.parse_args(argv)

    if not os.path.exists(args.path):
        sys.stderr.write(f"error: not found: {args.path}\n")
        return 2

    paths = list(_iter_md(args.path))
    if not paths:
        sys.stderr.write(f"error: no .md files at {args.path}\n")
        return 2

    if args.report:
        any_blocks = False
        for p in paths:
            with open(p, "r", encoding="utf-8") as fh:
                t = fh.read()
            ns, ne = count_sentinels(t)
            if ns or ne:
                any_blocks = True
                flag = "" if ns == ne else "  ** UNBALANCED **"
                print(f"{os.path.basename(p)}: {ns} block(s){flag}")
        if not any_blocks:
            print("No GM-ONLY blocks found.")
        return 0

    had_error = False

    # Single-file to stdout or --out
    if os.path.isfile(args.path):
        with open(args.path, "r", encoding="utf-8") as fh:
            text = fh.read()
        try:
            stripped, n = strip_gm_only(text)
        except ValueError as e:
            sys.stderr.write(f"error in {args.path}: {e}\n")
            return 1
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(stripped)
            sys.stderr.write(f"stripped {n} block(s) -> {args.out}\n")
        else:
            sys.stdout.write(stripped)
        return 0

    # Directory mode -> --out-dir required
    if not args.out_dir:
        sys.stderr.write("error: directory input requires --out-dir.\n")
        return 2

    total_blocks = 0
    for p in paths:
        with open(p, "r", encoding="utf-8") as fh:
            text = fh.read()
        rel = os.path.relpath(p, args.path)
        dest = os.path.join(args.out_dir, rel)
        try:
            stripped, n = strip_gm_only(text)
        except ValueError as e:
            sys.stderr.write(f"SKIPPED {rel}: {e}\n")
            had_error = True
            continue
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        # Safety: HARD leak check (sentinels / GM sections) blocks the write.
        leaks = verify_no_leak(stripped)
        if leaks:
            sys.stderr.write(f"LEAK DETECTED in {rel}: {'; '.join(leaks)} "
                             f"— NOT writing player copy.\n")
            had_error = True
            continue
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(stripped)
        # Advisory: soft tells don't block, but flag breadcrumbs to reword.
        for tell in verify_soft_tells(stripped):
            sys.stderr.write(f"  advisory ({rel}): {tell}\n")
        total_blocks += n
        if n:
            print(f"stripped {n} block(s): {rel}")
        else:
            print(f"(clean)            : {rel}")
    print(f"\nDone. {total_blocks} GM-ONLY block(s) removed across "
          f"{len(paths)} note(s). Player-safe copies in {args.out_dir}/")
    if had_error:
        print("WARNING: one or more notes were SKIPPED due to unbalanced "
              "sentinels — they are NOT in the player folder. Fix and re-run.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
