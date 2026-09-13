# MVP Analytics Data Contracts

## Purpose

These contracts turn the approved logical model and frozen business semantics into testable expectations. They describe analytical outputs, not executable SQL or a physical database design.

Every published dataset must identify compatible source snapshots, rule/mapping versions, and observation cutoffs where applicable. A failed required-key, uniqueness, or conditional-consistency rule is a load failure or quarantine condition; it is not silently repaired with zero or an UNKNOWN seller.

## Shared contract rules

### Evidence and NULL states

- `UNKNOWN` means a required descriptive value is missing, invalid, or unrecognized.
- `NOT_APPLICABLE` means the relationship or concept does not apply.
- `NOT_OBSERVED` remains NULL for scalar event values that may exist but are absent from the available evidence; a required date foreign key uses the distinct `NOT_OBSERVED` technical member.
- zero is an observed numerical value or an explicitly derived zero contribution.
- fact foreign keys are non-null and use governed technical members when semantically appropriate.
- missing fact rows, especially synthetic spend rows, are not implicit zeros.

### Cross-table version compatibility

- Facts combined in one KPI must use compatible source snapshots and the declared origin mapping version.
- Lifecycle queries must select exactly one observation cutoff, lifecycle rule version, and source snapshot set.
- Synthetic-spend queries must select exactly one scenario, methodology version, generation seed, and currency.
- Cross-fact ratios aggregate their components independently to conformed dimensional grain before joining; raw fact-to-fact joins are forbidden.

## Table contracts

### dim_date

**UNIQUENESS**

- `date_key` is unique.
- `calendar_date` is unique among `date_classification = 'CALENDAR'`.
- exactly one technical member exists for each of `UNKNOWN`, `NOT_OBSERVED`, and `NOT_APPLICABLE`.

**NOT NULL**

- `date_key` and `date_classification` are always present.
- all calendar attributes are present for `CALENDAR` rows.
- calendar attributes are NULL for technical rows.

**ACCEPTED VALUES**

- `date_classification IN ('CALENDAR', 'UNKNOWN', 'NOT_OBSERVED', 'NOT_APPLICABLE')`.
- quarter is 1-4, month is 1-12, day_of_month is valid for the date, and ISO day_of_week is 1-7.

**REFERENTIAL INTEGRITY**

- none outbound; every date key referenced by an approved fact exists here.

**CONDITIONAL CONSISTENCY**

- derived parts must exactly match `calendar_date`.
- `is_weekend = TRUE` iff ISO day_of_week is 6 or 7.
- `year_month` uses fixed `YYYY-MM` format.
- no fiscal or locale-dependent runtime attributes are introduced.

### dim_origin

**UNIQUENESS**

- `origin_key` is unique.
- `origin_member_code` is unique in the currently published Type 1 mapping.

**NOT NULL**

- `origin_key`, `origin_member_code`, `normalized_channel`, `classification`, and `mapping_version` are always present.
- `source_origin` may be NULL only for `MISSING` or `NOT_APPLICABLE` technical members; an unrecognized non-null raw value is still preserved.

**ACCEPTED VALUES**

- `classification IN ('OBSERVED', 'EXPLICIT_UNKNOWN', 'MISSING', 'UNRECOGNIZED', 'NOT_APPLICABLE')`.
- normalized technical values are `unattributed` for explicit unknown/missing/unrecognized and `not_applicable` for N/A.

**REFERENTIAL INTEGRITY**

- none outbound; all approved fact `origin_key` values resolve here.

**CONDITIONAL CONSISTENCY**

- raw `direct_traffic` maps to normalized `direct`.
- literal raw `unknown`, NULL, and unrecognized values map to `unattributed` with their distinct classifications.
- every other recognized observed value remains semantically equivalent to `source_origin`.
- no column or mapping encodes Campaign.
- one mapping version produces one deterministic result for a given raw state.

### dim_seller

**UNIQUENESS**

- `seller_key` is unique.
- `seller_id` is unique.

**NOT NULL**

- `seller_key`, `seller_id`, and `seller_source_presence` are always present.
- geography may be NULL when not observed in the e-commerce seller source.

