#!/usr/bin/env python3
"""
gate_loop.py — Generate-validate-retry loop for Platinum & Bramble notes.

WHAT THIS IS
------------
The automated half of the validation gate. It wraps the deterministic validator
(gate.py) around a local model served by Ollama:

    model generates a note
        -> gate.py checks structure
            -> on FAIL: the exact errors are fed back to the model, which
               regenerates (looping until PASS or max tries)
            -> on PASS: you get a valid note plus a short list of invented
               wikilinks (new canon) to approve or reject.

The structural gate is deterministic and automatic. The CANON approval is human
and irreducible (invented fiction has no ground truth — see build conclusion #3).
This script enforces the first and surfaces the second.

It imports the SAME validator gate.py uses, so there is one source of truth for
structure. If you change a template, you change gate.py's SCHEMAS; this loop
inherits it automatically.

REQUIREMENTS
------------
    - Python 3.9+
    - gate.py in the same directory (or importable on PYTHONPATH)
    - Ollama running locally with your model pulled
    - The `requests` library  (pip install requests)   [stdlib urllib fallback
      is included, so requests is optional]

QUICK START
-----------
    # 1. make sure Ollama is up and the model is pulled:
    ollama list
    # 2. generate a Region note named "The Marsh of Knor":
    python3 gate_loop.py region "The Marsh of Knor"
    # 3. with extra guidance for the model:
    python3 gate_loop.py npc "Old Hedda" --brief "the innkeeper's wary mother"
    # 4. save the result straight to a file (only written if it PASSES):
    python3 gate_loop.py settlement "Greywater" --out ./Greywater.md

EDIT TWO LINES FOR YOUR STACK: OLLAMA_URL and MODEL_NAME are defined right
below the imports.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error

# EDIT THESE TWO LINES FOR YOUR STACK >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
OLLAMA_URL = "http://localhost:11434"      # <-- EDIT if Ollama is elsewhere
MODEL_NAME = "qwen2.5:14b-instruct-q5_K_M"               # <-- EDIT to your exact model tag
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# --- import the validator (single source of truth for structure) ------------ #
try:
    import gate as gate_mod
except ImportError:
    sys.stderr.write(
        "error: gate.py must be in the same directory as gate_loop.py "
        "(or on PYTHONPATH).\n")
    raise SystemExit(2)


MAX_TRIES_DEFAULT = 4


# --------------------------------------------------------------------------- #
# MODEL CALL  (Ollama /api/chat)
# --------------------------------------------------------------------------- #
def call_model(messages: list[dict], temperature: float = 0.4,
               timeout: int = 600) -> str:
    """
    Send a chat request to Ollama and return the assistant's text.
    Uses stdlib urllib so no third-party dependency is required.
    `messages` is a list of {"role": ..., "content": ...}.
    """
    url = f"{OLLAMA_URL.rstrip('/')}/api/chat"
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Could not reach Ollama at {url}. Is it running, and is "
            f"MODEL_NAME ('{MODEL_NAME}') pulled? Underlying error: {e}") from e
    # Ollama /api/chat returns {"message": {"role": "...", "content": "..."}}
    msg = body.get("message", {})
    return msg.get("content", "")


# --------------------------------------------------------------------------- #
# EXTRACT the note from a chatty reply
# --------------------------------------------------------------------------- #
def extract_note(reply: str) -> str:
    """
    Pull the actual note out of the model's reply. The model may wrap it in a
    ```markdown ... ``` fence and/or surround it with commentary. Strategy:
      1. If there's a fenced block, take the largest fenced block.
      2. Otherwise, take from the first '---' (frontmatter start) to the end.
      3. Otherwise, return the whole reply (gate will reject it, loop continues).
    """
    # 1. fenced code blocks
    fences = re.findall(r"```(?:markdown|md|yaml)?\s*\n(.*?)```", reply,
                        flags=re.DOTALL)
    if fences:
        return max(fences, key=len).strip()
    # 2. from first frontmatter marker
    idx = reply.find("\n---")
    if reply.lstrip().startswith("---"):
        return reply.strip()
    if idx != -1:
        # back up to the '---' itself
        start = reply.rfind("---", 0, idx + 4)
        if start != -1:
            return reply[start:].strip()
    # 3. give up; return as-is
    return reply.strip()


# --------------------------------------------------------------------------- #
# PROMPT BUILDING  (schema embedded from gate.py — never hand-copied)
# --------------------------------------------------------------------------- #
def build_system_prompt(note_type: str) -> str:
    """
    Build the system prompt for a given note type, embedding the EXACT required
    sections and allowed frontmatter keys from gate.py's schema. This guarantees
    the model is told to produce precisely what the gate will check.
    """
    schema = gate_mod.SCHEMAS[note_type]
    fm_keys = schema["frontmatter"]
    sections = schema["sections"]
    tag_rule = ""
    if note_type in gate_mod.TAG_REQUIRED_TYPES:
        req = gate_mod.TAG_REQUIRED_TYPES[note_type]
        tag_rule = (f"\n- The `tags:` list MUST include at least one of: "
                    f"{', '.join(req)}.")

    fm_lines = "\n".join(f"  {k}:" for k in fm_keys)
    sec_lines = "\n".join(f"  ## {s}" for s in sections)

    return f"""You are the Worldbuilder for a Cairn 2e dark-folktale campaign \
