---
type: adr
name: "<% tp.file.title %>"
aliases: []
adr_number:             # e.g. ADR-024 — keep the running series
status: accepted        # proposed | accepted | superseded | deprecated
decision_date:          # YYYY-MM-DD
supersedes:             # ADR number this replaces, if any
related: []             # [[links]] to affected hosts, services, other ADRs
tags: [infrastructure, adr, decision]
created: "<% tp.date.now('YYYY-MM-DD') %>"
---

# <% tp.file.title %>

## Summary
One paragraph the Copilot can retrieve: the decision made and why, in plain language.
This is what answers "why did we do it this way" months from now.

## Context
The situation and forces at play — what problem or constraint prompted a decision.

## Decision
What was decided. State it plainly and unambiguously.

## Alternatives Considered
- The options that were weighed and **why each was rejected**. This is the heart of an ADR —
  the rejected paths are as valuable as the chosen one.

## Consequences
What this decision causes — the tradeoffs accepted, what becomes easier, what becomes harder,
what it commits you to.

<!-- ADRs are the documentation-first dividend (Volume 6): they record the WHY,
     not just the WHAT, which is what lets the Copilot explain the homelab rather
     than merely recite it. Keep them mostly prose — semantic search, not grep,
     answers "why" questions. -->
