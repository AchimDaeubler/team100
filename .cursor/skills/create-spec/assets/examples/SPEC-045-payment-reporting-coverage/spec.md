---
id: SPEC-045
title: "Add integration test coverage for payment reporting"
category: testing
owner: Daniel Benedetti                          # git config user.name
authored_by: augmented
---

## Problem statement

`ReportingService` has zero integration test coverage. Unit tests mock the database layer, so query correctness and transaction behavior are untested. Two production bugs in the last month (SPEC-039, SPEC-043) originated in reporting queries that passed unit tests but failed with real data.

## Coverage targets

- `ReportingService.generateDailySummary()` — date range queries, timezone handling, empty-result behavior
- `ReportingService.generatePaymentBreakdown()` — grouping by currency, null currency handling, large dataset pagination
- `ReportingController` endpoint integration — request parsing, response shape, error cases
- **Priority:** `generateDailySummary` (highest risk, caused SPEC-039), then `generatePaymentBreakdown`, then controller integration

## Acceptance criteria

1. Integration tests exist for `ReportingService.generateDailySummary()` covering date ranges, timezones, and empty results
2. Integration tests exist for `ReportingService.generatePaymentBreakdown()` covering currency grouping, nulls, and pagination
3. `ReportingController` endpoint tests cover request parsing, response shape, and error cases
4. All tests use `@SpringBootTest` with `@Testcontainers` (existing pattern)
5. Test fixtures created in `ReportingFixtures.java` following `PaymentFactory.java` pattern

## Test infrastructure

- **Framework:** `@SpringBootTest` with `@Testcontainers` for Postgres (existing pattern in `test/integration/`)
- **Fixtures:** Create `ReportingFixtures.java` following `PaymentFactory.java` pattern
- **Seed data:** 100 payments across 5 currencies, 3 date ranges, including edge cases
- **Run:** `mvn test -pl payments-service -Dtest='*IntegrationTest'`

## Research

- Confirmed zero integration test coverage for `ReportingService` via coverage report.
- `test/integration/` directory has established `@Testcontainers` pattern — reuse directly.
- `PaymentFactory.java` is the established fixture pattern.
- SPEC-039 and SPEC-043 both traced to reporting queries that unit tests couldn't catch.

## Scope boundaries

- No changes to production code
- No unit tests — this spec is specifically for integration coverage
- Performance testing is out of scope

## Implementation guidance

- **Files likely affected:** `ReportingServiceIntegrationTest.java` (new), `ReportingControllerIntegrationTest.java` (new), `ReportingFixtures.java` (new)
- **Files NOT to modify:** `ReportingService.java`, `ReportingController.java` (no production changes)
- **Patterns to follow:** `OnAccountCreditIntegrationTest.java` structure, `PaymentFactory.java` fixture pattern
