"""
title: Worldbuilder (Gated)
author: Platinum & Bramble
version: 0.1.0
description: >
  A gated Worldbuilder for the Platinum & Bramble campaign. Generates vault
  notes with the local model, validates them against the campaign's structural
  gate, and automatically retries (feeding errors back to the model) until the
  note passes or max tries is reached. Appears as a selectable model in the
  Open WebUI chat dropdown.

HOW IT WORKS
  You chat with it like a model. Tell it what note to make, e.g.:
      region: The Marsh of Knor
      npc: Old Hedda — the innkeeper's wary mother
  It generates, validates with the embedded gate, retries on failure, and
  returns the passing note plus a list of invented wikilinks for you to approve.

IMPORTANT — KEEP IN SYNC
  The validator below (SCHEMAS, TAG_REQUIRED_TYPES, validate()) is a copy of the
  logic in gate.py. Open WebUI Functions run sandboxed and cannot import your
  local gate.py, so the schema is embedded here. If you change a template (and
  therefore gate.py's SCHEMAS), paste the same change into the SCHEMAS dict
  below. The two must match or the in-chat gate will disagree with your CLI gate.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Optional

from pydantic import BaseModel, Field

try:
    import requests
except ImportError:  # Open WebUI provides requests; this is a safety net
    requests = None


# =========================================================================== #
# EMBEDDED GATE  (mirror of gate.py — keep in sync)
# =========================================================================== #
SCHEMAS = {
    "bible": {
        "frontmatter": ["type", "name", "aliases", "canon_state", "tags", "created",
                        "updated", "relationships", "first_appearance",
                        "last_appearance", "related_sessions"],
        "sections": ["Summary"],
    },
    "character": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "player",
                        "home_region", "faction", "occupation", "tags", "created",
                        "updated", "relationships", "first_appearance",
                        "last_appearance", "related_sessions"],
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
                        "parent_location", "tags", "created", "updated",
                        "relationships", "first_appearance", "last_appearance",
                        "related_sessions"],
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
        "sections": ["Summary", "Geography", "History", "Settlements", "Mysteries",
                     "Rumors", "Adventure Hooks", "Connected Regions", "Related Lore",
                     "Future Note Opportunities", "Session Appearances"],
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
    "timeline_entry": {
        "frontmatter": ["type", "name", "aliases", "canon_state", "event_date", "tags",
                        "created", "updated", "relationships"],
        "sections": ["Summary", "Event", "Participants", "Locations", "Consequences",
                     "Related Events", "Related Lore"],
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
    "wilderness": {
        "frontmatter": ["type", "name", "aliases", "status", "canon_state", "region",
                        "tags", "created", "updated", "relationships",
                        "first_appearance", "last_appearance", "related_sessions"],
        "sections": ["Summary", "Description", "Flora & Fauna", "Landmarks", "Trails",
                     "Inhabitants", "Rumors", "Mysteries", "Adventure Hooks",
                     "Connected Locations", "Session Appearances"],
    },
}

ALWAYS_NONEMPTY = ["type", "name"]
ALWAYS_NONEMPTY_BY_TYPE = {
    "session": ["type", "session_number"],
    "timeline_entry": ["type", "name"],
}
TITLE_ARTIFACT = "<% tp.file.title %>"
TAG_REQUIRED_TYPES = {"bible": ["campaign-bible", "gm-prep"]}
VALID_CANON_STATE = {"canon", "proposed", "draft", "hidden", "retired"}
VALID_STATUS = {"active", "inactive", "hidden", "destroyed", "dead",
                "completed", "abandoned", "unknown"}


def _normalize(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_frontmatter(text):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return None, text


def _parse_frontmatter_keys(fm):
    keys = {}
    for line in fm.split("\n"):
        if not line or line[0] in (" ", "\t", "-", "*", "#"):
            continue
        m = re.match(r"^([A-Za-z0-9_]+):(.*)$", line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def _parse_tags(fm):
    tags = []
    in_block = False
    for line in fm.split("\n"):
        m = re.match(r"^tags:\s*(.*)$", line)
        if m:
            inline = m.group(1).strip()
            if inline.startswith("[") and inline.endswith("]"):
                tags.extend(t.strip().strip('"').strip("'")
                            for t in inline[1:-1].split(",") if t.strip())
                in_block = False
            elif inline == "":
                in_block = True
            else:
                tags.append(inline.strip('"').strip("'"))
                in_block = False
            continue
        if in_block:
            bm = re.match(r"^\s*[-*]\s+(.+)$", line)
            if bm:
                tags.append(bm.group(1).strip().strip('"').strip("'"))
            elif line.strip() and not line[0].isspace() and ":" in line:
                in_block = False
    return [t.lower() for t in tags if t]


def _body_sections(body):
    return [ln[3:].strip() for ln in body.split("\n") if ln.startswith("## ")]


def validate(text, note_type=None, today=None):
    """Returns (ok: bool, errors: list[str]). Mirror of gate.py:validate."""
    today = today or _dt.date.today()
    text = _normalize(text)
    errors = []
    fm_block, body = _split_frontmatter(text)
    if fm_block is None:
        return False, ["No YAML frontmatter found (note must open with '---')."]
    fm = _parse_frontmatter_keys(fm_block)
    declared = fm.get("type", "").strip().strip('"').strip("'").lower()
    note_type = (note_type or declared or "").lower()
    if not note_type:
        return False, ["Note has no `type:` and none was supplied."]
    if note_type not in SCHEMAS:
        return False, [f"Unknown note type '{note_type}'."]
    if declared and declared != note_type:
        errors.append(f"Frontmatter type '{declared}' != expected '{note_type}'.")
    schema = SCHEMAS[note_type]
    allowed = set(schema["frontmatter"])
    for key in fm:
        if key not in allowed:
            if key == "summary":
                errors.append("Forbidden key `summary:` in frontmatter — Summary "
                              "must be a body `## Summary` section.")
            else:
                errors.append(f"Frontmatter key `{key}:` not in the closed set for "
                              f"'{note_type}'. Allowed: {', '.join(schema['frontmatter'])}.")
    for key in schema["frontmatter"]:
        if key not in fm:
            errors.append(f"Missing required frontmatter key `{key}:`.")
    nonempty = ALWAYS_NONEMPTY_BY_TYPE.get(note_type, ALWAYS_NONEMPTY)
    for key in nonempty:
        if key in allowed and not fm.get(key, "").strip().strip('"').strip("'"):
            errors.append(f"Frontmatter key `{key}:` must not be empty.")
    PLACEHOLDER_WORDS = {"unknown", "none", "n/a", "na", "tbd", "tba", "todo",
                         "null", "nil", "?", "??", "???"}
    for key, raw in fm.items():
        v = raw.strip().strip('"').strip("'").strip("[]").strip().lower()
        if v in PLACEHOLDER_WORDS:
            errors.append(f"Frontmatter key `{key}:` has placeholder value "
                          f"'{raw.strip()}'. Leave it blank or give a real value "
                          f"(never 'unknown'/'none'/'tbd').")
    if note_type in TAG_REQUIRED_TYPES:
        req = TAG_REQUIRED_TYPES[note_type]
        present_tags = _parse_tags(fm_block)
        if not any(t in present_tags for t in req):
            errors.append(f"Type '{note_type}' requires one of these tags: "
                          f"{', '.join(req)}. Found: {', '.join(present_tags) or '(none)'}.")
    if "canon_state" in allowed:
        cs_raw = fm.get("canon_state", "").strip().strip('"').strip("'")
        if cs_raw and cs_raw not in VALID_CANON_STATE:
            if cs_raw.lower() in VALID_CANON_STATE:
                errors.append(f"`canon_state:` '{cs_raw}' must be lowercase '{cs_raw.lower()}'.")
            else:
                errors.append(f"`canon_state:` '{cs_raw}' invalid. Use (lowercase): "
                              f"{', '.join(sorted(VALID_CANON_STATE))}.")
    if "status" in allowed:
        st_raw = fm.get("status", "").strip().strip('"').strip("'")
        if st_raw and st_raw not in VALID_STATUS:
            if st_raw.lower() in VALID_STATUS:
                errors.append(f"`status:` '{st_raw}' must be lowercase '{st_raw.lower()}'.")
            else:
                errors.append(f"`status:` '{st_raw}' not recognized. Use (lowercase): "
                              f"{', '.join(sorted(VALID_STATUS))}.")
    created = fm.get("created", "").strip().strip('"').strip("'")
    if created:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", created)
        if not m:
            errors.append(f"`created:` '{created}' is not blank and not YYYY-MM-DD.")
        else:
            try:
                d = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                if d > today:
                    errors.append(f"`created:` {created} is in the future.")
            except ValueError:
                errors.append(f"`created:` '{created}' is not a real date.")
    present = set(_body_sections(body))
    present.discard(TITLE_ARTIFACT)
    for sec in schema["sections"]:
        if sec not in present:
            errors.append(f"Missing required section `## {sec}`.")
    starts, ends = body.count("GM-ONLY:START"), body.count("GM-ONLY:END")
    if starts != ends:
        errors.append(f"Unbalanced GM-ONLY sentinels: {starts} START vs {ends} END.")
    else:
        for m in re.finditer(r"GM-ONLY:START\s*-*>?(.*?)<?!?-*\s*GM-ONLY:END",
                             body, flags=re.DOTALL):
            if not re.sub(r"[-*>!\s]", "", m.group(1)):
                errors.append("Empty GM-ONLY block: a START/END pair contains no "
                              "content. Remove the empty sentinels or fill them.")
                break
    return (len(errors) == 0), errors


# =========================================================================== #
# PROMPTING
# =========================================================================== #
def build_system_prompt(note_type):
    schema = SCHEMAS[note_type]
    fm_lines = "\n".join(f"  {k}:" for k in schema["frontmatter"])
    sec_lines = "\n".join(f"  ## {s}" for s in schema["sections"])
    tag_rule = ""
    if note_type in TAG_REQUIRED_TYPES:
        tag_rule = (f"\n- The `tags:` list MUST include at least one of: "
                    f"{', '.join(TAG_REQUIRED_TYPES[note_type])}.")
    return f"""You are the Worldbuilder for a Cairn 2e dark-folktale campaign \
