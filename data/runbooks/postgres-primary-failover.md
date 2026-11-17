# Runbook: PostgreSQL Primary Failover (pg-prod-01)

Owner: Database Platform Team
Systems: pg-prod-01 (primary), pg-prod-02 (replica)
Tier: 1

## Purpose
Promote the replica pg-prod-02 to primary when pg-prod-01 must be patched, rebooted, or has failed.
The payments-api and the batch-settlement job both write to this database.

## Pre-checks
1. Confirm replication lag on pg-prod-02 is under 5 seconds: `SELECT now() - pg_last_xact_replay_timestamp();`
2. Confirm no batch-settlement run is in progress. Failover during settlement can leave partial ledger writes.
3. Announce the maintenance window in #ops-changes at least 24 hours ahead for Tier 1 systems.

## Procedure
1. Put payments-api into read-only maintenance mode with the feature flag `payments.write_enabled=false`.
2. Run `patronictl switchover --master pg-prod-01 --candidate pg-prod-02`.
3. Verify the new primary accepts writes: `SELECT pg_is_in_recovery();` must return false.
4. Update the connection pooler (pgbouncer) target and reload it.
5. Re-enable writes with `payments.write_enabled=true`.

## Validation
- payments-api health check `/healthz` returns 200.
- Error rate on payments-api stays under 0.5% for 15 minutes.

## Rollback
If the new primary fails validation, run `patronictl switchover --master pg-prod-02 --candidate pg-prod-01`
to switch back, reload pgbouncer, and keep payments-api in read-only mode until the on-call DBA confirms data consistency.

## Expected duration
About 20 minutes, including about 2 minutes of write downtime for payments-api.