**ACCEPTED VALUES**

- `seller_source_presence IN ('funnel_only', 'ecommerce_only', 'both')`.
- present seller state codes follow the observed two-character source domain.

**REFERENTIAL INTEGRITY**

- none outbound; ClosedDeal and Order Item seller identifiers in accepted rows resolve here.

**CONDITIONAL CONSISTENCY**

- `funnel_only` requires presence in Closed Deals and absence from Sellers.
- `ecommerce_only` requires absence from Closed Deals and presence in Sellers.
- `both` requires presence in both governed source snapshots.
- funnel-only sellers may have NULL geography; this is `NOT_OBSERVED`, not an invented value.
- no acquisition event, origin, activation, or measure column is allowed on this dimension.

### fct_mql

**UNIQUENESS**

- `mql_id` is unique per published compatible source snapshot.

**NOT NULL**

- all contracted columns are required, including technical-key resolution for missing origin.

**ACCEPTED VALUES**

- `mql_count = 1`.
- the referenced date is a valid calendar member unless source-date validation explicitly quarantines the row.

**REFERENTIAL INTEGRITY**

- `contact_date_key` resolves to `dim_date`.
- `origin_key` resolves to `dim_origin` under the declared mapping version.

**CONDITIONAL CONSISTENCY**

- MQL raw origin and resolved origin classification/mapping agree.
- NULL raw origin resolves to the governed missing/unattributed member.
- `landing_page_id` is lineage context only and is never treated as Campaign.
- source filename contains no personal path.

### fct_closed_deal

**UNIQUENESS**

- `mql_id` is unique.
- `seller_id` is unique under the observed MVP contract; any drift fails the `acquired_seller_count = 1` assumption and requires semantic review.

**NOT NULL**

- all contracted columns are required for accepted rows, including `temporal_quality_status`.

**ACCEPTED VALUES**

- `closed_deal_count = 1` and `acquired_seller_count = 1`.
- `temporal_quality_status IN ('VALID', 'INVALID_SEQUENCE')`.

**REFERENTIAL INTEGRITY**

- `mql_id` resolves to exactly one compatible `fct_mql` row.
- `seller_key` resolves to a non-UNKNOWN `dim_seller` member whose natural key equals `seller_id`.
- origin, contact date, and won date keys resolve to their dimensions.

**CONDITIONAL CONSISTENCY**

- `origin_key` and `contact_date_key` exactly match the linked MQL.
- `won_date_key` matches the date portion of `won_timestamp`.
- `temporal_quality_status = 'VALID'` when `won_timestamp` is on or after the linked first-contact calendar date; otherwise it is `INVALID_SEQUENCE`.
- the governed MVP exception is preserved as `INVALID_SEQUENCE` without source correction, exclusion, or quarantine; it still contributes exactly 1 to both acquisition occurrence measures.
- new, removed, or changed temporal exceptions fail the governed exception contract rather than passing silently.
- a ClosedDeal is an acquisition event and is never treated as a marketplace Order.

### fct_seller_lifecycle

**UNIQUENESS**

- `(seller_key, observation_cutoff_timestamp, lifecycle_rule_version, source_snapshot_id)` is unique.
- one seller cannot have multiple acquisition records within a single compatible lifecycle version under the current 1:1 source contract.

**NOT NULL**

- seller, origin, won date/timestamp, cutoff date/timestamp, rule version, source snapshot, temporal quality, maturity flag, and count indicators are required.
- `is_activated_90d` is intentionally nullable for an immature seller or invalid temporal sequence, even if an early event is already observed for an immature cohort.
- activation event fields and duration are nullable only under the documented state rules.

**ACCEPTED VALUES**

- `mature_seller_count` and `activated_seller_count` are each 0 or 1.
- present `time_to_first_order_days` is greater than 0; it may exceed 90 because the first eligible post-win event is retained separately from 90-day activation classification.
- current `lifecycle_rule_version = 'seller_activation_v1'`, covering delivered eligibility, strict post-win ordering, the 90-day activation window, and required valid temporal quality.