called Platinum & Bramble. You author vault notes that must pass an automated \
structural gate EXACTLY. Output ONLY the note as Markdown — no preamble, no \
explanation, no code fences.

GROUNDING (from the Campaign Constitution):
- Mystery over explanation; folklore over history; adventure over lore.

CANON ANCHORS — these are FIXED. Never contradict or scramble them:
- THE MAP, west to east: the Holdlands (ordered North) — THE SEAM (the border,
  where the campaign is set) — the ASHWOOD (old Eastern forest). So Holdlands =
  WEST, Ashwood = EAST, the Seam is BETWEEN.
- "East of the Seam" = toward the wild Ashwood. "West of the Seam" = toward the
  settled Holdlands. Keep a place's described character consistent with its side.
- Whisperbridge is the chief crossing, a ford-inn ON the Seam.
- The Ford-Wardens are TRUCE-KEEPERS, not a garrison or army — peace by custom,
  no standing force or walls. Never write them as soldiers.
- The Ashwood is the central MYSTERY, deliberately unresolved.
- Do NOT invent played-session history. No sessions are played unless stated.

- Build THIN. Invent only what the note needs to be usable; leave most of the
  world open for play. A good note plants hooks and questions, not answers. Do
  NOT generate exhaustive sub-locations, named sub-factions, cults, deities,
  ghost NPCs, or backstory unless asked. When in doubt, write less and leave a
  "Future Note Opportunities" pointer instead.
