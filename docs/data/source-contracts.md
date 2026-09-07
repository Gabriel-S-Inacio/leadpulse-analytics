# Source Contracts

## Contract boundary and evidence

These contracts distinguish:

- **SOURCE-DOCUMENTED:** names or meanings described by the canonical source.
- **OBSERVED:** measurements from the locally imported copy identified by data/raw/manifest.json.
- **BUSINESS INTERPRETATION:** proposed LeadPulse meaning; it is not promoted to a source fact.
- **MVP BUSINESS RULE:** a frozen LeadPulse semantic decision; it is not asserted as a source property.

The observed copy contains 11 CSVs and 127,062,183 uncompressed bytes. Profiling used Python stdlib, counted full-row fingerprints, measured candidate keys and relationships, and emitted no complete records or unrestricted PII. Detailed machine-readable evidence remains ignored in data/raw/_profiling/profile.json.

## Marketing Qualified Leads

### SOURCE TABLE

olist_marketing_qualified_leads_dataset.csv — Olist Marketing Funnel.

### PURPOSE

Represent the sampled MQL population and its first known acquisition context.

### SOURCE GRAIN

**OBSERVED:** 8,000 rows, 4 columns, one row per mql_id.

### CANDIDATE KEY

**OBSERVED:** mql_id is unique and non-null: 8,000 distinct values, 0 duplicate key rows, and 0 null-key rows.

### IMPORTANT COLUMNS

**OBSERVED:** mql_id, first_contact_date, landing_page_id, origin.

### DATE FIELDS

**OBSERVED:** first_contact_date ranges from 2017-06-14 through 2018-05-31.

### RELATIONSHIPS

**OBSERVED:** 842 of 8,000 MQL keys match Closed Deals (10.525%); 7,158 do not. All 842 Closed Deal mql_id values match an MQL. Row multiplicity is 1:1 on the matched key.

### NULLABILITY OBSERVED

origin has 60 nulls (0.75%). Other columns have 0 observed nulls.

### CARDINALITY OBSERVED

- mql_id: 8,000.
- landing_page_id: 495.
- origin: 10 non-null values.

Full origin distribution: organic_search 2,296; paid_search 1,586; social 1,350; unknown 1,099; direct_traffic 499; email 493; referral 284; other 150; display 118; other_publicities 65. The last value is below 1% of non-null rows. No casefold collisions or leading/trailing whitespace variants were observed.

### KNOWN QUALITY ISSUES

60 missing origins and 1,099 explicit unknown origins limit source assignment. The table begins at MQL and contains no complete pre-MQL touch history or native advertising campaign identifier.

### LEADPULSE USAGE

Real-world source for MQL counts, cohort date, retained source_origin, minimal Channel normalization, and ClosedDeal conversion denominator. landing_page_id remains context and is not a Campaign.

**MVP BUSINESS RULE:** the explicit origin-to-Channel mapping is frozen in `analytics-semantics.md`; literal `unknown`, null, and unrecognized future values map to `unattributed`. Campaign remains unavailable.

### UNRESOLVED QUESTIONS

Revisit only if future source values require a versioned mapping extension. No Campaign derivation is approved for the MVP.

## Closed Deals

### SOURCE TABLE

olist_closed_deals_dataset.csv — Olist Marketing Funnel.

### PURPOSE

Represent successful B2B closes that link MQLs to sellers.

### SOURCE GRAIN

**OBSERVED:** 842 rows and 14 columns; 0 duplicate full rows.

### CANDIDATE KEY

**OBSERVED:** mql_id, seller_id, and the pair (mql_id, seller_id) are each unique and non-null across all 842 rows. The file therefore exhibits a 1:1 mql_id-to-seller_id relationship in this copy.

### IMPORTANT COLUMNS

**OBSERVED:** mql_id, seller_id, sdr_id, sr_id, won_date, business_segment, lead_type, lead_behaviour_profile, has_company, has_gtin, average_stock, business_type, declared_product_catalog_size, declared_monthly_revenue.

