---
id: SPEC-044
title: "Extract payment validation into dedicated validator"
category: refactoring
owner: Daniel Benedetti                          # git config user.name
authored_by: augmented
---

## Problem statement

Payment validation logic is scattered across `PaymentController` (request validation), `PaymentService` (business rules), and inline checks in batch processing. Consolidating into a single `PaymentValidator` reduces duplication and makes validation rules testable in isolation.

## Current state

- Request-level validation: `PaymentController.java:45-78` (null checks, type coercion)
- Business rule validation: `PaymentService.java:102-130` (amount ranges, currency support, duplicate detection)
- Batch-specific: will be added by SPEC-042
- Three locations, overlapping rules, no single source of truth

## Target state

- All payment validation in `PaymentValidator.java`
- `PaymentController` calls `PaymentValidator.validateRequest()`
- `PaymentService` calls `PaymentValidator.validateBusinessRules()`
- Batch processing calls both
- Validation rules unit-testable without controller or service context

## Behavioral equivalence

- All existing `PaymentControllerTest` cases pass without modification
- All existing `PaymentServiceTest` cases pass without modification
- New `PaymentValidatorTest` covers every rule extracted
- API responses for invalid inputs remain identical (same status codes, same error shapes)

## Acceptance criteria

1. All payment validation logic consolidated in `PaymentValidator.java`
2. `PaymentController` delegates to `PaymentValidator.validateRequest()`
3. `PaymentService` delegates to `PaymentValidator.validateBusinessRules()`
4. All existing tests pass without modification
5. New `PaymentValidatorTest` covers every extracted rule
6. API error responses are byte-identical to current behavior

## Research

- `FinanceValidator.java` is the established validator pattern in this codebase — use as structural reference.
- Confirmed three separate validation locations via code search.
- No other services depend on the inline validation logic in `PaymentController` or `PaymentService`.

## Scope boundaries

- Does not change any validation logic — only moves it
- Error response format unchanged
- `PaymentService` business logic untouched

## Implementation guidance

- **Files likely affected:** `PaymentController.java` (remove inline validation), `PaymentValidator.java` (new), `PaymentValidatorTest.java` (new)
- **Files NOT to modify:** `PaymentService.java` business logic (only validation extraction)
- **Patterns to follow:** `FinanceValidator.java` structure
