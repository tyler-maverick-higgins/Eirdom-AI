---
type: record
name: "<% tp.file.title %>"
aliases: []
status: current         # current | expired | superseded
record_type:            # insurance | identity | property | medical | financial | other
issuer:                 # who issued it
expires:                # YYYY-MM-DD, if it expires — renewal-reminder field
physical_location:      # where the actual document lives — safe, drawer, file
tags: [household, record]
created: "<% tp.date.now('YYYY-MM-DD') %>"
---

# <% tp.file.title %>

## Summary
One paragraph the assistant can retrieve: what this record is, who it's for, when it renews.

## Key Details
The non-sensitive facts worth having on hand — policy/document type, coverage, renewal terms.
**Do NOT store full account numbers, SSNs, card numbers, or passwords here** (see caution below).

## Renewal / Action
- What to do and when — renewal dates, who to contact, what's needed.

## Notes
- 

<!-- SENSITIVE-DATA CAUTION:
     This note is read by the local assistant via RAG. Keep it to what you'd be
     comfortable the assistant retrieving and quoting. Record WHERE a sensitive
     document is and WHEN it renews — not the secret numbers themselves. Account
     numbers, SSNs, card numbers, and passwords belong in the password manager,
     never in vault text. Same gate as Actual Budget in Volume 9: convenience is
     not a reason to expose sensitive data to an automated system. -->
