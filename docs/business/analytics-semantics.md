# MVP Analytics Semantics

## Purpose

This document freezes the semantic rules required to begin dimensional modeling. It does not define physical tables, SQL, pipelines, or published dashboard behavior.

Observed measurements come from the locally profiled Olist copies. Business rules below are LeadPulse decisions and must remain distinguishable from source facts.

## Order eligibility

An **Eligible Order** in the MVP is an Order whose source `order_status` is exactly `delivered`.

The rule prioritizes fulfilled historical activity over forecasts or in-progress transactions:

| Observed status | MVP eligibility | Rationale |
| --- | --- | --- |
| `delivered` | Included | Terminal fulfilled state and strongest available evidence that marketplace activity was realized. |
| `shipped` | Excluded | In transit; delivery and final fulfillment are not yet known. |
| `invoiced` | Excluded | Billing progress does not establish shipment or delivery. |
| `processing` | Excluded | Operationally open and not realized. |
| `approved` | Excluded | Payment/order approval is not fulfillment. |
| `created` | Excluded | Initial state with no evidence of fulfillment. |
| `canceled` | Excluded | Explicit non-fulfillment terminal state. |
| `unavailable` | Excluded | The marketplace could not fulfill the Order. |

Eligibility is governed by final observed status. `order_purchase_timestamp` remains the analytical event timestamp for eligible Order, GMV, and activation calculations. A later source correction to status restates the affected metrics under the normal versioned-correction process.

## GMV contract

The official MVP measure is **GMV (Marketplace Item Value Proxy)**:

```text
GMV(P, d) = SUM(order_items.price)
```

where each included Order Item:

- belongs to an Eligible Order;
- is supplied by an AcquiredSeller;
- has `order_purchase_timestamp` in the half-open period P;
- occurs strictly after that seller's `won_date`; and
- inherits acquisition dimension d through the supplying seller.

This choice preserves seller-level additivity because `price` exists at Order Item grain. `freight_value` is excluded: it is a logistics charge and is reported separately if needed. `payment_value` is not GMV: Payments are at Order/payment-sequence grain, may contain multiple rows or methods, may reflect vouchers or other settlement components, and cannot be allocated safely to a seller without an additional rule. Joining Payments directly to Order Items would risk double counting.

GMV is not Olist corporate revenue, recognized revenue, cash collected, margin, or profit. The source has no explicit currency column; the Brazilian/BRL context is a documented source assumption rather than a row-level currency fact.

## Seller activation

An **Activated Seller within 90 days** is a distinct AcquiredSeller that:

1. is linked through a valid ClosedDeal and `seller_id`;
2. supplies at least one Order Item belonging to an Eligible Order;
3. has that Order's `order_purchase_timestamp` strictly later than `won_date`; and
4. has its first such Order no later than `won_date + 90 days`.

Simple historical presence in Order Items is insufficient. Pre-win activity is rejected. Activity after day 90 remains valid downstream seller performance but does not satisfy the 90-day activation KPI.

### Empirical window analysis

The current source snapshot yields 376 acquired sellers with a post-win delivered Order. Percentiles use linear interpolation over their first eligible Order lag:

| Measure | Observed value |
| --- | ---: |
| Count | 376 |
| Minimum | 3.209745 days |
| P25 | 22.617188 days |
| Median | 44.293131 days |
| P75 | 71.913027 days |
| P90 | 101.939334 days |
| P95 | 117.442888 days |
| Maximum | 188.870972 days |
| Activated within 30 days | 128 (34.042553%) |
| Activated within 60 days | 246 (65.425532%) |
| Activated within 90 days | 322 (85.638298%) |
| Activated within 180 days | 374 (99.468085%) |

The MVP selects **90 days**. It captures most observed activations while retaining 746 of 842 acquired sellers as mature cohorts at the empirical source cutoff. A 60-day window omits over one third of observed activations; 180 days leaves only 460 mature sellers and materially increases censoring. The P90 slightly exceeds 90 days, so the metric is explicitly a time-bounded activation standard, not an estimate of eventual activation.

The empirical cutoff is the maximum observed Order purchase timestamp, `2018-10-17 17:30:18`; it is a reproducible data boundary, not a claimed extraction timestamp. A seller enters the 90-day denominator only when `won_date + 90 days <= cutoff`. In the current copy, 746 sellers are time-mature and 314 activated within 90 days, an observed mature-cohort activation rate of 42.091153%. The remaining 96 sellers are incomplete cohorts and are excluded from the denominator, never counted as non-activated.

Within the mature denominator, no qualifying event means **not activated in the linked public snapshots**, not proof that the seller never transacted in reality. The 462 ClosedDeal sellers absent from the e-commerce seller snapshot remain a material coverage limitation and must be disclosed with the KPI.

## Governed Closed Deal temporal exception

The MVP preserves one observed Closed Deal whose `won_date` is two calendar days before its linked MQL `first_contact_date`. It is classified as `INVALID_SEQUENCE` rather than corrected, excluded, or quarantined. The row remains valid evidence that a Closed Deal occurred and contributes to Closed Deals, Acquired Sellers, and MQL-to-Acquired-Seller conversion.

Sequence-dependent lifecycle metrics must require `temporal_quality_status = 'VALID'`. Time to first order, post-acquisition activation, and activation within 90 days will enforce that policy when `fct_seller_lifecycle` is implemented; no lifecycle result is produced in this stage.

## Acquisition conversion

