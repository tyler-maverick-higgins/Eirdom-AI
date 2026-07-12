# Template Type: Bible

This is the authoritative template for **campaign-bible notes** — the foundational design, premise, and GM-prep documents that define the campaign itself (e.g. Tone & Themes, Overview, First Session prep).

**Use `type: bible` ONLY for design/premise/prep documents about the campaign.**
In-world canon — a place, a person, a faction, a myth, an item — must use its proper typed template (location, settlement, region, npc, character, faction, lore, mystery, etc.). The `bible` type is intentionally loose (only a Summary is required) because these are human-authored design docs with no shared fixed structure; it is **not** a general-purpose escape from structure. The gate enforces this by requiring a `campaign-bible` or `gm-prep` structural tag on every bible note.

Do not alter the metadata field set. Add free-form `## ` sections as the document needs; only `## Summary` is required.

---

type: bible
name: "<% tp.file.title %>"
aliases: []

canon_state: canon

tags:

* campaign
* campaign-bible

created: "<% tp.date.now('YYYY-MM-DD') %>"
updated:

relationships: []

first_appearance:
last_appearance:

related_sessions: []

---

# <% tp.file.title %>

## Summary

One self-contained paragraph stating what this document is, what it governs, and why it matters to the campaign. This is the required retrieval anchor; everything below it is free-form.

<!--
After the Summary, structure the document however it needs to be structured —
these are design/premise/prep docs and do not share a fixed shape. Add any
`## ` sections that serve the document.

Required tag: every bible note must carry `campaign-bible` OR `gm-prep` in tags
(the gate enforces this). Use `gm-prep` for referee-prep documents (e.g. a first
session plan) and `campaign-bible` for load-bearing reference (tone, premise).

GM-only content: wrap in <!-- GM-ONLY:START --> ... <!-- GM-ONLY:END --> so it
is stripped before ingestion into the assistant knowledge base.
-->