- PROTECT THE EAST. The Eastern forest (the Ashwood, "east of the Seam") is the
  campaign's central mystery and is DELIBERATELY kept thin and unresolved, even
  for the GM. Do NOT invent its deep history, its rulers, what dwells in it, or
  what power stirs there. If a note touches the East, keep it sparse, uncertain,
  and from an outsider's limited view; leave the truth open.
- Tone: grounded and grim with heroic counterweight, mythic only at the edges —
  not generic dark-fantasy, not a horror theme park. Rationed strangeness.
- Use established canon names where relevant (the Seam, Whisperbridge, the
  Holdlands, the Ashwood, the Ford-Wardens, the Wrong Cold). NEVER contradict
  established canon. New names/details are DRAFTS for GM approval.
- Values must be lowercase: status (e.g. active), canon_state (e.g. draft).
- Leave fields BLANK rather than writing "unknown"/"none"/"tbd"; the gate rejects
  placeholder words.
- In `relationships:`, reference other notes as [[wikilinks]], never bare names.
- You may OMIT optional sections if a thin note doesn't need them; don't invent
  inhabitants, factions, cults, or deities just to fill a section.
- Do NOT emit empty GM-ONLY blocks; only use the sentinels when there is real
  GM-only content between them.

HARD STRUCTURAL RULES (the gate rejects any violation):
- The note is type '{note_type}'.
- Frontmatter is YAML between two '---' lines, FIRST line of the file.
- Frontmatter must contain EXACTLY these keys, no others (CLOSED set):
{fm_lines}
- NEVER put a `summary:` key in frontmatter; the summary is a body section.
- `type:` must be "{note_type}". `name:` must not be empty.
- `created:` blank OR a real past YYYY-MM-DD; prefer blank, never invent a date.
- The body must contain ALL of these headers, spelled EXACTLY:
{sec_lines}
- You MAY add extra sections, but never omit a required one.
- Wrap GM-only/spoiler content in <!-- GM-ONLY:START --> ... <!-- GM-ONLY:END -->.{tag_rule}

