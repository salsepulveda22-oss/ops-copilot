# Eval report: POC gate

**Gate result: PASS** (33/34 cases passed, offline mode)

| Metric | Score | POC gate | Result |
|---|---|---|---|
| Runbook source found in top 3 (recall@3) | 100% | >= 80% | PASS |
| Runbook section correct (top 1) | 92% | >= 80% | PASS |
| Dependency recall | 100% | >= 90% | PASS |
| Dependency precision | 100% | >= 90% | PASS |
| Change ticket risk rating correct | 100% | >= 80% | PASS |
| Blackout conflicts detected correctly | 100% | >= 100% | PASS |
| Refuses when it should ('I don't know') | 100% | >= 90% | PASS |
| Answers when it should (no false refusals) | 100% | >= 90% | PASS |
| Answers that carry a citation | 100% | >= 100% | PASS |

## Cases

| ID | Type | Question | Result |
|---|---|---|---|
| R01 | runbook | What is the rollback for the postgres failover? | PASS |
| R02 | runbook | How do I rotate the auth certificate? | FAIL |
| R03 | runbook | How do I patch the kafka brokers? | PASS |
| R04 | runbook | What should I check before refreshing UAT? | PASS |
| R05 | runbook | How long does the settlement job take? | PASS |
| R06 | runbook | How do I verify the postgres failover worked? | PASS |
| R07 | runbook | The settlement job failed after the file was transmitted. Should I rerun it? | PASS |
| R08 | runbook | How do I roll back a kafka patch if a broker does not rejoin the cluster? | PASS |
| R09 | runbook | How much write downtime does payments-api have during a database failover? | PASS |
| R10 | runbook | How do I validate that the new auth certificate is live? | PASS |
| R11 | runbook | What should I check before patching kafka, like under-replicated partitions? | PASS |
| R12 | runbook | Before a UAT refresh, can unmasked production data be loaded? | PASS |
| R13 | runbook | When does the nightly settlement job run and what does it send? | PASS |
| G01 | impact | What breaks if pg-prod-01 goes down? | PASS |
| G02 | impact | What is impacted if kafka-prod-02 goes down? | PASS |
| G03 | impact | What breaks if auth-svc-01 goes down? | PASS |
| G04 | impact | Which services are affected if batch-01 is rebooted? | PASS |
| G05 | impact | What breaks if pg-uat-01 goes down? | PASS |
| G06 | impact | What is downstream of lb-ext-01? | PASS |
| G07 | dependencies | What does payments-api depend on? | PASS |
| G08 | dependencies | What does online-banking depend on? | PASS |
| T01 | change_ticket | Draft a change ticket to patch pg-prod-01 at 02:00 | PASS |
| T02 | change_ticket | Draft a change ticket to patch pg-uat-01 | PASS |
| T03 | change_ticket | Draft a change ticket to restart notifications | PASS |
| T04 | change_ticket | Draft a change ticket to patch kafka-prod-01 at 14:00 | PASS |
| T05 | change_ticket | Draft a change ticket to reboot app-uat-01 at 02:00 | PASS |
| T06 | change_ticket | Draft a change ticket to patch batch-01 at 01:15 | PASS |
| X01 | refusal | What breaks if db-legacy-09 goes down? | PASS |
| X02 | refusal | What is the vacation policy for engineers? | PASS |
| X03 | refusal | How do I restart the mainframe CICS region? | PASS |
| X04 | refusal | What is the procedure for a kubernetes upgrade? | PASS |
| X05 | refusal | How do I reset my VPN password? | PASS |
| X06 | refusal | Draft a change ticket for the coffee machine | PASS |
| X07 | refusal | Draft a change ticket to patch web-prod-07 | PASS |