### DATE FIELDS

**OBSERVED:** won_date ranges from 2017-12-05 02:00:00 through 2018-11-14 18:04:19, with 0 null/invalid values.

### RELATIONSHIPS

- All 842 mql_id values match MQLs.
- 380 of 842 seller_id values match the E-Commerce Sellers table (45.130641%); 462 do not.
- The same 380 seller_id values appear in Order Items; 462 have no observed Order Item.
- **BUSINESS INTERPRETATION:** ClosedDeal-to-AcquiredSeller is 1:1 inside the funnel file, while downstream e-commerce coverage is partial and must not be mistaken for failed funnel identity.

### NULLABILITY OBSERVED

- average_stock: 776 (92.161520%).
- business_segment: 1 (0.118765%).
- business_type: 10 (1.187648%).
- declared_product_catalog_size: 773 (91.805226%).
- has_company: 779 (92.517815%).
- has_gtin: 778 (92.399050%).
- lead_behaviour_profile: 177 (21.021378%).
- lead_type: 6 (0.712589%).
- mql_id, seller_id, won_date, sdr_id, sr_id, and declared_monthly_revenue: 0 observed nulls.

### CARDINALITY OBSERVED

- mql_id: 842; seller_id: 842; sdr_id: 32; sr_id: 22.
- business_segment: 33 non-null values.
- lead_type: 8 non-null values.
- lead_behaviour_profile: 9 non-null values.
- business_type: 3 non-null values.

No leading/trailing whitespace or capitalization collisions were observed in the profiled categorical fields.

### KNOWN QUALITY ISSUES

High null rates make stock, company/GTIN, and declared catalog size unsuitable as required fields. Behaviour profile is null for 21.02%. The e-commerce snapshot contains only 380 of the 842 acquired seller IDs.

### LEADPULSE USAGE

Real-world ClosedDeal, MQL-to-AcquiredSeller conversion, seller-acquired date, and source-supported B2B identity.

### UNRESOLVED QUESTIONS

Explain the 462 sellers outside the e-commerce snapshot and decide whether high-null descriptive fields belong in later models.

## Sellers

### SOURCE TABLE

olist_sellers_dataset.csv — Olist Brazilian E-Commerce.

### PURPOSE

Represent marketplace sellers present in the e-commerce snapshot.

### SOURCE GRAIN

**OBSERVED:** 3,095 rows and 4 columns, one row per seller_id.

### CANDIDATE KEY

**OBSERVED:** seller_id is unique and non-null: 3,095 distinct values, with 0 duplicate key rows.

### IMPORTANT COLUMNS

**OBSERVED:** seller_id, seller_zip_code_prefix, seller_city, seller_state.

### DATE FIELDS

None.

### RELATIONSHIPS

**OBSERVED:** all 3,095 Sellers appear in Order Items. Only 380 match Closed Deals; 2,715 Sellers have no match in the Marketing Funnel Closed Deals copy.

### NULLABILITY OBSERVED

No nulls observed.

### CARDINALITY OBSERVED

seller_id has 3,095 values; seller_state has 23 values.

### KNOWN QUALITY ISSUES

No row/key issue observed. Cross-source coverage differs because the public funnel is a sampled, bounded acquisition population.

### LEADPULSE USAGE

Validate downstream presence of acquired sellers and provide seller context. Geographic attributes are not identity.

### UNRESOLVED QUESTIONS

Confirm how snapshot boundaries explain unmatched populations before defining downstream cohort completeness.

## Orders

### SOURCE TABLE

olist_orders_dataset.csv — Olist Brazilian E-Commerce.

### PURPOSE

Represent EndCustomer marketplace Orders and their lifecycle.

### SOURCE GRAIN

**OBSERVED:** 99,441 rows and 8 columns, one row per order_id.