**REFERENTIAL INTEGRITY**

- seller, origin, won-date, activation-date, and cutoff-date keys resolve to conformed dimensions.
- seller/origin/won values match the canonical `fct_closed_deal` acquisition.
- `first_eligible_order_id`, when present, resolves to at least one matching `fct_order_item` row under the same compatible source snapshot.

**CONDITIONAL CONSISTENCY**

- `is_mature_90d = (temporal_quality_status = 'VALID' AND observation_cutoff_timestamp >= won_timestamp + 90 days)`.
- mature seller count is 1 iff `is_mature_90d` is TRUE.
- `is_activated_90d = TRUE` requires activation timestamp/date, first eligible Order ID, and duration; `activation_timestamp` is the timestamp of that Order event.
- `is_activated_90d = FALSE` requires a valid mature cohort and no first eligible Order within 90 days; a later first event may remain populated.
- immature or invalid-temporal rows use NULL activation status, not FALSE.
- activated seller count is 1 iff the row is both mature and activated; otherwise it is 0.
- activation timestamp is the first eligible delivered Order strictly after won timestamp and no later than cutoff; it may occur after 90 days.
- first eligible Order uses deterministic purchase-timestamp then order-id tie-breaking and must be delivered.
- `INVALID_SEQUENCE` rows remain in the snapshot with maturity FALSE, activation status/duration/event fields NULL, and the `UNKNOWN` activation date member.
- downstream aggregations must select exactly one `observation_cutoff_timestamp + lifecycle_rule_version + source_snapshot_id` version before summing lifecycle measures.
- the same seller may occur across versions, but aggregations must select one version.

### fct_order_item

**UNIQUENESS**

- `(order_id, order_item_id)` is unique per published compatible source snapshot.

**NOT NULL**

- source identity, seller/date/origin keys, purchase timestamp, status, monetary values, primary flags, eligible GMV, and provenance are required.
- won timestamp and acquisition-relative flags are nullable only when acquisition is not applicable.

**ACCEPTED VALUES**

- `order_item_id > 0`.
- `item_price >= 0`, `freight_value >= 0`, and `eligible_gmv_amount >= 0`.
- `order_item_count = 1`.
- `order_status IN ('created', 'approved', 'invoiced', 'processing', 'shipped', 'delivered', 'unavailable', 'canceled')` for the profiled source contract.

**REFERENTIAL INTEGRITY**

- every `order_id` resolves to exactly one compatible Orders header during construction.
- `seller_key`, origin, purchase date, and seller won date keys resolve to dimensions.
- an acquired seller resolves to exactly one canonical ClosedDeal; non-acquired items use the origin and won-date N/A members.

**CONDITIONAL CONSISTENCY**

- purchase date key equals the date portion of Order purchase timestamp.
- all items with the same `order_id` have the same propagated status and purchase timestamp.
- `is_eligible_order = TRUE` iff status is `delivered`.
- acquired seller requires acquisition origin, calendar won date, won timestamp, and non-null temporal flags.
- non-acquired seller requires origin/won date N/A members, NULL won timestamp, and NULL acquisition-relative flags.
- `is_post_acquisition = TRUE` iff purchase timestamp is strictly after won timestamp.
- `is_within_90d_of_acquisition = TRUE` iff purchase lies in `(won_timestamp, won_timestamp + 90 days]`; TRUE implies post-acquisition.
- `eligible_gmv_amount = item_price` iff seller is acquired, Order is delivered, and purchase is post-acquisition; otherwise it is exactly 0.
- freight never contributes to eligible GMV; `payment_value` and an Order-level total are absent.
- Order counts use distinct `order_id` overall or distinct `(seller_key, order_id)` by seller/origin; item rows are never summed as Orders.

### fct_marketing_spend

**UNIQUENESS**

- `(spend_date_key, origin_key, scenario_id)` is unique.

**NOT NULL**

- every contracted field is required.

**ACCEPTED VALUES**

- `spend_amount >= 0`.
- MVP `currency = 'BRL'`.
- `data_classification = 'SYNTHETIC'` exactly.
- scenario and methodology identifiers are nonblank.

