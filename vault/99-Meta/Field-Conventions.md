---

type: meta
name: "Field Conventions"
aliases: ["Field Conventions", "Vault Conventions", "Conventions"]
tags: [meta, reference]
created: "2026-06-21"
updated: "2026-06-22"
---------------------

# Field Conventions

This document defines the standards used throughout The Bramblewise Archive.

Every template, assistant, query, dashboard, and retrieval workflow assumes these conventions are followed consistently.

The vault is the source of truth.

If a convention changes:

1. Update this document first.
2. Update affected templates.
3. Update assistant instructions if necessary.

Consistency is more important than perfection.

---

# 1. Core Principles

The vault exists to serve three purposes:

1. Human readability
2. Obsidian graph relationships
3. AI retrieval and reasoning

A note should be understandable by:

* The GM
* Future players
* Future assistants

Anything important enough to remember should exist as explicit text inside the vault.

Never rely on:

* Memory
* Folder names alone
* File names alone
* Images alone

Important information belongs in:

* Frontmatter
* Summary sections
* Wikilinks
* Relationship sections

---

## 2. Aliases

Every entity that may be known by multiple names should include aliases.

Examples:

```yaml
aliases:
  - Captain Vael
  - The One-Eyed Captain
  - Vael of the Reach
```

Aliases improve:

* Obsidian link resolution
* Search
* AI retrieval
* Natural language matching

Use:

```yaml
aliases: []
```

when no alternate names exist.

---

## 3. Wikilink Rule

All relationships between entities use wikilinks.

Never use plain text for references to other notes.

Correct:

```yaml
faction: "[[Factions/The Ash Wardens]]"

location: "[[Locations/Settlements/Whisperbridge]]"

leader: "[[NPCs/Captain Vael]]"
```

Correct:

```markdown
The town is protected by [[The Ash Wardens]].
```

Incorrect:

```yaml
faction: The Ash Wardens
```

Wikilinks provide:

* Backlinks
* Graph connections
* Better retrieval
* Better context expansion

---

## 4. Canon State

All campaign notes should include:

```yaml
canon_state:
```

Allowed values:

| Value      | Meaning                                    |
| ---------- | ------------------------------------------ |
| canon      | Established campaign truth                 |
| proposed   | Draft awaiting GM approval                 |
| rumor      | Information believed by some characters    |
| legend     | Mythic or uncertain historical information |
| superseded | Replaced by newer canon                    |

Examples:

```yaml
canon_state: canon
```

```yaml
canon_state: proposed
```

```yaml
canon_state: rumor
```

This field is one of the most important fields in the vault.

Assistants should never treat proposed content as canon.

---

## 5. Status Vocabularies

Status values are controlled vocabularies.

Only use approved values.

## NPC

```text
alive
dead
missing
unknown
```

## Character

```text
active
retired
dead
missing
```

## Faction

```text
active
dormant
disbanded
destroyed
```

## Location

```text
active
ruined
abandoned
hidden
lost
```

## Mystery

```text
hidden
suspected
investigated
partially-resolved
resolved
```

## Item

```text
held
lost
destroyed
sought
unknown
```

## Quest

```text
open
active
completed
failed
abandoned
```

## Infrastructure Host

```text
active
offline
decommissioned
```

## ADR

```text
proposed
accepted
superseded
deprecated
```

## Vehicle

```text
owned
sold
retired
```

## Warranty

```text
active
expired
claimed
void
```

## Home Project

```text
planned
active
on-hold
done
abandoned
```

---

## 6. Session Tracking

Campaign entities should track their appearance history.

Recommended fields:

```yaml
first_appearance:
last_appearance:
related_sessions: []
```

Example:

```yaml
first_appearance: "[[Sessions/Session 03]]"

last_appearance: "[[Sessions/Session 08]]"

related_sessions:
  - "[[Sessions/Session 03]]"
  - "[[Sessions/Session 08]]"
```

This allows future assistants to answer questions such as:

* Which NPCs have not appeared recently?
* Which faction has been most active?
* Which locations are currently relevant?

---

## 7. Relationship Standards

Relationships should be explicit whenever possible.

Example:

```yaml
relationships:
  - target: "[[NPCs/Captain Vael]]"
    status: ally

  - target: "[[Factions/The Ash Wardens]]"
    status: hostile
```

Allowed relationship states:

```text
ally
friendly
neutral
strained
hostile
enemy
```

Relationship data is more valuable than descriptive prose alone.

---

## 8. Tag Vocabulary

## Template Tags

Every template supplies its own type tags.