### CANDIDATE KEY

**OBSERVED:** order_id is unique and non-null across 99,441 rows. customer_id is also distinct for every Order in this table.

### IMPORTANT COLUMNS

**OBSERVED:** order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date.

### DATE FIELDS

- order_purchase_timestamp: 2016-09-04 21:15:19 to 2018-10-17 17:30:18.
- order_approved_at: 2016-09-15 12:16:38 to 2018-09-03 17:40:06.
- order_delivered_carrier_date: 2016-10-08 10:34:01 to 2018-09-11 19:48:28.
- order_delivered_customer_date: 2016-10-11 13:46:32 to 2018-10-17 13:22:46.
- order_estimated_delivery_date: 2016-09-30 00:00:00 to 2018-11-12 00:00:00.

### RELATIONSHIPS

- 98,666 distinct OrderItem order_id values all match Orders; 775 Orders have no Order Item.
- 99,441 Orders all match Customers by customer_id with 1:1 row multiplicity.
- 99,440 Orders match Payments; one Order has no Payment. Payments have no unmatched order_id.

### NULLABILITY OBSERVED

order_approved_at has 160 nulls (0.160899%); order_delivered_carrier_date 1,783 (1.793023%); order_delivered_customer_date 2,965 (2.981668%). Other columns have 0 observed nulls.

### CARDINALITY OBSERVED

order_id: 99,441; customer_id: 99,441; order_status: 8.

Complete status distribution: delivered 96,478; shipped 1,107; canceled 625; unavailable 609; invoiced 314; processing 301; created 5; approved 2. No case or surrounding-whitespace variants were observed.

### KNOWN QUALITY ISSUES

Lifecycle date nullability is status-dependent. Orders without Order Items and the one Order without Payment need status-aware investigation.

### LEADPULSE USAGE

Downstream period and Order context.

**MVP BUSINESS RULE:** only `delivered` Orders are eligible. `order_purchase_timestamp` governs event time, and acquired-seller activity must occur strictly after the seller's ClosedDeal won_date.

### UNRESOLVED QUESTIONS

Refund/chargeback treatment remains unresolved because these files do not expose a complete refund event fact.

## Order Items

### SOURCE TABLE

olist_order_items_dataset.csv — Olist Brazilian E-Commerce.

### PURPOSE

Connect Orders to sellers and provide item price/freight observations.

### SOURCE GRAIN

**OBSERVED:** 112,650 rows and 7 columns at Order/item-sequence grain; 0 duplicate full rows.

### CANDIDATE KEY

**OBSERVED:** (order_id, order_item_id) is unique and non-null for all 112,650 rows.

### IMPORTANT COLUMNS

**OBSERVED:** order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value.

### DATE FIELDS

shipping_limit_date ranges from 2016-09-19 00:15:34 through 2020-04-09 22:35:08. The 2020 maximum is beyond the Order purchase range and requires interpretation before use.

### RELATIONSHIPS

98,666 distinct order_id values all match Orders; row multiplicity is N:1 with at most 21 Order Items per order_id. All 3,095 distinct seller_id values match Sellers; seller-to-item multiplicity is 1:N with up to 2,033 item rows for one seller.

### NULLABILITY OBSERVED

No nulls observed in any column.

### CARDINALITY OBSERVED

order_id: 98,666; order_item_id values: 21; product_id: 32,951; seller_id: 3,095.

### KNOWN QUALITY ISSUES

Multi-item and multi-seller Orders make order-level counts non-additive across sellers. shipping_limit_date includes a far-future value relative to purchases.

### LEADPULSE USAGE

Primary seller_id bridge and official MVP source for marketplace item-value/GMV.

**MVP BUSINESS RULE:** GMV sums `price` only for Order Items on delivered Orders, supplied by AcquiredSellers, with Order purchase strictly after won_date. `freight_value` is excluded.

### UNRESOLVED QUESTIONS