**MQL to Acquired Seller Conversion Rate** is a first-contact cohort metric:

```text
COUNT_DISTINCT(seller_id linked to a cohort MQL by a valid ClosedDeal,
               with won_date <= reporting_cutoff)
/
COUNT_DISTINCT(mql_id whose first_contact_date is in the cohort)
```

- `first_contact_date` assigns both numerator and denominator to the MQL cohort.
- `won_date` determines whether the conversion was observable by the explicit reporting cutoff; it does not reassign the conversion to a won-date cohort.
- The denominator includes every valid MQL in the cohort, including non-converters.
- Every result is labeled `as of <reporting_cutoff>` because no source-backed conversion maturity SLA exists.
- Cohorts with unequal follow-up may be shown only with their follow-up age and an `INCOMPLETE` quality status. They are not presented as final or compared as equally mature cohorts.
- The full-copy observation is 842 / 8,000 = 10.525% as of the latest observed `won_date`; this is an observed snapshot rate, not proof that every cohort is complete.

## Downstream KPI rules

### Activated Sellers

```text
COUNT_DISTINCT(acquired seller_id meeting the 90-day activation rule)
```

Grain: acquisition Channel and ClosedDeal cohort period. Time basis: `won_date` for cohorting and first eligible `order_purchase_timestamp` for the event. Only mature 90-day cohorts are publishable.

### Seller Activation Rate

```text
Activated Sellers within 90 days / Acquired Sellers with 90 complete observation days
```

Grain and time basis match Activated Sellers. A zero denominator returns null.

### Orders from Acquired Sellers

```text
Overall: COUNT_DISTINCT(eligible order_id with at least one post-win acquired-seller item)
Seller/channel slice: COUNT_DISTINCT(seller_id, order_id) for eligible post-win participation
```

Grain: Order event period, acquisition Channel, and optional AcquiredSeller drilldown. Time basis: `order_purchase_timestamp`. Channel slices are non-additive when an Order has multiple sellers; overall totals deduplicate `order_id`.

### GMV from Acquired Sellers

Uses the official GMV formula in this document. Grain: Order Item event period, acquisition Channel, and AcquiredSeller. Time basis: `order_purchase_timestamp`.

### Orders per Activated Seller

```text
COUNT_DISTINCT(seller_id, order_id for eligible Orders in days (0, 90])
/
COUNT_DISTINCT(Activated Seller within 90 days)
```

Grain: ClosedDeal cohort period and acquisition Channel. Both numerator and denominator use the same mature cohort and 90-day horizon.

### GMV per Activated Seller

```text
SUM(eligible order_items.price in days (0, 90])
/
COUNT_DISTINCT(Activated Seller within 90 days)
```

Grain: ClosedDeal cohort period and acquisition Channel. Both numerator and denominator use the same mature cohort and 90-day horizon.

### Time to First Order

```text
first eligible order_purchase_timestamp - won_date
```

Reported as count, minimum, P25, median, P75, P90, P95, and maximum for Activated Sellers in mature 90-day cohorts. It is not averaged across non-activated sellers.

## Channel and source origin

`source_origin` retains the exact non-null Marketing Funnel `origin` value; source null remains null. The MVP uses only a minimal deterministic `channel` mapping:

| source_origin | channel |
| --- | --- |
| `organic_search` | `organic_search` |
| `paid_search` | `paid_search` |
| `social` | `social` |
| `direct_traffic` | `direct` |
| `email` | `email` |
| `referral` | `referral` |
| `display` | `display` |
| `other_publicities` | `other_publicities` |
| `other` | `other` |
| `unknown` or null | `unattributed` |

No higher-level paid/organic rollup is frozen. `landing_page_id` remains a source context field. Campaign is unavailable for Olist outcomes and is absent from the synthetic spend MVP contract.

## Controlled synthetic Advertising Spend contract

The future synthetic source has one row per `spend_date × source_origin × scenario_id`.

Required fields:

- `spend_date`;
- `source_origin` using an explicitly selected observed non-null origin value;
- `channel` produced only by the mapping above;
- `spend_amount`, finite, non-negative, and represented at currency precision;
- `currency`, fixed to `BRL` for an MVP scenario;
- `scenario_id` and `methodology_version`;
- `generation_seed`;
- `data_classification = SYNTHETIC`.

Generation must be deterministic for the same seed and methodology version, preserve the declared date/origin grain, avoid duplicate keys, and document plausible bounds before generation. Each scenario declares an a-priori allowlist of spend-eligible source_origin values; the contract does not assume that every observed origin is paid. Zero spend must be intentional rather than missing. Campaign is not generated in the MVP.

The generator may use dates and source-origin coverage to define its domain, but it must not inspect Closed Deals, activation, Orders, GMV, conversion rates, or any downstream KPI to tune spend. Spend is never adjusted to create attractive CPL, Seller Acquisition Cost, GMV ROAS, or other outputs. Any metric mixing this spend with real Olist outcomes remains labeled as a synthetic scenario.

## OPEN DECISIONS

- Select the reporting timezone for source timestamps that contain no timezone offset.
- Define refund/chargeback treatment if a source containing those events is introduced; the current public files do not expose a complete refund fact.
- Establish a real source snapshot/extraction timestamp for future refreshes instead of relying on the empirical maximum event timestamp.
- Revisit Campaign only if a source-backed, governed campaign identifier becomes available.
- Define a source-backed conversion maturity SLA if future refreshes make cohort completion measurable.