Produce the complete note now."""


def extract_note(reply):
    fences = re.findall(r"```(?:markdown|md|yaml)?\s*\n(.*?)```", reply, flags=re.DOTALL)
    if fences:
        return max(fences, key=len).strip()
    if reply.lstrip().startswith("---"):
        return reply.strip()
    idx = reply.find("\n---")
    if idx != -1:
        start = reply.rfind("---", 0, idx + 4)
        if start != -1:
            return reply[start:].strip()
    return reply.strip()


def parse_request(user_text):
    """
    Parse 'region: The Marsh of Knor' or 'npc: Old Hedda — wary mother'.
    Returns (note_type, name, brief). Falls back to type=None if unparseable.
    """
    m = re.match(r"^\s*([a-zA-Z_]+)\s*:\s*(.+)$", user_text.strip())
    if not m:
        return None, None, None
    note_type = m.group(1).lower()
    rest = m.group(2).strip()
    # split a brief off after an em-dash or ' - '
    parts = re.split(r"\s+[—-]\s+", rest, maxsplit=1)
    name = parts[0].strip()
    brief = parts[1].strip() if len(parts) > 1 else ""
    return note_type, name, brief


def invented_wikilinks(note_text):
    seen = []
    for m in re.finditer(r"\[\[([^\]]+)\]\]", note_text):
        target = m.group(1).split("|")[0].strip()
        if target.endswith("/") or target in seen:
            continue
        seen.append(target)
    return seen


# =========================================================================== #
# THE PIPE  (Open WebUI entry point)
# =========================================================================== #
class Pipe:
    class Valves(BaseModel):
        OLLAMA_URL: str = Field(
            default="http://host.docker.internal:11434",
            description="Base URL of your Ollama server.")
        MODEL_NAME: str = Field(
            default="qwen2.5:14b-instruct-q5_K_M",
            description="Exact Ollama model tag to generate with.")
        MAX_TRIES: int = Field(
            default=4, description="Max generate-validate attempts before giving up.")
        TEMPERATURE: float = Field(
            default=0.4, description="Sampling temperature for generation.")

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        # Names the entry that appears in the model dropdown.
        return [{"id": "worldbuilder_gated", "name": "Worldbuilder (Gated)"}]

    def _call_model(self, messages):
        url = f"{self.valves.OLLAMA_URL.rstrip('/')}/api/chat"
        payload = {
            "model": self.valves.MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.valves.TEMPERATURE},
        }
        if requests is None:
            raise RuntimeError("The 'requests' library is unavailable in this "
                               "Open WebUI environment.")
        r = requests.post(url, json=payload, timeout=600)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")

    def pipe(self, body: dict) -> str:
        # Pull the latest user message
        messages_in = body.get("messages", [])
        user_text = ""
        for msg in reversed(messages_in):
            if msg.get("role") == "user":
                user_text = msg.get("content", "")
                break

        note_type, name, brief = parse_request(user_text)
        if not note_type or note_type not in SCHEMAS:
            known = ", ".join(sorted(SCHEMAS))
            return (
                "**Worldbuilder (Gated)** — tell me what to make, like:\n\n"
                "```\nregion: The Marsh of Knor\n"
                "npc: Old Hedda — the innkeeper's wary mother\n```\n\n"
                f"Known types: {known}.")

        system = build_system_prompt(note_type)
        convo = [
            {"role": "system", "content": system},
            {"role": "user",
             "content": f'Create the {note_type} note titled "{name}".'
                        + (f"\n\nGuidance: {brief}" if brief else "")},
        ]

        note_text, last_errors = "", []
        passed = False
        tries = 0
        for attempt in range(1, self.valves.MAX_TRIES + 1):
            tries = attempt
            try:
                reply = self._call_model(convo)
            except Exception as e:  # surface connection problems in-chat
                return (f"**Could not reach the model.** Check the Valves "
                        f"(OLLAMA_URL / MODEL_NAME).\n\n`{e}`")
            note_text = extract_note(reply)
            ok, errors = validate(note_text, note_type=note_type)
            last_errors = errors
            if ok:
                passed = True
                break
            convo.append({"role": "assistant", "content": note_text})
            bullet = "\n".join(f"- {e}" for e in errors)
            convo.append({"role": "user", "content":
                          "The note FAILED structural validation:\n" + bullet +
                          "\n\nFix EVERY error and output the COMPLETE corrected "
                          "note again — only the Markdown note, no commentary, no "
                          "fences. Keep all already-correct content."})

        # Assemble the in-chat response
        header = (f"### ✅ Valid `{note_type}` note — “{name}” (passed in {tries} "
                  f"attempt{'s' if tries != 1 else ''})\n\n"
                  if passed else
                  f"### ❌ Could not produce a valid `{note_type}` note in {tries} "
                  f"attempts\n\nRemaining errors:\n"
                  + "\n".join(f"- {e}" for e in last_errors) + "\n\n")

        out = header + "```markdown\n" + note_text.rstrip("\n") + "\n```\n"

        if passed:
            links = invented_wikilinks(note_text)
            if links:
                out += ("\n**Canon to approve** (wikilinks referenced — confirm real "
                        "ones, reject/rename invented ones):\n"
                        + "\n".join(f"- `[[{l}]]`" for l in links)
                        + "\n\n_The gate checks structure; truth is yours._")
        return out