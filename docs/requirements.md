# Ops Knowledge Copilot: Product Requirements (POC)

How this POC was scoped, using SAFe artifacts. The code, eval set and CI gate in this repo implement these requirements.

## Problem
Infrastructure engineers spend about 30 minutes per change searching runbooks, tickets and the CMDB.
Missed dependencies cause change-related incidents.

## Epic hypothesis
**For** infrastructure and SRE engineers **who** need to assess change risk quickly, **the** Ops Knowledge Copilot
**is an** AI assistant **that** answers runbook and dependency questions with cited sources and drafts change tickets.
**Unlike** manual search across several tools, **our solution** cuts research time and catches hidden dependencies.

| Type | Measure |
|---|---|
| Business outcome | 50% less change-research time; 20% fewer change-caused incidents |
| Leading indicators | Weekly active users, answer acceptance rate, citation click-through |

## AI capability map
| Capability | Job in the product | Where in this repo |
|---|---|---|
| RAG | Retrieve the right runbook section and cite it | `copilot/retriever.py` |
| Knowledge graph | Server → application → business service dependencies | `copilot/graph.py`, `data/graph.json` |
| Agent | Route the question to the right tool and compose the answer | `copilot/agent.py` |
| Claude Skill | Standard change-risk procedure, applied the same way every time | `skills/change-risk-assessment/SKILL.md` |
| LLM (Claude) | Natural-language answers grounded in retrieved text (optional) | `copilot/llm.py` |

## Staged gates
| Stage | Scope | Exit criteria |
|---|---|---|
| **POC (this repo)** | 5 runbooks, 23-node graph, 1 Skill, offline mode | Gates in `evals/run_evals.py`: retrieval recall@3 ≥ 80%, section accuracy ≥ 80%, dependency precision and recall ≥ 90%, refusal accuracy ≥ 90%, 100% of answers cited |
| MVP | Real runbook corpus and CMDB feed, vector search, Claude answers, 3 pilot teams | ≥ 85% answer accuracy, < 5% unsupported claims, p95 latency < 5 s, security review passed |
| Production | SSO, audit logging, monitoring, all infrastructure teams | Model risk review approved, SLOs met, cost per query under budget, support runbook in place |

## Features
| Feature | Benefit hypothesis | Status |
|---|---|---|
| F1: Runbook search with citations | Engineers find procedures 50% faster | POC done |
| F2: Dependency knowledge graph | Catches downstream impacts missed today | POC done |
| F3: Change-risk agent + Skill | Standardizes risk assessments across teams | POC done |
| F4: Eval and CI gate | Quality is measured on every commit, not guessed | POC done |
| F5: Cloud-native deployment and guardrails | Meets bank security and resilience standards | MVP |

## User stories and acceptance criteria
**S1.** As an SRE, I want to ask "what breaks if server X goes down?" so I can scope change impact.
- Lists direct and transitive dependents from the graph, with tiers. *(eval G01–G06)*
- Unknown server → says it is unknown; never guesses. *(eval X01, test `test_unknown_system_is_refused_not_guessed`)*
- Dependency precision and recall ≥ 90%. *(gate)*

**S2.** As an engineer, I want to ask how to do a procedure and get the exact runbook section.
- Returns the matching section with a citation. *(eval R01–R13)*
- No relevant runbook → "I don't know". *(eval X02–X05)*

**S3.** As a change manager, I want a drafted change ticket with a risk rating so assessments are consistent.
- Follows the Skill's risk rules: High / Medium / Low. *(eval T01–T06)*
- Flags windows that conflict with runbook blackout rules. *(eval T01, T06)*
- Always a DRAFT; the agent cannot submit or approve. *(test `test_ticket_is_always_a_draft`)*

## Non-functional requirements (MVP and production)
- **Security:** no customer data in prompts; private endpoints; secrets in a vault; role-based access to runbooks.
- **Governance:** model risk review, versioned prompts and Skills, full audit log of questions and answers.
- **Reliability:** offline/extractive fallback when the LLM API is unavailable (already in the POC).
- **Cost:** token budget per query; cheaper model for simple lookups.
- **Observability:** trace each agent step; rerun the eval suite on every change (CI gate already in the POC).

## Risks (ROAM)
| Risk | Status | Response |
|---|---|---|
| CMDB dependency data is incomplete | Owned | Data engineering enabler to reconcile CMDB with service discovery before MVP |
| Keyword search misses paraphrased questions | Mitigated | Synonym map in POC; vector search in MVP (eval R02 shows the gap) |
| Engineers trust a wrong answer | Mitigated | Citations on every answer, "I don't know" threshold, human approval on tickets |
