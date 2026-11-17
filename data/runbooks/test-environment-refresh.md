# Runbook: Test Environment Data Refresh (UAT)

Owner: Release Engineering
Systems: pg-uat-01, app-uat-01
Tier: 3

## Purpose
Refresh the UAT database from a masked production snapshot so testers work with realistic data.
No customer-facing services depend on UAT.

## Pre-checks
1. Confirm the snapshot has passed the data-masking job. Unmasked production data must never be loaded into UAT.
2. Tell the QA channel at least 2 hours ahead because UAT will be unavailable during the refresh.

## Procedure
1. Stop app-uat-01.
2. Restore the masked snapshot to pg-uat-01 with `pg_restore --clean`.
3. Run the post-refresh script `reset_test_accounts.sql` to recreate test logins.
4. Start app-uat-01.

## Validation
- Smoke tests in the UAT pipeline pass.

## Rollback
Restore the previous UAT snapshot, which is kept for 7 days.

## Expected duration
About 1 hour.
