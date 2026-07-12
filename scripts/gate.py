#!/usr/bin/env python3
"""
gate.py — Deterministic structural validator for the Platinum & Bramble vault.

WHAT THIS IS
------------
A pure, dependency-free checker. It takes the text of a single Markdown note
plus its declared note-type and returns a pass/fail result with a precise list
of structural errors. It makes NO model calls and NO network calls. It cannot
check whether the *fiction* is true (invented canon has no ground truth) — only
whether the note is STRUCTURALLY valid against its template.

It is the deterministic half of the validation gate described in the campaign
build plan: the retry loop (model -> gate -> errors back to model -> repeat)
wraps this validator but lives elsewhere (see gate_loop.py / the Open WebUI
integration). Keeping the validator pure means you can run it on your existing
vault RIGHT NOW, unit-test it, and trust it independently of any model.

SCHEMAS are derived directly from the corrected template library (the versions
with the frontmatter `summary:` key removed). If you change a template, update
the matching entry in SCHEMAS below.

USAGE
-----
    # As a library:
    from gate import validate
    result = validate(note_text, note_type="region")
    if not result.ok:
        for err in result.errors:
            print(err)

    # As a CLI (type inferred from frontmatter `type:` if not given):
    python3 gate.py path/to/Note.md
    python3 gate.py path/to/Note.md --type region
    python3 gate.py vault_dir/            # validate every .md in a directory
    python3 gate.py vault_dir/ --json     # machine-readable output for the loop

EXIT CODES
----------
    0  all checked notes passed
    1  one or more notes failed validation
    2  usage / file error
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- #
# SCHEMA
# --------------------------------------------------------------------------- #
# For each note type:
#   "frontmatter": the CLOSED SET of allowed frontmatter keys. Any key present
#                  that is not in this set is a failure (closed-set rule).
#                  Note: "summary" is deliberately ABSENT everywhere — its
#                  presence in frontmatter is a hard failure.
#   "sections":    the required "## " body sections, in no particular order for
#                  validation (presence is what matters). The Templater title
#                  artifact "## <% tp.file.title %>" is never required.
#
# Derived directly from the corrected templates. Keep in sync if templates change.

SCHEMAS: dict[str, dict[str, list[str]]] = {
    "bible": {
        # Foundational design/premise/GM-prep documents (Tone & Themes, Overview,
        # First Session). Intentionally loose: only Summary is required, because
        # these human-authored docs share no fixed structure. Guarded by a
        # required campaign-bible/gm-prep tag (see TAG_REQUIRED_TYPES below) so the
        # loose type cannot be used to evade structure on in-world canon.
        "frontmatter": ["type", "name", "aliases", "canon_state", "tags", "created",
                        "updated", "relationships", "first_appearance",
                        "last_appearance", "related_sessions"],
        "sections": ["Summary"],
    },
    "character": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "player",
                        "home_region", "faction", "occupation", "tags", "created",
                        "updated", "relationships", "first_appearance", "last_appearance",
                        "related_sessions"],
        # Required core only. The defining-trait slot (e.g. "The Raven", "Voice"),
        # Secrets, and Equipment & Possessions are OPTIONAL and not checked by name.
        # "How They Play (Cairn 2e)" header is standardized; pronoun lives in the body.
        "sections": ["Summary", "Background", "Arc", "Goals & Bonds", "Relationships",
                     "How They Play (Cairn 2e)", "Session Log"],
    },
    "culture": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "region",
                        "tags", "created", "updated", "relationships",
                        "first_appearance", "last_appearance", "related_sessions"],
        "sections": ["Summary", "Origins", "Core Values", "Traditions",
                     "Social Structure", "Appearance & Material Culture",
                     "Relationships", "Notable Locations", "Common Beliefs",
                     "Misconceptions", "Adventure Hooks", "Session Appearances"],
    },
    "dungeon": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "region",
                        "parent_location", "tags", "created", "updated", "relationships",
                        "first_appearance", "last_appearance", "related_sessions"],
        "sections": ["Summary", "Origins", "Current State", "Entrances",
                     "Important Areas", "Inhabitants", "Dangers",
                     "Treasures & Secrets", "Mysteries", "Adventure Hooks",
                     "Connected Locations", "Session Appearances"],
    },
    "event": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state",
                        "event_type", "event_date", "tags", "created", "updated",
                        "relationships", "first_appearance", "last_appearance",
                        "related_sessions"],
        "sections": ["Summary", "Description", "Participants", "Locations", "Causes",
                     "Consequences", "Historical Significance", "Rumors & Legends",
                     "Related Mysteries", "Related Notes", "Session Appearances"],
    },
    "faction": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "leader",
                        "headquarters", "tags", "created", "updated", "relationships",
                        "first_appearance", "last_appearance", "related_sessions"],
        "sections": ["Summary", "Purpose", "Goals", "Leadership",
                     "Structure & Membership", "Relationships", "Assets & Reach",
                     "Holdings", "Secrets", "Adventure Hooks", "Session Appearances"],
    },
    "item": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "owner",
                        "current_location", "tags", "created", "updated",
                        "relationships", "first_appearance", "last_appearance",
                        "related_sessions"],
        "sections": ["Summary", "Description", "Properties", "History",
                     "Current Status", "Interested Parties", "Related Locations",
                     "Mysteries", "Adventure Hooks", "Session Appearances"],
    },
    "location": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state",
                        "location_type", "region", "controlling_faction",
                        "parent_location", "tags", "created", "updated",
                        "relationships", "first_appearance", "last_appearance",
                        "related_sessions"],
        "sections": ["Summary", "Description", "History", "Inhabitants",
                     "Points of Interest", "Rumors", "Hooks", "Connected Locations",
                     "Session Appearances"],
    },
    "lore": {
        "frontmatter": ["type", "name", "aliases", "canon_state", "tags", "created",
                        "updated", "relationships", "first_appearance",
                        "last_appearance", "related_sessions"],
        "sections": ["Summary", "Background", "Significance", "Related Locations",
                     "Related NPCs", "Related Factions", "Related Mysteries",
                     "Common Beliefs", "Competing Interpretations", "Open Questions",
                     "Session Appearances"],
    },
    "mystery": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "tags",
                        "created", "updated", "relationships", "related_sessions"],
        "sections": ["Summary", "Known Facts", "Rumors", "Competing Theories",
                     "Evidence", "Open Questions", "Related Locations",
                     "Related NPCs", "Session Progress"],
    },
    "npc": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state",
                        "occupation", "location", "faction", "tags", "created",
                        "updated", "relationships", "first_appearance",
                        "last_appearance", "related_sessions"],
        "sections": ["Summary", "Appearance & Manner", "Voice", "Personality",
                     "Motivations", "Relationships", "Knowledge", "Secrets", "Hooks",
                     "Session Appearances"],
    },
    "organization": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "leader",
                        "headquarters", "tags", "created", "updated", "relationships",
                        "first_appearance", "last_appearance", "related_sessions"],
        "sections": ["Summary", "Purpose", "Leadership", "Membership", "Structure",
                     "Resources", "Operations", "Relationships", "Secrets",
                     "Adventure Hooks", "Session Appearances"],
    },
    "quest": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state",
                        "quest_giver", "region", "tags", "created", "updated",
                        "relationships", "first_appearance", "last_appearance",
                        "related_sessions"],
        "sections": ["Summary", "Objective", "Background", "Participants", "Locations",
                     "Progress", "Obstacles", "Stakes", "Related Mysteries",
                     "Related Notes", "Session Appearances"],
    },
    "region": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "tags",
                        "created", "updated", "relationships", "first_appearance",
                        "last_appearance", "related_sessions", "controlling_faction"],
        # Thin core only. The "populate from play" sections — Wilderness Areas,
        # Dungeons, Factions, Important NPCs, Cultures, Religions — are OPTIONAL,
        # so a thin region isn't forced to invent inhabitants, cults, or deities.
        # Authors and the worldbuilder may still include them.
        "sections": ["Summary", "Geography", "History", "Settlements", "Mysteries",
                     "Rumors", "Adventure Hooks", "Connected Regions", "Related Lore",
                     "Future Note Opportunities", "Session Appearances"],
    },
    "religion": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state",
                        "primary_region", "tags", "created", "updated", "relationships",
                        "first_appearance", "last_appearance", "related_sessions"],
        "sections": ["Summary", "Beliefs", "Deities & Spirits", "Sacred Practices",
                     "Holy Days", "Clergy & Leadership", "Holy Sites",
                     "Heresies & Schisms", "Relationships", "Mysteries",
                     "Adventure Hooks", "Session Appearances"],
    },
    "session": {
        "frontmatter": ["type", "session_number", "session_date", "status",
                        "canon_state", "tags", "created", "updated",
                        "present_characters", "npcs_encountered", "locations_visited",
                        "factions_involved", "quests_advanced", "mysteries_touched",
                        "new_notes_created"],
        "sections": ["Summary", "What Happened", "Decisions & Outcomes",
                     "NPCs Encountered", "Locations Visited", "Factions Involved",
                     "Quests Advanced", "Mysteries Touched", "New Discoveries",
                     "Loot & Rewards", "Loose Threads", "Campaign Changes",
                     "GM Notes", "Session Appearances"],
    },
    "settlement": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state",
                        "settlement_type", "region", "controlling_faction",
                        "population_scale", "tags", "created", "updated",
                        "relationships", "first_appearance", "last_appearance",
                        "related_sessions"],
        "sections": ["Summary", "Description", "Government", "Economy", "Notable NPCs",
                     "Factions Present", "Points of Interest", "Rumors", "Problems",
                     "Adventure Hooks", "Connected Locations", "Session Appearances"],
    },
    "timeline_entry": {
        "frontmatter": ["type", "name", "aliases", "canon_state", "event_date", "tags",
                        "created", "updated", "relationships"],
        "sections": ["Summary", "Event", "Participants", "Locations", "Consequences",
                     "Related Events", "Related Lore"],
    },
    "wilderness": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "region",
                        "tags", "created", "updated", "relationships",
                        "first_appearance", "last_appearance", "related_sessions"],
        "sections": ["Summary", "Description", "Flora & Fauna", "Landmarks", "Trails",
                     "Inhabitants", "Rumors", "Mysteries", "Adventure Hooks",
                     "Connected Locations", "Session Appearances"],
    },
}

# Frontmatter keys that may legitimately be blank (awaiting a value not yet
# decided in play — e.g. a region not yet linked, a faction not yet assigned).
# A blank required key is NOT an error; an absent required key IS. This matches
# the "build thin, fill from play" discipline.
#
# We do NOT require every key to have a value. We require: (a) no key outside
# the closed set, and (b) the type/name keys to be non-empty (a note must know
# what it is and what it's called). Everything else may be blank.
ALWAYS_NONEMPTY = ["type", "name"]
# Session/Timeline use different identity keys:
ALWAYS_NONEMPTY_BY_TYPE = {
    "session": ["type", "session_number"],
    "timeline_entry": ["type", "name"],
}

TITLE_ARTIFACT = "<% tp.file.title %>"  # never required as a section

# Controlled vocabularies for these frontmatter fields. Values must match
# case-sensitively (lowercase), to keep the vault consistent and stop the model
# from drifting into "Active"/"Draft" etc.
VALID_CANON_STATE = {"canon", "proposed", "draft", "hidden", "retired"}
VALID_STATUS = {"active", "inactive", "hidden", "destroyed", "dead",
                "completed", "abandoned", "unknown"}

# Some types must carry at least one tag from a required set, to stop a loose
# type from being misused. `bible` is intentionally low-structure, so it is only
# valid for genuine design/premise/prep docs — enforced by requiring a
# campaign-bible or gm-prep structural tag.
TAG_REQUIRED_TYPES: dict[str, list[str]] = {
    "bible": ["campaign-bible", "gm-prep"],
}


# --------------------------------------------------------------------------- #
# RESULT TYPES
# --------------------------------------------------------------------------- #
@dataclass
class Result:
    ok: bool
    note_type: Optional[str]
    path: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "note_type": self.note_type,
            "path": self.path,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# --------------------------------------------------------------------------- #
# PARSING HELPERS  (handle the real-world traps: CRLF, blank lines, etc.)
# --------------------------------------------------------------------------- #
def _normalize(text: str) -> str:
    """Strip carriage returns so CRLF vault files compare correctly."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_frontmatter(text: str) -> tuple[Optional[str], str]:
    """
    Return (frontmatter_block, body). A note's frontmatter is the block between
    the first '---' on line 1 and the next '---'. If the file does not start
    with '---', there is no frontmatter (returns None).
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1:])
            return fm, body
    # opened but never closed
    return None, text


def _parse_frontmatter_keys(fm: str) -> dict[str, str]:
    """
    Extract top-level keys and their raw inline values from a frontmatter block.
    Only TOP-LEVEL keys (no leading whitespace) count, so nested list items or
    mapping values are not mistaken for keys. Value is whatever follows the
    first colon on the key's line (may be empty).
    """
    keys: dict[str, str] = {}
    for line in fm.split("\n"):
        if not line or line[0] in (" ", "\t", "-", "*", "#"):
            continue
        m = re.match(r"^([A-Za-z0-9_]+):(.*)$", line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def _parse_tags(fm: str) -> list[str]:
    """
    Extract tag values from a frontmatter block, handling both styles:
      inline:  tags: [campaign, region]
      block:   tags:\n  - campaign\n  - region   (or '* campaign' bullets)
    Returns a lowercased list of tag strings.
    """
    lines = fm.split("\n")
    tags: list[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        m = re.match(r"^tags:\s*(.*)$", line)
        if m:
            inline = m.group(1).strip()
            if inline.startswith("[") and inline.endswith("]"):
                # inline list
                inner = inline[1:-1]
                tags.extend(t.strip().strip('"').strip("'")
                            for t in inner.split(",") if t.strip())
                in_block = False
            elif inline == "":
                in_block = True  # block list follows
            else:
                tags.append(inline.strip('"').strip("'"))
                in_block = False
            continue
        if in_block:
            # block items are '- tag' or '* tag', possibly indented
            bm = re.match(r"^[\s]*[-*]\s+(.+)$", line)
            if bm:
                tags.append(bm.group(1).strip().strip('"').strip("'"))
            elif stripped and not line[0].isspace() and ":" in line:
                in_block = False  # next top-level key ends the block
    return [t.lower() for t in tags if t]


def _body_sections(body: str) -> list[str]:
    """Return the list of '## ' section titles in the body (CR already stripped)."""
    out = []
    for line in body.split("\n"):
        if line.startswith("## "):
            out.append(line[3:].strip())
    return out


# --------------------------------------------------------------------------- #
# VALIDATION
# --------------------------------------------------------------------------- #
def validate(text: str, note_type: Optional[str] = None,
             path: Optional[str] = None,
             today: Optional[_dt.date] = None,
             known_sessions: Optional[set] = None) -> Result:
    """
    Validate a single note's structure. `note_type` may be omitted; if so it is
    read from the frontmatter `type:` key. `today` is injectable for testing the
    future-date check. `known_sessions`, if given, is the set of session numbers
    that actually exist (as ints); when provided, the note is soft-warned for
    citing a "Session N" that isn't among them (catches invented play history).
    When omitted, the session-citation check is skipped.
    """
    today = today or _dt.date.today()
    text = _normalize(text)
    errors: list[str] = []
    warnings: list[str] = []

    fm_block, body = _split_frontmatter(text)
    if fm_block is None:
        return Result(ok=False, note_type=note_type, path=path,
                      errors=["No YAML frontmatter found (note must open with '---' "
                              "on line 1 and close with a second '---')."])

    fm = _parse_frontmatter_keys(fm_block)

    # Resolve note type
    declared = fm.get("type", "").strip().strip('"').strip("'").lower()
    note_type = (note_type or declared or "").lower()
    if not note_type:
        errors.append("Note has no `type:` in frontmatter and no type was supplied.")
        return Result(ok=False, note_type=None, path=path, errors=errors)
    if note_type not in SCHEMAS:
        errors.append(f"Unknown note type '{note_type}'. "
                      f"Known types: {', '.join(sorted(SCHEMAS))}.")
        return Result(ok=False, note_type=note_type, path=path, errors=errors)
    if declared and declared != note_type:
        errors.append(f"Frontmatter type '{declared}' does not match expected "
                      f"type '{note_type}'.")

    schema = SCHEMAS[note_type]
    allowed = set(schema["frontmatter"])

    # --- RULE 1: no frontmatter key outside the closed set ------------------ #
    for key in fm:
        if key not in allowed:
            if key == "summary":
                errors.append("Frontmatter contains forbidden key `summary:` — the "
                              "Summary must be a body `## Summary` section, never "
                              "frontmatter (Field Conventions §11).")
            else:
                errors.append(f"Frontmatter key `{key}:` is not in the closed set for "
                              f"type '{note_type}'. Allowed: {', '.join(schema['frontmatter'])}.")

    # --- RULE 2: all required frontmatter keys present ---------------------- #
    for key in schema["frontmatter"]:
        if key not in fm:
            errors.append(f"Frontmatter is missing required key `{key}:`.")

    # --- RULE 3: identity keys must be non-empty ---------------------------- #
    nonempty = ALWAYS_NONEMPTY_BY_TYPE.get(note_type, ALWAYS_NONEMPTY)
    for key in nonempty:
        val = fm.get(key, "").strip().strip('"').strip("'")
        if not val:
            errors.append(f"Frontmatter key `{key}:` must not be empty.")

    # --- RULE 3b: no literal placeholder words in frontmatter values -------- #
    # Models like to write "unknown"/"none"/"n/a"/"tbd" where a field should be
    # blank or a real value. These pollute retrieval; require blank instead.
    PLACEHOLDER_WORDS = {"unknown", "none", "n/a", "na", "tbd", "tba", "todo",
                         "null", "nil", "?", "??", "???"}
    for key, raw in fm.items():
        v = raw.strip().strip('"').strip("'").strip("[]").strip().lower()
        if v in PLACEHOLDER_WORDS:
            errors.append(f"Frontmatter key `{key}:` has placeholder value "
                          f"'{raw.strip()}'. Leave it blank or give a real value "
                          f"(never 'unknown'/'none'/'tbd').")

    # --- RULE 3c: relationships should use wikilinks, not bare strings ------ #
    # SOFT warning: §7 relationships reference other notes, so a populated
    # relationship should contain a [[wikilink]]. Bare strings like
    # "- Whisperbridge" are almost certainly a model error. Not a hard fail,
    # because the populated shape isn't yet battle-tested in the vault.
    if "relationships" in fm:
        # Walk the relationships block in the raw frontmatter. A YAML block list
        # has an EMPTY inline value with '- item' lines following, so we inspect
        # the block whenever such items appear (don't gate on the inline value).
        in_block = False
        has_link = False
        has_bare = False
        for line in fm_block.split("\n"):
            if re.match(r"^relationships:\s*(\[\s*\])?\s*$", line):
                in_block = True
                continue
            if in_block:
                if line and not line[0].isspace() and ":" in line:
                    break  # next top-level key ends the block
                if "[[" in line:
                    has_link = True
                elif re.match(r"^\s*-\s+\S", line):
                    has_bare = True
        if has_bare and not has_link:
            warnings.append("`relationships:` entries look like bare strings "
                            "(e.g. '- Whisperbridge'); they should reference "
                            "notes as [[wikilinks]] per the relationship "
                            "convention.")

    # --- RULE 4: canon_state and status must be valid lowercase values ------ #
    if "canon_state" in allowed:
        cs_raw = fm.get("canon_state", "").strip().strip('"').strip("'")
        if cs_raw and cs_raw not in VALID_CANON_STATE:
            if cs_raw.lower() in VALID_CANON_STATE:
                errors.append(f"`canon_state:` '{cs_raw}' must be lowercase "
                              f"'{cs_raw.lower()}'.")
            else:
                errors.append(f"`canon_state:` '{cs_raw}' is not a valid value. "
                              f"Use one of (lowercase): "
                              f"{', '.join(sorted(VALID_CANON_STATE))}.")
    if "status" in allowed:
        st_raw = fm.get("status", "").strip().strip('"').strip("'")
        if st_raw and st_raw not in VALID_STATUS:
            if st_raw.lower() in VALID_STATUS:
                errors.append(f"`status:` '{st_raw}' must be lowercase "
                              f"'{st_raw.lower()}'.")
            else:
                errors.append(f"`status:` '{st_raw}' is not a recognized value. "
                              f"Use one of (lowercase): "
                              f"{', '.join(sorted(VALID_STATUS))}.")

    # --- RULE 4b: tag guardrail for loose types (e.g. bible) ---------------- #
    if note_type in TAG_REQUIRED_TYPES:
        required_any = TAG_REQUIRED_TYPES[note_type]
        present_tags = _parse_tags(fm_block)
        if not any(t in present_tags for t in required_any):
            errors.append(
                f"Type '{note_type}' requires at least one of these tags: "
                f"{', '.join(required_any)}. This guardrail keeps the loose "
                f"'{note_type}' type from being used for in-world canon (which "
                f"must use its own typed template). Found tags: "
                f"{', '.join(present_tags) or '(none)'}.")

    # --- RULE 5: created date blank, or valid ISO and not in the future ----- #
    created = fm.get("created", "").strip().strip('"').strip("'")
    if created:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", created)
        if not m:
            errors.append(f"`created:` value '{created}' is not blank and not a valid "
                          f"YYYY-MM-DD date.")
        else:
            try:
                d = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                if d > today:
                    errors.append(f"`created:` date {created} is in the future "
                                  f"(today is {today.isoformat()}).")
            except ValueError:
                errors.append(f"`created:` value '{created}' is not a real date.")

    # --- RULE 6: all required body sections present ------------------------- #
    present = set(_body_sections(body))
    present.discard(TITLE_ARTIFACT)  # never required; ignore Templater artifact
    for sec in schema["sections"]:
        if sec not in present:
            errors.append(f"Missing required section `## {sec}`.")

    # --- RULE 7: Summary must be a body section ----------------------------- #
    if "Summary" not in present:
        # already reported as a missing section above, but make the intent loud
        if not any("## Summary" in e for e in errors):
            errors.append("Note has no body `## Summary` section.")

    # --- RULE 8: GM-ONLY sentinel blocks: balanced AND non-empty ------------ #
    starts = body.count("GM-ONLY:START")
    ends = body.count("GM-ONLY:END")
    if starts != ends:
        errors.append(f"Unbalanced GM-ONLY sentinels: {starts} START vs {ends} END. "
                      f"Every `<!-- GM-ONLY:START -->` needs a matching "
                      f"`<!-- GM-ONLY:END -->` or the strip-on-ingest step will leak "
                      f"or over-cut.")
    else:
        # Each matched START..END pair must contain real content. An empty block
        # is noise (the model sometimes emits bare sentinels); it strips to
        # nothing and clutters the note.
        for m in re.finditer(r"GM-ONLY:START\s*-*>?(.*?)<?!?-*\s*GM-ONLY:END",
                             body, flags=re.DOTALL):
            inner = m.group(1)
            # strip comment punctuation, list bullets, and whitespace
            cleaned = re.sub(r"[-*>!\s]", "", inner)
            if not cleaned:
                errors.append("Empty GM-ONLY block: a "
                              "`<!-- GM-ONLY:START -->`/`<!-- GM-ONLY:END -->` pair "
                              "contains no content. Remove the empty sentinels or "
                              "put the GM-only text between them.")
                break

    # --- RULE 8b: cited sessions should exist (soft, only if we know them) -- #
    if known_sessions is not None:
        cited = set(int(n) for n in re.findall(r"\bSession\s+(\d+)\b", body))
        invented = sorted(cited - known_sessions)
        if invented:
            warnings.append(
                "References session(s) that don't exist yet: "
                + ", ".join(f"Session {n}" for n in invented)
                + ". No such session has been played/indexed — this looks like "
                "invented play history. (If you just played it, add it to the "
                "Session Index first.)")

    # --- RULE 9: forward-reference wikilinks are ALLOWED -------------------- #
    # We deliberately do NOT fail on links to non-existent notes here, because
    # the founding discipline relies on forward references from `proposed`
    # entities and open `[[Folder/]]` stubs. Link *resolution* is a separate,
    # softer check (see check_links, run with --check-links).

    ok = len(errors) == 0
    return Result(ok=ok, note_type=note_type, path=path, errors=errors,
                  warnings=warnings)


def check_links(text: str, known_notes: set[str]) -> list[str]:
    """
    OPTIONAL soft check: report wikilinks that don't resolve to a known note,
    EXCLUDING allowed forward-reference forms:
      - open folder stubs like [[Factions/]], [[Locations/]] (end with '/')
      - links whose surrounding line marks them (proposed) — caller may pre-filter
    Returns a list of warning strings (never hard errors). The known_notes set
    should contain note basenames without the .md extension.
    """
    text = _normalize(text)
    warnings: list[str] = []
    for m in re.finditer(r"\[\[([^\]]+)\]\]", text):
        target = m.group(1).split("|")[0].strip()
        if target.endswith("/"):
            continue  # open folder stub — allowed
        # normalize "Name" vs "Name.md"
        base = target[:-3] if target.endswith(".md") else target
        if base not in known_notes:
            warnings.append(f"Wikilink [[{target}]] does not resolve to a known note "
                            f"(allowed if this is a proposed/forward reference).")
    return warnings


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _iter_markdown(path: str):
    if os.path.isdir(path):
        for root, _dirs, files in os.walk(path):
            for fn in sorted(files):
                if fn.endswith(".md"):
                    yield os.path.join(root, fn)
    else:
        yield path


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Validate Platinum & Bramble vault notes.")
    ap.add_argument("path", help="A .md file or a directory of notes.")
    ap.add_argument("--type", help="Force a note type (else read from frontmatter).")
    ap.add_argument("--json", action="store_true", help="Emit JSON (for the retry loop).")
    ap.add_argument("--check-links", action="store_true",
                    help="Also warn about unresolved wikilinks (soft).")
    args = ap.parse_args(argv)

    if not os.path.exists(args.path):
        print(f"error: path not found: {args.path}", file=sys.stderr)
        return 2

    paths = list(_iter_markdown(args.path))
    if not paths:
        print(f"error: no .md files found at {args.path}", file=sys.stderr)
        return 2

    # Build known-notes set for link checking (basenames without extension).
    known = {os.path.splitext(os.path.basename(p))[0] for p in paths}

    # Build the set of session numbers that actually exist, by scanning for
    # notes of type 'session' and reading their session_number. Used for the
    # invented-play-history soft warning. Only meaningful when validating a
    # directory; for a single file we pass None (check skipped).
    known_sessions = None
    if os.path.isdir(args.path):
        known_sessions = set()
        for p in paths:
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    t = _normalize(fh.read())
            except OSError:
                continue
            fmb, _ = _split_frontmatter(t)
            if not fmb:
                continue
            keys = _parse_frontmatter_keys(fmb)
            if keys.get("type", "").strip().strip('"').strip("'").lower() == "session":
                num = keys.get("session_number", "").strip().strip('"').strip("'")
                if num.isdigit():
                    known_sessions.add(int(num))

    results = []
    any_fail = False
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            results.append(Result(ok=False, note_type=None, path=p,
                                  errors=[f"could not read file: {e}"]))
            any_fail = True
            continue
        res = validate(text, note_type=args.type, path=p,
                       known_sessions=known_sessions)
        if args.check_links:
            res.warnings.extend(check_links(text, known))
        if not res.ok:
            any_fail = True
        results.append(res)

    if args.json:
        print(json.dumps([r.as_dict() for r in results], indent=2))
        return 1 if any_fail else 0

    # Human-readable
    for r in results:
        label = os.path.basename(r.path) if r.path else "(input)"
        if r.ok and not r.warnings:
            print(f"PASS  {label}  [{r.note_type}]")
        elif r.ok:
            print(f"PASS  {label}  [{r.note_type}]  ({len(r.warnings)} warning(s))")
            for w in r.warnings:
                print(f"      ~ {w}")
        else:
            print(f"FAIL  {label}  [{r.note_type or '?'}]")
            for e in r.errors:
                print(f"      ✗ {e}")
            for w in r.warnings:
                print(f"      ~ {w}")
    n_pass = sum(1 for r in results if r.ok)
    print(f"\n{n_pass}/{len(results)} notes passed.")
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())