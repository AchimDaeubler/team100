---
id: SPEC-042
title: "Add batch payment endpoint"
category: feature
owner: Daniel Benedetti                          # git config user.name
authored_by: augmented
---

## Problem statement

Finance teams process payments individually through `POST /payments`, requiring one API call per payment. For month-end reconciliation, this means hundreds of sequential calls. A batch endpoint reduces client-side complexity and network overhead.

## Acceptance criteria

1. `POST /payments/batch` accepts an array of payment objects and returns `201` with a summary response
2. Request body follows the schema in `resources/batch-payment-api.md`
3. Validation rejects requests where any payment has `amount <= 0`, returning `400` with per-item errors
4. Partial failures are not supported — the batch is atomic (all succeed or all fail)
5. Batch size is limited to 100 items; requests exceeding this return `413`
6. All new endpoints have integration tests using the existing `@SpringBootTest` setup

## User scenarios

- *Month-end reconciliation:* Finance operator uploads a CSV of payments to the internal tool. The tool transforms the CSV to a batch API call. If any payment fails validation, the entire batch is rejected and the operator fixes the CSV.
- *Automated disbursement:* Background job creates a batch of approved payments and submits them atomically. Success triggers ledger update; failure triggers alert.

## Research

- `BatchInvoiceController.java` uses atomic batch pattern with `@Transactional` on the service method. Reuse this approach.
- No existing batch endpoint for payments — net new.
- `Payment.java:34-52` already has `amount`, `currency`, `referenceId` fields. No schema migration needed.
- API gateway rate limit: 100 req/s per client. Batch counts as 1 request.
- Reviewed SPEC-031 (single payment endpoint) for consistency.

## Scope boundaries

- Partial batch success (saga pattern) out of scope
- Batch scheduling is a separate spec
- No legacy endpoint changes
- Performance optimization for batches >100 items is follow-up

## Implementation guidance

- **Files likely affected:** `PaymentController.java`, `BatchPaymentRequest.java` (new), `BatchPaymentResponse.java` (new), `PaymentService.java`, `PaymentControllerTest.java`, `BatchPaymentIntegrationTest.java` (new)
- **Files NOT to modify:** `LegacyPaymentController.java`
- **Patterns to follow:** Controller structure from `OnAccountCreditController.java`, validation via `FinanceValidator.validate()`, integration tests from `OnAccountCreditIntegrationTest.java`
- **NFRs:** Batch of 100 items within 5 seconds under normal load. All errors follow `ErrorResponse` schema.