Resolve the shipping-limit-date anomaly policy before using that field operationally; it does not govern MVP GMV.

## Customers (EndCustomer source)

### SOURCE TABLE

olist_customers_dataset.csv — Olist Brazilian E-Commerce.

### PURPOSE

Represent final buyers using order-scoped and cross-order identifiers.

### SOURCE GRAIN

**OBSERVED:** 99,441 rows and 5 columns, one row per customer_id.

### CANDIDATE KEY

**OBSERVED:** customer_id is unique/non-null with 99,441 values. customer_unique_id is non-null but not unique: 96,096 distinct values and 3,345 repeated-key rows.

### IMPORTANT COLUMNS

**OBSERVED:** customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state.

### DATE FIELDS

None; activity time comes from Orders.

### RELATIONSHIPS

All 99,441 Orders match one Customer row through customer_id with observed 1:1 row multiplicity.

### NULLABILITY OBSERVED

No nulls observed.

### CARDINALITY OBSERVED

customer_id: 99,441; customer_unique_id: 96,096; customer_state: 27.

### KNOWN QUALITY ISSUES

customer_id is order-scoped and must not be used as persistent EndCustomer identity. customer_unique_id intentionally repeats and is not a row key.

### LEADPULSE USAGE

EndCustomer context only; never seller acquisition or Seller Acquisition Cost.

### UNRESOLVED QUESTIONS

Decide whether EndCustomer analysis is needed in MVP and define privacy-safe use of location.

## Payments

### SOURCE TABLE

olist_order_payments_dataset.csv — Olist Brazilian E-Commerce.

### PURPOSE

Represent payment sequences associated with Orders.

### SOURCE GRAIN

**OBSERVED:** 103,886 rows and 5 columns at Order/payment-sequence grain; 0 duplicate full rows.

### CANDIDATE KEY

**OBSERVED:** (order_id, payment_sequential) is unique and non-null for all 103,886 rows.

### IMPORTANT COLUMNS

**OBSERVED:** order_id, payment_sequential, payment_type, payment_installments, payment_value.

### DATE FIELDS

None.

### RELATIONSHIPS

99,440 distinct payment order_id values all match Orders. One Order has no Payment. Observed Order-to-Payment row multiplicity is 1:N: 2,961 order IDs have multiple payment rows and the maximum is 29.

### NULLABILITY OBSERVED

No nulls observed.

### CARDINALITY OBSERVED

order_id: 99,440; payment_sequential values: 29; payment_type values: 5.

### KNOWN QUALITY ISSUES

Multiple payments per Order make naive joins to Order Items multiplicative. Nine payment_value rows are zero.

### LEADPULSE USAGE

Relationship validation and settlement-oriented profiling. Payments are not the official GMV source.

**MVP BUSINESS RULE:** `payment_value` must not be joined and summed at Order Item/seller grain or substituted for GMV.

### UNRESOLVED QUESTIONS

Explain the Order without Payment and decide whether payment values support a separate metric.

## Monetary observations

All figures below cover all raw rows with no Order status, cancellation, or refund filter.

### Order Item price

- Count 112,650; null 0; invalid 0; zero 0; negative 0.
- Minimum 0.85; maximum 6,735.00; sum 13,591,643.70.

### Order Item freight_value

- Count 112,650; null 0; invalid 0; zero 383; negative 0.
- Minimum 0.00; maximum 409.68; sum 2,251,909.54.

### Payment payment_value

- Count 103,886; null 0; invalid 0; zero 9; negative 0.
- Minimum 0.00; maximum 13,664.08; sum 16,008,872.12.

### Candidate comparison

- SUM(price): 13,591,643.70.
- SUM(price + freight_value): 15,843,553.24.
- SUM(payment_value): 16,008,872.12.
- Payment minus price: 2,417,228.42.
- Payment minus price plus freight: 165,318.88.