**REFERENTIAL INTEGRITY**

- spend date resolves to a `CALENDAR` member.
- origin resolves to a governed spend-eligible `dim_origin` member and cannot be `NOT_APPLICABLE`.

**CONDITIONAL CONSISTENCY**

- one scenario has one methodology version, seed, currency, and origin mapping version.
- repeated generation with the same declared inputs produces identical keys and amounts.
- generated origin coverage follows an a-priori allowlist; it does not invent Campaign.
- generation does not read Closed Deals, lifecycle, Orders, GMV, conversion, or other downstream outcomes.
- absent rows are not zero; a zero amount must be explicitly generated by the methodology.
- alternative scenarios/currencies are never summed together.

The implemented contract is `baseline_v1` with methodology `paid_media_daily_v1`, seed `20260913`, currency `BRL`, and exact `SYNTHETIC` classification. Its allowlist is `paid_search`, `display`, `social`, and `other_publicities`; each origin spans its own observed MQL first-contact minimum through maximum. Daily amounts use declared per-origin baselines, fixed month/weekday effects, and bounded hash-derived variation. The ignored generated CSV checksum is retained through raw metadata and `source_snapshot_id`.

## Dashboard-ready semantic marts

All four marts are rebuilt as tables for the local MVP. Their ratios are convenience outputs, not additive measures; overall ratios must always be recalculated from the exposed numerators and denominators.

### mart_acquisition_performance

- grain is `(cohort_month, origin_key)`, where the cohort is always MQL `first_contact_date` month;
- MQLs, Closed Deals, and Acquired Sellers reconcile to their facts without row loss or fanout;
- the Closed Deal numerator inherits the MQL contact cohort rather than switching to `won_date`;
- conversion is `acquired_sellers / mqls`, with a zero denominator producing NULL.

### mart_seller_activation

- grain is `(cohort_month, origin_key, observation_cutoff_timestamp, lifecycle_rule_version, source_snapshot_id)`;
- the implemented mart selects the most recent deterministic `seller_activation_v1` tuple and exposes the full tuple on every row;
- mature and activated counts reconcile to that exact lifecycle version;
- time-to-first-Order averages and medians include only mature `is_activated_90d = TRUE` sellers and must not be summed across groups;
- 90-day GMV and seller/Order participations are independently aggregated before division by Activated Sellers.

### mart_marketing_efficiency

- grain is `(period, origin_key, scenario_id, methodology_version, generation_seed, currency, lifecycle version tuple)`;
- spend, MQL, acquisition, and 90-day GMV components are aggregated independently before joining;
- coverage boundaries preserve the source-origin generation window in partial first/last months;
- `data_classification = 'SYNTHETIC'`; CPL, Seller Acquisition Cost, and GMV ROAS inherit that classification and remain non-causal;
- every query must select one scenario/methodology/seed/currency and one lifecycle tuple.

### mart_downstream_performance

- grain is `(purchase_month, origin_key, seller_key, order_id)` rather than a lossy month/origin aggregate;
- `eligible_gmv` is additive and reconciles to item-grain eligible GMV;
- seller/Order participation is additive at this grain;
- Orders are non-additive across sellers/origins, so global and cross-origin counts use `COUNT(DISTINCT order_id)`;
- retaining the natural Order identifier prevents the known multi-seller Orders from being silently double-counted.

### Mart quality and fanout rules

- each complete mart grain is unique and all governed keys resolve;
- rates remain between 0 and 1 where applicable, monetary values remain non-negative, and all denominators are exposed;
- acquisition MQL and seller totals recompose exactly to their source facts;
- activation measures recompose only after selecting one complete lifecycle version;
- marketing spend recomposes per scenario tuple and is never joined directly to seller- or item-grain facts;
- downstream GMV recomposes to `fct_order_item`, while global Orders use distinct `order_id`;
- no dashboard query may sum precomputed rates, mix spend scenarios, or mix lifecycle snapshots.

## KPI feasibility

`SUPPORTED` means the logical schema and implemented analytics layer provide a defensible computation path. It does not imply that a dashboard or production orchestration is implemented.

