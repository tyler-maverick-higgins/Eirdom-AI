---
type: home-system
name: "<% tp.file.title %>"
aliases: []
status: active          # active | replaced | removed
system_type:            # furnace | water-heater | hvac | well | septic | sump | appliance | other
brand: 
model: 
serial: 
location:               # where in the home — basement, garage, kitchen
installed:              # YYYY-MM-DD
warranty_expires:       # YYYY-MM-DD — folded in; a separate Warranty note is optional
tags: [household, home-system]
created: "<% tp.date.now('YYYY-MM-DD') %>"
---

# <% tp.file.title %>

## Summary
One paragraph the assistant can retrieve: what this is, where it is, and what it needs to keep running.

## Specifications
The numbers you'll actually be asked for — filter size, fuel type, capacity, model/serial, settings.

## Maintenance
- What it needs and how often — filter changes, flushes, inspections. The recurring care.

## Service History
<!-- newest entries appended below; one line per service: date — what — who -->
- 

## Manuals & Support
- Links to the manual, the installer/servicer contact, parts sources.

## Notes
- 

<!-- This one note covers an appliance OR a home system, with warranty fields built in.
     Keep a SEPARATE Warranty note only when the warranty covers something that
     isn't a system/appliance, or when you want to track a standalone policy.
     One fact, one home — don't duplicate the fridge's identity across two notes. -->
