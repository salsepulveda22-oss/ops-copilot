# Runbook: Auth Service TLS Certificate Rotation

Owner: Identity Team
Systems: auth-svc-01, auth-svc-02, lb-ext-01
Tier: 1

## Purpose
Rotate the TLS certificate for the auth-service before it expires. Every customer login to online-banking and the
mobile app goes through auth-service.

## Pre-checks
1. Confirm the new certificate chain validates: `openssl verify -CAfile chain.pem new-cert.pem`.
2. Confirm the certificate expiry is at least 30 days away so there is time to roll back.

## Procedure
1. Upload the new certificate to the secrets vault under `auth/tls/current`.
2. Drain auth-svc-01 from the external load balancer lb-ext-01.
3. Restart auth-svc-01 so it loads the new certificate, then return it to the pool.
4. Repeat for auth-svc-02.

## Validation
- `curl -v https://auth.example.internal/healthz` shows the new certificate serial number.
- Login success rate stays above 99% for 30 minutes.

## Rollback
Restore the previous certificate version in the vault (`auth/tls/previous`) and restart each node one at a time.

## Expected duration
About 30 minutes with no customer downtime.
