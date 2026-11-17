# Runbook: Batch Settlement Job Recovery

Owner: Payments Engineering
Systems: batch-01
Tier: 1

## Purpose
The batch-settlement job runs nightly at 01:00 CT on batch-01. It reads the day's transactions from pg-prod-01
and sends settlement files to the clearing partner. A failed run delays merchant payouts.

## Pre-checks
1. Check the job status in the scheduler: `ctl status settlement-nightly`.
2. Check the last log lines in `/var/log/settlement/nightly.log` for the failing step.

## Procedure
1. If the job failed before the "file transmitted" step, rerun it with `ctl rerun settlement-nightly --from-checkpoint`.
2. If the job failed after transmission, do not rerun. Duplicate settlement files cause double payouts.
   Open a Sev 2 incident and contact the clearing partner.
3. Never change the database or patch batch-01 between 00:30 and 04:00 CT.

## Validation
- The scheduler shows `SUCCESS` for settlement-nightly.
- The clearing partner acknowledgement file arrives in `/data/settlement/acks/`.

## Rollback
There is no rollback for a transmitted file. Work with the clearing partner to reverse duplicates.

## Expected duration
The job normally takes 90 minutes.
