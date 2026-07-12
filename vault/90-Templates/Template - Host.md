---
type: host
name: "<% tp.file.title %>"
aliases: []
status: active          # active | offline | decommissioned
hostname:               # exact hostname — e.g. EIRDOM-DC-01
ip:                     # exact IP — e.g. 10.1.10.10 (or "none — air-gapped")
vlan:                   # VLAN number/name — e.g. 10 (Corporate)
role:                   # what it does — AD DS, Docker host, Wazuh manager, etc.
os:                     # exact OS + version
host_type:              # vm | physical | container-host | appliance
hypervisor: "[[]]"      # if a VM, link the Proxmox host note
tags: [infrastructure, host]
created: "<% tp.date.now('YYYY-MM-DD') %>"
---

# <% tp.file.title %>

## Summary
One paragraph the Copilot can retrieve: what this host is, where it sits on the network, what it runs.
State exact identifiers here as plain text so they are retrievable verbatim.

## Specifications
Resources and placement — vCPU/RAM/disk (or hardware), VLAN, switch port, rack/location.

## Services & Roles
- What runs on it, with exact names — services, ports, the GPOs or configs that apply.

## Access & Dependencies
- How it's reached, what it depends on, what depends on it. Link related [[hosts]].

## Maintenance & Notes
- Backup coverage, update cadence, quirks. Link the relevant [[Decisions/]] (ADRs).

<!-- Exact strings matter here. The Infrastructure Copilot favors grep-style retrieval
     for literal identifiers (Volume 6) and must quote IPs/hostnames/ports verbatim.
     Write them as plain text in the body, not only in a table, so chunking can't
     orphan a value from its label. -->
