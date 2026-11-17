# Runbook: Kafka Broker Rolling Patch (kafka-prod-01..03)

Owner: Messaging Platform Team
Systems: kafka-prod-01, kafka-prod-02, kafka-prod-03
Tier: 1

## Purpose
Apply OS and JVM patches to the Kafka cluster one broker at a time without losing messages.
The fraud-scoring service and the notifications service consume from this cluster.

## Pre-checks
1. Confirm there are no under-replicated partitions: `kafka-topics.sh --describe --under-replicated-partitions` returns nothing.
2. Confirm consumer lag for the `fraud-events` topic is under 1,000 messages.

## Procedure
1. Patch one broker at a time. Stop the broker with a controlled shutdown so partition leadership moves first.
2. Apply patches and reboot the host.
3. Start the broker and wait until under-replicated partitions return to zero.
4. Repeat for the next broker. Never have two brokers down at once.

## Validation
- Under-replicated partitions equal zero.
- fraud-scoring consumer lag returns under 1,000 within 10 minutes.

## Rollback
If a broker does not rejoin the cluster within 15 minutes, stop the rollout, restore the previous OS image from the
golden snapshot, and page the Messaging on-call. Do not patch the remaining brokers.

## Expected duration
About 45 minutes per broker.