**BUSINESS INTERPRETATION:** payments can differ because an Order can have multiple payment methods/sequences and payment value may include components not represented by item price plus freight. Cancellations, status scope, vouchers, financing/rounding, and adjustments can contribute to differences.

**MVP BUSINESS RULE:** official GMV is `SUM(order_items.price)` over delivered, post-win acquired-seller Order Items. Freight and payment_value are excluded. GMV is a marketplace item-value proxy, never Olist corporate revenue.

## Seller activation observations and MVP rule

Using only presence in Order Items, with no Order-status filter and no finalized activation contract:

- ClosedDeal sellers: 842.
- Sellers appearing in Order Items: 380.
- Sellers absent from Order Items: 462.
- Observed presence rate: 45.130641%.
- All 380 matched sellers have usable won and first-purchase timestamps.
- Days from won_date to first observed Order: minimum 3.209745, median 44.293131, maximum 220.806319.
- Negative durations: 0.

The stricter semantic candidate was measured using delivered Orders and requiring order_purchase_timestamp strictly later than won_date:

- Acquired sellers: 842.
- Sellers with a post-win delivered Order: 376.
- Sellers without a post-win delivered Order: 466.
- Pre-win/equal qualifying item rows rejected: 0.
- First eligible Order lag: minimum 3.209745; P25 22.617188; median 44.293131; P75 71.913027; P90 101.939334; P95 117.442888; maximum 188.870972 days.
- Within 30 days: 128 of 376 observed activations (34.042553%).
- Within 60 days: 246 (65.425532%).
- Within 90 days: 322 (85.638298%).
- Within 180 days: 374 (99.468085%).

**MVP BUSINESS RULE:** an Activated Seller has at least one Order Item on a delivered Order purchased in `(won_date, won_date + 90 days]`. At the empirical source cutoff `2018-10-17 17:30:18`, only the 746 sellers with a complete 90-day window enter the denominator; 314 activated, producing 42.091153%. The 96 incomplete sellers are excluded rather than classified as non-activated. Because 462 ClosedDeal sellers are absent from the e-commerce seller snapshot, non-activation means no qualifying event observed in the linked snapshots, not proven real-world inactivity.

## Observed relationship matrix

1. MQL mql_id to Closed Deals mql_id: left 8,000; right 842; matched 842; unmatched left 7,158; unmatched right 0; left match 10.525%; multiplicity 1:1.
2. Closed Deals seller_id to Sellers seller_id: left 842; right 3,095; matched 380; unmatched left 462; unmatched right 2,715; left match 45.130641%; multiplicity 1:1.
3. Closed Deals seller_id to Order Items seller_id: left 842; right 3,095; matched 380; unmatched left 462; unmatched right 2,715; left match 45.130641%; multiplicity 1:N.
4. Sellers seller_id to Order Items seller_id: left 3,095; right 3,095; matched 3,095; unmatched left/right 0; left match 100%; multiplicity 1:N.
5. Order Items order_id to Orders order_id: left 98,666; right 99,441; matched 98,666; unmatched left 0; unmatched right 775; left match 100%; multiplicity N:1.
6. Orders customer_id to Customers customer_id: left/right 99,441; matched 99,441; unmatched left/right 0; left match 100%; multiplicity 1:1.
7. Orders order_id to Payments order_id: left 99,441; right 99,440; matched 99,440; unmatched left 1; unmatched right 0; left match 99.998994%; multiplicity 1:N.

## OPEN DECISIONS

- Explain cross-source snapshot coverage for the 462 ClosedDeal sellers absent from e-commerce.
- Define refund/chargeback treatment if a future source exposes those events.
- Set reporting timezone and handling of the 2020 shipping-limit outlier.
- Establish a source-backed extraction timestamp for future cohort maturity calculations; the current cutoff is an empirical maximum event timestamp.
- Confirm the e-commerce dataset license and capture source-version metadata in future acquisitions.
