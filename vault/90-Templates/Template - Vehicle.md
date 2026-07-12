---
type: vehicle
name: "<% tp.file.title %>"
aliases: []
status: owned           # owned | sold | retired (see 99-Meta/Field-Conventions)
make: 
model: 
year: 
vin: 
plate: 
purchased:              # YYYY-MM-DD
tags: [household, vehicle]
created: "<% tp.date.now('YYYY-MM-DD') %>"
---

# <% tp.file.title %>

## Summary
One paragraph the assistant can retrieve: which vehicle this is, who drives it, its current state.

## Specifications
The vitals worth having on hand — engine, oil type/capacity, tire size, battery group, key codes.

## Service History
<!-- newest entries appended below; one line per service: date — what — mileage -->
- 

## Maintenance Schedule
- Recurring items and when they're due — oil, tires, registration, inspection.

## Documents & Coverage
- Registration, insurance, title location, and any [[Warranties/]] or service plans.

## Notes
- 
