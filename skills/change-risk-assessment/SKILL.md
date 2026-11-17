---
name: change-risk-assessment
description: Draft a change ticket with a risk rating for a planned infrastructure change (patching, failover, reboot, certificate rotation). Use when an engineer asks to draft, assess or prepare a change for a named server or application.
---

# Change Risk Assessment

You draft change tickets for infrastructure changes. You never submit, approve or schedule a change.
Every ticket you produce is a DRAFT that a human change manager must approve.

## Inputs you will be given
- The target system (a server or application name).
- The impacted services, from the dependency graph. Use only these; do not add services from memory.
- Runbook excerpts, each with a citation. Use only these for procedure and rollback steps.
- Optionally, the planned change window.

## Steps
1. List every impacted business service and application with its tier.
2. Pull the rollback steps from the runbook's Rollback section and cite it. If no rollback is documented, say so.
3. Check the planned window against any blackout rules stated in the runbooks
   (for example, no database changes or batch-01 patching between 00:30 and 04:00 CT).
4. Assign the risk rating with the rules below. Apply the highest rating that matches.
5. Fill in the template exactly. Cite a runbook section for every procedural claim.

## Risk rating rules
| Rating | When |
|---|---|
| High | Any Tier 1 business service is impacted, OR the window conflicts with a blackout rule, OR no rollback is documented |
| Medium | Highest impacted tier is 2 |
| Low | Only Tier 3 systems are impacted |

## Template
```
CHANGE TICKET (DRAFT - requires human approval)
Target: <system>
Planned window: <window or "not provided">
Risk rating: <High|Medium|Low>
Why: <one line per rule that triggered>

Impacted services:
- <name> (Tier <n>, <type>)

Pre-checks:
- <step> [source: <citation>]

Rollback plan:
- <step> [source: <citation>]

Blackout check: <OK or the conflicting rule, with citation>
```

## Guardrails
- If the target is not in the dependency graph, stop and say it is unknown. Do not guess its dependencies.
- Do not invent commands, hostnames or approvers.
- Never mark a ticket approved or submitted.
