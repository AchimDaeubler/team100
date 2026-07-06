---
id: SPEC-043
title: "Fix currency rounding error in payment summaries"
category: bug
owner: Daniel Benedetti                          # git config user.name
authored_by: automated
---

## Problem statement

Payment summary totals show values like `$1,499.999999997` instead of `$1,500.00`. Reported via production observability alert. Affects all payment summary views when the sum of line items produces floating-point artifacts.

## Acceptance criteria

1. `PaymentSummaryService.calculateTotal()` returns values rounded to 2 decimal places using `CurrencyUtils.round()`
2. Summary totals in API responses never contain more than 2 decimal places
3. Existing tests for `PaymentSummaryService` continue to pass
4. New test case covers the floating-point edge case: sum of `[499.99, 500.00, 500.01]` returns `1500.00`

## Reproduction

- **Input:** Three payment line items with amounts `499.99`, `500.00`, `500.01`
- **Actual output:** Summary total `1499.9999999999998`
- **Expected output:** Summary total `1500.00`
- **Environment:** Production, Java 17, all currency types affected

## Root cause analysis

`PaymentSummaryService.calculateTotal()` (line 87) uses `double` arithmetic for summing. The `CurrencyUtils.round()` utility exists and is used elsewhere but was missed in this method. Added in commit `a3f2e1d` (2026-03-15) as part of SPEC-038.

## Blast radius

Called by `SummaryController` and `ReportingService`. `CurrencyUtils.round()` is already the standard. No downstream schema changes.

## Research

- Confirmed `CurrencyUtils.round()` is the established pattern (used in 14 other locations).
- `PaymentSummaryService.calculateTotal()` is the only monetary sum using raw `double`.
- SPEC-039 was a similar bug in a different service — same root cause.

## Scope boundaries

- Converting from `double` to `BigDecimal` throughout is a separate refactoring spec
- This fix applies `CurrencyUtils.round()` at the return boundary only

## Implementation guidance

- **Files likely affected:** `PaymentSummaryService.java`, `PaymentSummaryServiceTest.java`
- **Files NOT to modify:** `CurrencyUtils.java` (already correct)
- **Patterns to follow:** Use `CurrencyUtils.round()` — never use `Math.round()` on monetary values
