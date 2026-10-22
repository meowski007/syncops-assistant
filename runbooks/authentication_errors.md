# SRE Runbook: Authentication and Token Invalidation Errors

## Overview
- **Category:** `AUTH_EXPIRED`
- **Severity Classification:** SEV2 (widespread auth failure) / SEV3 (localized token refresh drop)
- **Service:** Identity Token Verifier & Session Gateway
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Symptoms & Detection
- Alert `AuthExpiredSurge`: Sudden elevation in `AUTH_EXPIRED` sync failure events across clients.
- Elevated HTTP 401 Unauthorized responses from sync ingress routers.
- Increased volume of customer support tickets citing "Session Expired" or "Please log in again".

## 2. Immediate Diagnostic Checklist
1. **Check Identity Provider (IdP) Certificate Status:**
   - Verify if an automated TLS or JSON Web Key Set (JWKS) leaf certificate rotation occurred within the last 4 hours.
   - Confirm whether intermediate CA certificates are properly cached by the sync authentication proxy.
2. **Inspect Token Lifetime Settings:**
   - Verify if OAuth access token TTL or refresh token sliding window configuration was inadvertently reduced.
3. **Analyze Client App Version Breakdown:**
   - Confirm if older client versions lack support for updated signature algorithms (e.g., RS256 vs ES256).

## 3. Mitigation Steps
1. **Refresh JWKS Key Cache:**
   - Trigger a synchronous reload of the token validator JWKS public key cache across all ingress nodes.
2. **Grace Period Extension:**
   - Temporarily enable a 15-minute token clock-skew grace window on the verification middleware.
3. **Client Session Recovery:**
   - Notify in-app clients via push sync flags to initiate silent refresh token exchange.

## 4. Rollback Strategy
- If an erroneous IdP policy change or token validator binary was deployed, rollback to the previous container build immediately.

## 5. Verification & Recovery Confirmation
- Verify that `AUTH_EXPIRED` error count on `sync_events` returns to baseline (< 0.2% of total traffic).
- Check that customer ticket volume under `AUTH_ERROR` decreases to normal levels.
- Confirm token verification latency p99 is under 15ms.