called Platinum & Bramble. You author vault notes that must pass an automated \
structural gate EXACTLY. Output ONLY the note as Markdown — no preamble, no \
explanation, no code fences.

GROUNDING (from the Campaign Constitution):
- Mystery over explanation; folklore over history; adventure over lore.

CANON ANCHORS — these are FIXED. Never contradict or scramble them:
- THE MAP, west to east: the Holdlands (the ordered North) — then THE SEAM
  (the border country, where the campaign is set) — then the ASHWOOD (the old
  Eastern forest). So: Holdlands = WEST, Ashwood = EAST, the Seam is BETWEEN.
- "East of the Seam" means toward/into the Ashwood (wild, mysterious, dangerous).
  "West of the Seam" means toward the Holdlands (settled, ordered North). Do not
  confuse these. If you place something east, it is near the wild wood, not the
  North; keep its described character consistent with its side.
- Whisperbridge is the chief crossing, a ford-inn ON the Seam.
- The Ford-Wardens are TRUCE-KEEPERS, not a garrison or army — they hold the
  peace by custom and reputation, with no standing force or walls. Never write
  them as soldiers or a military unit.
- The Ashwood is the campaign's central MYSTERY and is deliberately unresolved.
- Do NOT invent played-session history (e.g. "Session 3: the party did X").
  No sessions have been played unless the request says so.

- Build THIN. Invent only what the note needs to be usable; leave most of the
  world open for play. A good note plants hooks and questions, not answers. Do
  NOT generate exhaustive sub-locations, named sub-factions, cults, deities,
  ghost NPCs, or backstory unless asked — a few evocative, open elements beat a
  dense gazetteer. When in doubt, write less and leave a "Future Note
  Opportunities" pointer instead.
- PROTECT THE EAST. The Eastern forest (the Ashwood, "east of the Seam") is the
  campaign's central mystery and is DELIBERATELY kept thin and unresolved, even
  for the GM. Do NOT invent its deep history, its rulers, what dwells in it, or
  what power stirs there. If a note touches the East, keep it sparse, uncertain,
  and from an outsider's limited view; leave the truth open.
- Tone: grounded and grim with heroic counterweight, mythic only at the edges —
  not generic dark-fantasy, not a horror theme park. Rationed strangeness.
- Use established canon names where relevant (the Seam, Whisperbridge, the
  Holdlands, the Ashwood, the Ford-Wardens, the Wrong Cold). NEVER contradict
  established canon. Any NEW name or detail you invent is a DRAFT for GM
  approval, not final canon.