Examples:

```yaml
tags:
  - campaign
  - npc
```

```yaml
tags:
  - household
  - warranty
```

Do not remove type tags.

### Structural Tags

In addition to template type tags, the following structural tags are approved. They mark a note's role in the vault, not a plot topic.

```text
campaign-bible
gm-prep
constitution
```

`campaign-bible` marks foundational canon notes (Tone & Themes, Overview, and similar load-bearing reference). `gm-prep` marks notes written as referee preparation rather than in-world canon. `constitution` marks the single Campaign Constitution — the top design authority the other bible notes defer to.

New structural tags should be added here before use.

---

## Campaign Tags

Use only approved topical tags.

```text
#main-plot
#side-plot
#recurring
#unresolved
#mystery
#rumor
#artifact
#ancient
#frontier
#political
#religious
#military
#dangerous
#lost
#legendary
#secret
#player-created
```

New tags should be added here before use.

---

## 9. Folder Standards

Campaign notes belong in the following locations.

## Characters

```text
10-Campaign/Characters/
```

## NPCs

```text
10-Campaign/NPCs/
```

## Factions

```text
10-Campaign/Factions/
```

## Regions

```text
10-Campaign/Locations/Regions/
```

## Settlements

```text
10-Campaign/Locations/Settlements/
```

## Wilderness

```text
10-Campaign/Locations/Wilderness/
```

## Dungeons

```text
10-Campaign/Locations/Dungeons/
```

## Cultures

```text
10-Campaign/Lore/Cultures/
```

## History

```text
10-Campaign/Lore/History/
```

## Mysteries

```text
10-Campaign/Lore/Mysteries/
```

## Religions

```text
10-Campaign/Lore/Religions/
```

Folder placement matters.

Knowledge bases, assistants, dashboards, and retrieval systems use folder boundaries to determine context.

---

## 10. Naming Standards

Use Title Case.

Good:

```text
Captain Vael.md
Whisperbridge.md
The Ash Wardens.md
```

Bad:

```text
captain_vael.md
captain-vael.md
npc01.md
```

The filename should represent the primary identity of the note.

Session notes are the only exception.

Examples:

```text
Session 01.md
Session 14.md
Session 37.md
```

---

## 11. Summary Rule

Every note should contain a Summary section.

The Summary is the most important retrieval chunk in the vault.

Target length:

75–200 words

A Summary should answer:

* What is this?
* Why does it matter?
* How does it connect to the wider world?

The Summary must stand alone.

The Summary is a body section (`## Summary`) only.

It must never appear as a frontmatter key. Frontmatter holds structured fields; the Summary is standalone prose and belongs in the note body, where retrieval indexes it as its own chunk. A note whose frontmatter contains a `summary:` key fails validation.

Good summaries are written as complete prose.

Avoid:

* Bullet lists
* Fragmented notes
* Context-dependent references

Assistants frequently retrieve the Summary before any other content.

---

## 12. Assistant Compatibility Rule

Anything an assistant must know later should exist as explicit text.

Avoid:

* Information implied by structure alone
* Information only visible in images
* Information only present in filenames

Prefer:

* Frontmatter
* Wikilinks
* Summary paragraphs
* Relationship sections
* Explicit notes

The easier a fact is to retrieve, the more useful it becomes.

---

## 13. Worldbuilding Principle

Every campaign note should create future play opportunities.

Whenever possible include:

* A mystery
* A tension
* A relationship
* A consequence
* A question

The world should feel:

* Ancient
* Layered
* Connected
* Dangerous
* Discoverable

Avoid isolated lore.

Prefer interconnected lore.

Every note should connect to something else.

---

## 14. Quick Reference

| Convention              | Rule                                  |
| ----------------------- | ------------------------------------- |
| Aliases                 | Record alternate names                |
| Wikilinks               | Use links for all relationships       |
| Canon State             | Distinguish canon from drafts         |
| Status                  | Use approved values only              |
| Tags                    | Use controlled vocabulary             |
| Relationships           | Record explicit connections           |
| Session Tracking        | Track appearances                     |
| Folders                 | Place notes in correct folders        |
| Naming                  | Use Title Case                        |
| Summary                 | 75–200 word standalone paragraph      |
| Assistant Compatibility | Make important facts explicit         |
| Worldbuilding           | Create future adventure opportunities |

---

## Final Principle

The vault is the source of truth.

If something matters:

Write it down.

If something connects:

Link it.

If something changes:

Update the note.

A world becomes easier to run, easier to search, and easier for assistants to understand when every note follows the same conventions.
