# ADR 0001: Dimensional Model Strategy

## STATUS

Accepted — conceptual design, 2026-09-08. Physical implementation remains deferred.

## CONTEXT

LeadPulse must connect MQL acquisition, successful seller onboarding, seller activation, downstream Order Item GMV, and future synthetic spend. The sources have different grains, multi-item and multi-seller Orders, only successful Closed Deals, and a seller bridge that is incomplete across public snapshots.

Putting acquisition fields and activation metrics on a seller dimension would mix events with entity descriptors. Using Order-level payments for seller GMV or joining raw facts directly would create duplication. Campaign and EndCustomer are not valid acquisition dimensions for the MVP.

## DECISION

Use a dimensional constellation with:

- event facts `fct_mql`, `fct_closed_deal`, and `fct_order_item`;
- derived versioned snapshot `fct_seller_lifecycle` at one acquired seller per cutoff/rule/source-snapshot version;
- future `fct_marketing_spend` at date, source_origin, and scenario grain;
- conformed `dim_date`, `dim_origin`, and `dim_seller`;
- `fct_order_item` as the central downstream transaction fact;
- no separate `fct_order` in the MVP;
- acquisition context propagated to downstream facts through governed seller lineage, not stored as intrinsic seller attributes.

Cross-fact KPIs aggregate each component to conformed date/origin/cohort grain before division. Campaign, EndCustomer, Product, Geography, Business Segment, and Lead Profile do not become active MVP dimensions merely because source columns or files exist.

## ALTERNATIVES CONSIDERED

1. **Current lifecycle row overwritten at each cutoff:** rejected because it is simpler operationally but cannot reproduce historical as-of metrics without external state.
2. **One wide seller table:** rejected because it would place won_date, origin, maturity, activation, and mutable cutoff-dependent results on a descriptive dimension.
3. **One accumulating MQL fact containing the close:** rejected because sparse outcome fields would blur two event grains and make successful-close counting less explicit.
4. **Separate fct_order and fct_order_item:** rejected for the MVP because seller-attributed GMV lives at item grain and Order counting still requires non-additive handling across sellers.
5. **Compute activation independently in every mart/report:** rejected because first-event, eligibility, maturity, and cutoff rules would drift.
6. **Direct fact-to-fact joins for ratios:** rejected because joins at unequal grains can multiply observations; components instead aggregate through conformed dimensions.

## CONSEQUENCES

- Acquisition events, seller descriptions, and lifecycle outcomes have explicit ownership.
- GMV remains additive at seller-assigned Order Item grain.
- Order counts require distinct semantics and cannot be summed from item rows.
- Published lifecycle rows are immutable; a new cutoff, rule, or source snapshot creates a new version, and consumers must select exactly one version.
- Acquisition cohort/origin context is deliberately propagated to downstream facts to avoid fragile consumption-time fact joins.
- Deferred dimensions can be introduced only when a business question and source contract justify them.
- Physical database, SQL, dbt, indexing, partitioning, and incremental decisions remain open for a later phase.