- Values must be lowercase: status (e.g. active), canon_state (e.g. draft).
- Leave fields BLANK rather than writing "unknown"/"none"/"tbd" — the gate
  rejects placeholder words. An empty `first_appearance:` is correct; `unknown`
  is not.
- In `relationships:`, reference other notes as [[wikilinks]], never bare names.
- You may OMIT optional sections entirely if a thin note doesn't need them. Do
  not invent inhabitants, factions, cults, or deities just to fill a section.
- Do NOT emit empty GM-ONLY blocks. Only use
  <!-- GM-ONLY:START --> ... <!-- GM-ONLY:END --> when there is real GM-only
  content to put between them.

HARD STRUCTURAL RULES (the gate rejects any violation):
- The note is type '{note_type}'.
- Frontmatter is YAML between two '---' lines, FIRST line of the file.
- Frontmatter must contain EXACTLY these keys, no others (this is a CLOSED set):
{fm_lines}
- NEVER put a `summary:` key in frontmatter. The summary is a body section.
- `type:` must be "{note_type}". `name:` must not be empty.
- `created:` must be blank OR a real past date as YYYY-MM-DD. NEVER invent a date;
  prefer leaving it blank.
- The body must contain ALL of these section headers, spelled EXACTLY:
{sec_lines}
- You MAY add extra sections beyond these, but never omit a required one.
- Wrap any GM-only / spoiler content in <!-- GM-ONLY:START --> and
  <!-- GM-ONLY:END --> so it can be stripped before player-facing use.
- Keep every '## Summary' as a standalone paragraph (it is the retrieval anchor).{tag_rule}

Produce the complete note now."""


def build_retry_message(errors: list[str]) -> str:
    """Feed the gate's exact errors back to the model for correction."""
    bullet = "\n".join(f"- {e}" for e in errors)
    return (
        "The note you produced FAILED structural validation with these errors:\n"
        f"{bullet}\n\n"
        "Fix EVERY error and output the COMPLETE corrected note again. Output only "
        "the Markdown note, no commentary, no code fences. Do not drop any content "
        "that was already correct; only fix what the errors call out.")


# --------------------------------------------------------------------------- #
# CANON-APPROVAL SURFACE  (the human floor)
# --------------------------------------------------------------------------- #
def invented_wikilinks(note_text: str) -> list[str]:
    """
    Return the distinct wikilink targets in the note, EXCLUDING open folder
    stubs ([[Foo/]]). These are the candidate pieces of invented canon the GM
    must approve or reject. (We don't try to know which already exist here —
    that's for the GM eye or a vault cross-check; the point is to surface them.)
    """
    seen = []
    for m in re.finditer(r"\[\[([^\]]+)\]\]", note_text):
        target = m.group(1).split("|")[0].strip()
        if target.endswith("/"):
            continue
        if target not in seen:
            seen.append(target)
    return seen