| KPI | Status | Source tables | Caveats |
| --- | --- | --- | --- |
| MQLs | SUPPORTED | `fct_mql`, `dim_date`, `dim_origin` | Sum `mql_count`; source starts at MQL, not Visitor. |
| Closed Deals | SUPPORTED | `fct_closed_deal`, `dim_date`, `dim_origin` | Sum close indicator; source contains successful closes only. |
| Acquired Sellers | SUPPORTED | `fct_closed_deal`, `dim_seller`, `dim_origin` | Distinct seller is canonical; additive indicator requires refreshed uniqueness validation. |
| MQL -> AcquiredSeller Conversion | SUPPORTED | separately aggregated `fct_mql` and `fct_closed_deal` | Same first-contact cohort/origin/cutoff; incomplete cohorts remain labeled rather than presumed final. |
| Activated Sellers | SUPPORTED | `fct_seller_lifecycle`, `dim_origin`, `dim_seller` | Sum activated count only for mature rows at exactly one lifecycle version. |
| Seller Activation Rate | SUPPORTED | `fct_seller_lifecycle` | `SUM(activated_seller_count) / SUM(mature_seller_count)`; zero denominator returns NULL. |
| Orders from Acquired Sellers | SUPPORTED | `fct_order_item`, `dim_seller`, `dim_origin` | Delivered, post-win only; distinct Order overall or seller/Order participation by seller/origin. |
| GMV from Acquired Sellers | SUPPORTED | `fct_order_item`, `dim_seller`, `dim_origin` | Sum `eligible_gmv_amount`; excludes freight, Payments, refunds not observed, and corporate-revenue claims. |
| GMV per Activated Seller | SUPPORTED | `fct_order_item` plus one-version `fct_seller_lifecycle` | Numerator filters mature cohort items to `(0, 90]`; aggregate facts separately before division. |
| Orders per Activated Seller | SUPPORTED | `fct_order_item` plus one-version `fct_seller_lifecycle` | Numerator is distinct seller/Order participation in `(0, 90]`; same mature cohort denominator. |
| Time to First Order | SUPPORTED | `fct_seller_lifecycle`, `dim_origin` | Distribution for activated sellers in mature cohorts; never sum or impute non-activators. |
| Synthetic Spend | SUPPORTED | `fct_marketing_spend`, `dim_date`, `dim_origin` | Select one scenario/methodology/currency; values are synthetic, deterministic, and non-causal. |
| CPL | SUPPORTED | separately aggregated `fct_marketing_spend` and `fct_mql` | Explicit synthetic scenario only; compatible date/origin aggregation and zero denominator yields NULL. |
| Seller Acquisition Cost | SUPPORTED | separately aggregated `fct_marketing_spend` and `fct_closed_deal` | B2B seller acquisition, never EndCustomer CAC or fully loaded cost; scenario-labeled. |
| GMV ROAS | SUPPORTED | separately aggregated `fct_marketing_spend`, `fct_closed_deal`, and `fct_order_item` | Valid mature acquisition cohort and GMV in `(0, 90]`; synthetic/non-causal, not corporate revenue or accounting return. |

## Known contract risks

- The source extraction cutoff is inferred rather than supplied, so lifecycle snapshots must expose their evidence cutoff and source identity.
- Funnel-only sellers make observed non-activation sensitive to cross-dataset coverage.
- The observed ClosedDeal `mql_id`/`seller_id` 1:1 relationship must be retested on every source refresh.
- Source timestamps lack a decided timezone; the logical contract preserves source-naive timestamps and forbids invented offsets.
- Refund and chargeback outcomes are incomplete, so delivered item GMV remains a marketplace sales-value proxy.
- Distinct Order participation is non-additive across sellers/origins; a future governed aggregate may optimize it, but does not change this contract.

## Implementation boundary

These logical and executable dbt contracts do not define orchestration, incremental retention, late-arriving-data handling, dashboard presentation, or production indexing/partitioning. The current physical choices are recorded in `docs/architecture/physical-data-platform.md`.
