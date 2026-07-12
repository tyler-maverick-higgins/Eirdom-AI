---
type: warranty
name: "<% tp.file.title %>"
aliases: []
status: active          # active | expired | claimed | void (see 99-Meta/Field-Conventions)
item: "[[]]"            # what it covers — link the appliance/system note if one exists
brand: 
model: 
serial: 
purchase_date:          # YYYY-MM-DD
expires:                # YYYY-MM-DD — the date the filter/query cares about
provider:               # who honors it — manufacturer, retailer, third party
receipt:                # link or path to the receipt/proof of purchase
tags: [household, warranty]
created: "<% tp.date.now('YYYY-MM-DD') %>"
---

# <% tp.file.title %>

## Summary
One paragraph the assistant can retrieve: what this covers, until when, and how to claim it.

## Coverage
What the warranty includes and excludes — parts, labor, accidental damage, etc.

## How to Claim
The steps and contact details to make a claim. Phone, portal, what they'll ask for.

## Notes
- Registration confirmation, extended-warranty terms, anything worth remembering.