# --------------------------------------------------------------------------- #
# THE LOOP
# --------------------------------------------------------------------------- #
def generate_valid_note(note_type: str, name: str, brief: str = "",
                        max_tries: int = MAX_TRIES_DEFAULT,
                        verbose: bool = True):
    """
    Run the generate-validate-retry loop. Returns (ok, note_text, result, tries).
    """
    if note_type not in gate_mod.SCHEMAS:
        raise SystemExit(f"Unknown note type '{note_type}'. Known: "
                         f"{', '.join(sorted(gate_mod.SCHEMAS))}.")

    system = build_system_prompt(note_type)
    user = f'Create the {note_type} note titled "{name}".'
    if brief:
        user += f"\n\nGuidance: {brief}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    last_text = ""
    last_result = None
    last_conn_error = None
    import time
    for attempt in range(1, max_tries + 1):
        if verbose:
            print(f"  · attempt {attempt}/{max_tries}: generating…",
                  file=sys.stderr)
        try:
            reply = call_model(messages)
        except Exception as e:
            # A model/connection failure is a FAILED ATTEMPT, not a crash. Record
            # it and retry (with a short backoff) rather than dying on attempt 1 —
            # the server may be loading the model or briefly overloaded.
            last_conn_error = str(e)
            if verbose:
                print(f"  · model call failed: {e}", file=sys.stderr)
                if attempt < max_tries:
                    print("  · backing off 3s and retrying…", file=sys.stderr)
            if attempt < max_tries:
                time.sleep(3)
            continue
        note_text = extract_note(reply)
        result = gate_mod.validate(note_text, note_type=note_type)
        last_text, last_result = note_text, result

        if result.ok:
            if verbose:
                print(f"  · PASSED on attempt {attempt}.", file=sys.stderr)
            return True, note_text, result, attempt, None

        if verbose:
            print(f"  · failed ({len(result.errors)} error(s)); feeding back.",
                  file=sys.stderr)
        # Append the model's own (extracted) note and the correction request,
        # preserving conversation so it edits rather than starts over.
        messages.append({"role": "assistant", "content": note_text})
        messages.append({"role": "user",
                         "content": build_retry_message(result.errors)})

    return False, last_text, last_result, max_tries, last_conn_error


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate a Platinum & Bramble note via local model, "
                    "looping until it passes the structural gate.")
    ap.add_argument("type", help="Note type (e.g. region, npc, settlement, "
                                  "faction, mystery, character, item, quest…).")
    ap.add_argument("name", help='Note title, e.g. "The Marsh of Knor".')
    ap.add_argument("--brief", default="", help="Extra guidance for the model.")
    ap.add_argument("--max-tries", type=int, default=MAX_TRIES_DEFAULT)
    ap.add_argument("--out", help="Write the note here ONLY if it passes.")
    ap.add_argument("--quiet", action="store_true", help="Suppress progress.")
    args = ap.parse_args(argv)

    if args.max_tries < 1:
        sys.stderr.write("error: --max-tries must be at least 1.\n")
        return 2

    ok, note_text, result, tries, conn_error = generate_valid_note(
        args.type.lower(), args.name, brief=args.brief,
        max_tries=args.max_tries, verbose=not args.quiet)

    print("\n" + "=" * 70)
    if ok:
        print(f"PASS — valid {args.type} note '{args.name}' in {tries} attempt(s).")
    elif result is None and conn_error:
        # Every attempt failed to reach the model — show the friendly message,
        # not a traceback.
        print(f"FAIL — could not reach the model after {tries} attempt(s).")
        print(f"  Last error: {conn_error}")
        print("  Check that Ollama is running and MODEL_NAME is a model that")
        print("  loads on your machine (see `ollama list` / `ollama ps`).")
        print("=" * 70 + "\n")
        return 1
    else:
        print(f"FAIL — could not produce a valid note in {tries} attempt(s).")
        if result is not None and result.errors:
            print("Remaining errors:")
            for e in result.errors:
                print(f"  ✗ {e}")
        if conn_error:
            print(f"  (note: at least one attempt also had a model error: {conn_error})")
    print("=" * 70 + "\n")

    if note_text:
        print(note_text)

    # Canon-approval surface
    links = invented_wikilinks(note_text)
    if links:
        print("\n" + "-" * 70)
        print("CANON TO APPROVE — wikilinks the model referenced (new or existing):")
        for l in links:
            print(f"  • [[{l}]]")
        print("Review these: approve real ones, reject/rename invented ones that")
        print("shouldn't become canon. The gate checks STRUCTURE; truth is yours.")
        print("-" * 70)

    if args.out:
        if ok:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(note_text.rstrip("\n") + "\n")
            print(f"\nWrote {args.out}")
        else:
            print(f"\nNOT written to {args.out} (did not pass).")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())