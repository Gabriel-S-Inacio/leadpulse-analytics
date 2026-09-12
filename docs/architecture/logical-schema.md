# MVP Logical Analytical Schema

## Purpose and boundary

This document defines storage-independent logical contracts for the approved MVP dimensional tables. It does not define executable SQL, database schemas, PostgreSQL types, migrations, indexes, partitions, dbt materializations, or loading strategies.

The approved surface is limited to `dim_date`, `dim_origin`, `dim_seller`, `fct_mql`, `fct_closed_deal`, `fct_seller_lifecycle`, `fct_order_item`, and future `fct_marketing_spend`. Campaign, EndCustomer, Product, and a separate Order fact are outside this contract.

## Logical type vocabulary

- `ANALYTICAL_KEY`: storage-independent analytical reference. Its physical representation is deferred.
- `STRING`, `INTEGER`, `DECIMAL`, `DATE`, `TIMESTAMP`, and `BOOLEAN`: logical types, not database-specific declarations.
- DECIMAL monetary fields preserve source precision. Currency and scale are physical-contract decisions.

## Key semantics

- **Natural key:** identity supplied by, or reproducibly expressed from, the source business data.
- **Logical primary key:** column set that must uniquely identify a row in the analytical table.
- **Analytical/surrogate key:** warehouse-managed reference used to conform dimensions across facts. Its physical data type and generation mechanism are deferred.

`dim_origin` and `dim_seller` will probably use warehouse-generated surrogate keys. `dim_date.date_key` is a deterministic analytical key. Facts retain their natural or derivation identity as the logical primary key; no standalone fact surrogate key is required by the MVP.

## Global NULL policy

- **UNKNOWN:** a value should exist but is missing, invalid, or unrecognized. Dimension references resolve to a governed `UNKNOWN` member rather than a nullable foreign key.
- **NOT APPLICABLE:** the concept does not apply to the row. It uses a distinct technical dimension member where a foreign key is present.
- **NOT OBSERVED:** an event or attribute could exist but is absent from the available source snapshot/cutoff. Nullable event fields retain NULL; they are not converted to zero.
- **ZERO:** a measured and semantically valid numeric zero. It never substitutes for unknown, not applicable, or not observed.

Technical members in conformed dimensions have stable non-null analytical keys and explicit classifications. Facts must not silently map `NOT APPLICABLE` to `UNKNOWN` or `unattributed`.

Source-event facts expose one governed compatible source snapshot per published relation. Their `source_snapshot_id` is lineage metadata, not an extra row-grain component; retaining multiple source snapshots in one physical relation would require a later versioned-storage decision.

## Dimensions

### dim_date

**TABLE PURPOSE:** conformed calendar used through role-playing keys for contact, close, purchase, activation, observation cutoff, and spend dates.

**GRAIN:** one row per calendar date, plus a small governed set of technical members.

**LOGICAL PRIMARY KEY:** `date_key`.

**SOURCE/NATURAL KEY:** `calendar_date` for `CALENDAR` rows; `date_classification` for technical `UNKNOWN`, `NOT_OBSERVED`, and `NOT_APPLICABLE` rows.

**FOREIGN KEYS:** none.

| Logical name | Semantic definition | Logical type | Nullable | Source | Derivation rule | Business constraints |
| --- | --- | --- | --- | --- | --- | --- |
| date_key | Stable analytical date member identifier. | ANALYTICAL_KEY | NO | Generated | Deterministic from calendar date or reserved technical-member code. | Unique; immutable; physical type deferred. |
| calendar_date | Gregorian calendar date represented by the row. | DATE | YES | Generated | Calendar sequence covering governed source/future dates. | Required and unique when classification is `CALENDAR`; NULL for technical members. |
| date_classification | Kind of date member. | STRING | NO | Generated | Assigned during calendar generation. | One of `CALENDAR`, `UNKNOWN`, `NOT_OBSERVED`, `NOT_APPLICABLE`. |
| year | Calendar year. | INTEGER | YES | Generated | Extracted from `calendar_date`. | Required for `CALENDAR`; NULL for technical members. |
| quarter | Calendar quarter number. | INTEGER | YES | Generated | Derived from month. | 1 through 4 for `CALENDAR`. |
| month | Calendar month number. | INTEGER | YES | Generated | Extracted from `calendar_date`. | 1 through 12 for `CALENDAR`. |
| month_name | Governed English calendar month label. | STRING | YES | Generated | Deterministic lookup from month. | Required for `CALENDAR`; locale must not vary by runtime. |
| year_month | Sortable calendar month label. | STRING | YES | Generated | `YYYY-MM` from `calendar_date`. | Required for `CALENDAR`; fixed format. |
| day_of_month | Day number within month. | INTEGER | YES | Generated | Extracted from `calendar_date`. | 1 through 31 for `CALENDAR`. |
| day_of_week | ISO weekday number. | INTEGER | YES | Generated | Monday = 1 through Sunday = 7. | 1 through 7 for `CALENDAR`. |
| day_name | Governed English weekday label. | STRING | YES | Generated | Deterministic lookup from ISO weekday. | Required for `CALENDAR`; locale must not vary by runtime. |
| is_weekend | Whether the date is Saturday or Sunday. | BOOLEAN | YES | Generated | `day_of_week IN (6, 7)`. | Required for `CALENDAR`; NULL for technical members. |

No fiscal calendar, holiday hierarchy, or duplicated physical date dimensions are part of the MVP.

### dim_origin

**TABLE PURPOSE:** conform the exact observed acquisition origin, minimal Channel normalization, and technical origin states across real outcome facts and synthetic spend.

**GRAIN:** one row per governed origin member in the currently published mapping.

**LOGICAL PRIMARY KEY:** `origin_key`.

**SOURCE/NATURAL KEY:** `origin_member_code`. It remains stable even when the raw value is NULL. The Type 1 MVP strategy restates the published member when its mapping changes; `mapping_version` records which rules produced the current state rather than adding history to the grain.

**FOREIGN KEYS:** none.

| Logical name | Semantic definition | Logical type | Nullable | Source | Derivation rule | Business constraints |
| --- | --- | --- | --- | --- | --- | --- |
| origin_key | Analytical origin member identifier. | ANALYTICAL_KEY | NO | Generated | Assigned to each governed origin member. | Unique; immutable across Type 1 mapping restatements. |
| origin_member_code | Stable machine-readable identity for the member. | STRING | NO | Generated | Exact raw value encoded for observed members; reserved codes for technical members. | Unique; never blank. |
| source_origin | Exact acquisition-origin value as observed. | STRING | YES | Marketing Qualified Leads or synthetic contract | Preserved without case/spacing normalization, including an unrecognized non-null value. | NULL only for `MISSING` or `NOT_APPLICABLE` technical members. |
| normalized_channel | Minimal governed Channel label. | STRING | NO | Derived | `direct_traffic` becomes `direct`; unknown, NULL, or unrecognized becomes `unattributed`; other observed values remain semantically equivalent to raw origin; N/A becomes `not_applicable`. | Must follow the mapping version; no Campaign semantics. |
| classification | Reason and evidential class of the member. | STRING | NO | Derived | Based on raw observability and applicability. | One of `OBSERVED`, `EXPLICIT_UNKNOWN`, `MISSING`, `UNRECOGNIZED`, `NOT_APPLICABLE`. |
| mapping_version | Version of the normalization rules. | STRING | NO | Governed metadata | Assigned when mapping is published. | Nonblank; mappings are reproducible by version. |

A NULL source origin maps to the `MISSING`/`unattributed` member. Literal `unknown` maps to `EXPLICIT_UNKNOWN`/`unattributed`. An e-commerce event with no acquisition applicability uses `NOT_APPLICABLE`, not `unattributed`.

### dim_seller

**TABLE PURPOSE:** conform seller identity across successful B2B acquisition, lifecycle, and marketplace Order Items.

**GRAIN:** one row per distinct `seller_id` observed in the governed source snapshot union.

**LOGICAL PRIMARY KEY:** `seller_key`.

**SOURCE/NATURAL KEY:** `seller_id`.

**FOREIGN KEYS:** none.

| Logical name | Semantic definition | Logical type | Nullable | Source | Derivation rule | Business constraints |
| --- | --- | --- | --- | --- | --- | --- |
| seller_key | Analytical seller identifier. | ANALYTICAL_KEY | NO | Generated | Assigned after conforming the seller-id union. | Unique; immutable for a natural `seller_id`. |
| seller_id | Anonymized Olist seller identifier. | STRING | NO | Closed Deals and/or Sellers | Preserved exactly from source. | Unique; nonblank. |
| seller_zip_code_prefix | Seller location prefix when supplied by e-commerce source. | STRING | YES | Sellers | Preserved as an identifier, not a numeric measure. | NULL when not observed; must not be imputed. |
| seller_city | Seller city when supplied. | STRING | YES | Sellers | Preserved source value; normalization deferred. | NULL when not observed. |
| seller_state | Seller state code when supplied. | STRING | YES | Sellers | Preserved source value. | When present, must be a valid observed two-character state code. |
| seller_source_presence | Sources in which the seller identifier is present. | STRING | NO | Closed Deals and Sellers | Set-membership classification over the governed snapshots. | One of `funnel_only`, `ecommerce_only`, `both`. |

`seller_source_presence` belongs in the MVP because it makes the known cross-source coverage gap explicit. `won_date`, origin, activation fields, GMV, and acquisition descriptors are excluded because they are events, attribution context, or measures.

## Facts

### fct_mql

**TABLE PURPOSE:** represent first observed MQL acquisition entries and their acquisition cohort/origin.

**GRAIN:** one row per `mql_id`.

**LOGICAL PRIMARY KEY:** `mql_id`.

**SOURCE/NATURAL KEY:** `mql_id` from Marketing Qualified Leads.

**FOREIGN KEYS:** `contact_date_key -> dim_date.date_key`; `origin_key -> dim_origin.origin_key`.

| Logical name | Semantic definition | Logical type | Nullable | Source | Derivation rule | Business constraints |
| --- | --- | --- | --- | --- | --- | --- |
| mql_id | Anonymized MQL identifier and degenerate source key. | STRING | NO | Marketing Qualified Leads | Preserved. | Unique; nonblank. |
| contact_date_key | Role-playing date of first known contact. | ANALYTICAL_KEY | NO | `first_contact_date` | Resolve to `dim_date`; UNKNOWN only if source value fails validation. | Referential integrity required. |
| origin_key | First Known Acquisition Source member. | ANALYTICAL_KEY | NO | `origin` | Resolve exact raw value through versioned `dim_origin`; missing values use UNKNOWN/unattributed member. | Referential integrity required. |
| landing_page_id | Source landing-page identifier. | STRING | NO | `landing_page_id` | Preserved without treating it as Campaign. | Nonblank under observed source contract. |
| mql_count | Additive MQL row indicator. | INTEGER | NO | Derived | Constant `1`. | Exactly 1. |
| source_snapshot_id | Governed identifier of the imported source copy. | STRING | NO | Acquisition metadata | Assigned to the profiling/load snapshot. | Nonblank and reproducible. |
| source_file_name | Non-personal source filename for row lineage. | STRING | NO | Acquisition metadata | Constant for the source table. | Must not contain a personal filesystem path. |

No timestamp is invented: the public MQL source supplies `first_contact_date`, not time-of-day.

### fct_closed_deal

**TABLE PURPOSE:** represent successful B2B seller-acquisition closes and their inherited acquisition context.

**GRAIN:** one row per valid ClosedDeal/source `mql_id`.

**LOGICAL PRIMARY KEY:** `mql_id`.

**SOURCE/NATURAL KEY:** `mql_id`; `seller_id` is an observed alternate unique key that must be revalidated per snapshot.

**FOREIGN KEYS:** `seller_key -> dim_seller.seller_key`; `origin_key -> dim_origin.origin_key`; `contact_date_key -> dim_date.date_key`; `won_date_key -> dim_date.date_key`.

| Logical name | Semantic definition | Logical type | Nullable | Source | Derivation rule | Business constraints |
| --- | --- | --- | --- | --- | --- | --- |
| mql_id | Converted MQL identifier and ClosedDeal source key. | STRING | NO | Closed Deals | Preserved. | Unique; must match exactly one `fct_mql` row in the same compatible source snapshot. |
| seller_id | Acquired seller natural identifier retained for lineage. | STRING | NO | Closed Deals | Preserved. | Unique under the observed contract; must resolve to `seller_key`. |
| seller_key | Conformed acquired-seller reference. | ANALYTICAL_KEY | NO | Closed Deals | Resolve `seller_id` through `dim_seller`. | Referential integrity required; UNKNOWN is not valid for accepted rows. |
| origin_key | First Known Acquisition Source inherited from the MQL. | ANALYTICAL_KEY | NO | MQL relationship | Lookup by `mql_id`; do not infer from downstream behavior. | Must equal the related MQL origin for the same snapshot. |
| contact_date_key | MQL cohort date inherited from the MQL. | ANALYTICAL_KEY | NO | MQL relationship | Lookup by `mql_id`. | Must equal the related MQL contact date. |
| won_date_key | Calendar date of successful commercial close. | ANALYTICAL_KEY | NO | `won_date` | Date portion resolved through `dim_date`. | Referential integrity required. |
| won_timestamp | Exact observed successful-close timestamp. | TIMESTAMP | NO | `won_date` | Parsed without timezone invention. | Must not precede the start of `contact_date_key`; timezone remains source-naive. |
| closed_deal_count | Additive successful-close indicator. | INTEGER | NO | Derived | Constant `1`. | Exactly 1. |
| acquired_seller_count | Additive acquired-seller indicator under validated 1:1 mapping. | INTEGER | NO | Derived | Constant `1` while `seller_id` remains unique. | Exactly 1; load must fail if uniqueness contract drifts. |
| source_snapshot_id | Governed source-copy identifier. | STRING | NO | Acquisition metadata | Assigned to compatible Funnel snapshot. | Nonblank and reproducible. |
| source_file_name | Non-personal source filename. | STRING | NO | Acquisition metadata | Constant for Closed Deals source. | No personal path or credential. |

`business_segment`, `lead_type`, `lead_behaviour_profile`, and `business_type` are retained in raw lineage but deferred from the MVP analytical surface. They are event-time descriptors without a prioritized question or stable dimensional contract.

### fct_seller_lifecycle

**TABLE PURPOSE:** preserve reproducible acquired-seller activation evaluation as of a declared cutoff and rule/source version.

**GRAIN:** one row per acquired seller, observation cutoff timestamp, lifecycle rule version, and source snapshot.

**LOGICAL PRIMARY KEY:** `(seller_key, observation_cutoff_timestamp, lifecycle_rule_version, source_snapshot_id)`.

**SOURCE/NATURAL KEY:** derived identity `(seller_id, observation_cutoff_timestamp, lifecycle_rule_version, source_snapshot_id)`; no independent source key exists.

**FOREIGN KEYS:** `seller_key -> dim_seller`; `origin_key -> dim_origin`; `won_date_key`, `activation_date_key`, and `observation_cutoff_date_key -> dim_date`.

| Logical name | Semantic definition | Logical type | Nullable | Source | Derivation rule | Business constraints |
| --- | --- | --- | --- | --- | --- | --- |
| seller_key | Acquired seller being evaluated. | ANALYTICAL_KEY | NO | Closed Deal lineage | Resolve acquired `seller_id`. | One evaluation per complete logical key. |
| origin_key | First Known Acquisition Source of the acquired seller. | ANALYTICAL_KEY | NO | Closed Deal/MQL lineage | Inherited from acquisition event. | Must equal related ClosedDeal origin. |
| won_date_key | Date role for the acquisition close. | ANALYTICAL_KEY | NO | Closed Deal | Resolve date portion of `won_timestamp`. | Must equal related ClosedDeal won date. |
| won_timestamp | Successful acquisition timestamp used for temporal ordering. | TIMESTAMP | NO | Closed Deal | Preserved. | Earlier bound for eligible activation event. |
| activation_date_key | Date of first eligible Order within 90 days, or technical not-observed member. | ANALYTICAL_KEY | NO | Derived Order Item event | Resolve first qualifying purchase date; use `NOT_OBSERVED` if no qualifying activation is observed by cutoff. | Must be calendar member iff activation timestamp is present. |
| activation_timestamp | First delivered Order purchase strictly after won timestamp and no more than 90 days later. | TIMESTAMP | YES | Derived from Order Items + Orders | Minimum qualifying purchase timestamp. | NULL when no qualifying activation is observed by cutoff. |
| observation_cutoff_date_key | Date role of the as-of cutoff. | ANALYTICAL_KEY | NO | Governed run metadata | Date portion of cutoff. | Must resolve to a calendar member. |
| observation_cutoff_timestamp | Inclusive upper bound of source evidence used by the evaluation. | TIMESTAMP | NO | Governed run metadata | Declared for the published snapshot. | Must be at or after won timestamp. |
| lifecycle_rule_version | Version of eligibility, temporal, and maturity rules. | STRING | NO | Governed metadata | Assigned on rule publication. | Nonblank; immutable for a published row. |
| source_snapshot_id | Source snapshot set used for the result. | STRING | NO | Acquisition metadata | Identifies compatible Funnel/e-commerce inputs. | Nonblank; immutable for a published row. |
| is_mature_90d | Whether the cutoff is at least 90 days after won timestamp. | BOOLEAN | NO | Derived | `observation_cutoff_timestamp >= won_timestamp + 90 days`. | Controls activation-rate denominator eligibility. |
| is_activated_90d | Tri-state activation result. | BOOLEAN | YES | Derived | TRUE when qualifying first Order is observed; FALSE only when mature and none is observed; NULL when immature and no qualifying event is yet observed. | Never FALSE for an immature row. |
| mature_seller_count | Additive denominator indicator within one snapshot version. | INTEGER | NO | Derived | 1 when mature, otherwise 0. | Exactly 0 or 1. |
| activated_seller_count | Additive numerator indicator within one snapshot version. | INTEGER | NO | Derived | 1 only when mature and activated within 90 days, otherwise 0. | Cannot exceed `mature_seller_count`. |
| time_to_first_order_days | Elapsed fractional days to the qualifying activation Order. | DECIMAL | YES | Derived | Difference between won timestamp and the first delivered purchase in `(won_timestamp, won_timestamp + 90 days]`. | Greater than 0 and no more than 90 when present; non-additive. |
| first_eligible_order_id | First delivered post-win Order that satisfies the 90-day activation rule. | STRING | YES | Derived | Deterministic minimum qualifying purchase timestamp, then order_id tie-break. | Required exactly when an activation is observed. |
| first_eligible_order_timestamp | Purchase timestamp of `first_eligible_order_id`. | TIMESTAMP | YES | Derived | Same deterministic activation-event rule. | Strictly after won timestamp, no more than 90 days later, and no later than cutoff. |

Published rows are immutable. A changed cutoff, rule, or source snapshot appends a new logical version. Consumers must select exactly one compatible version before aggregating lifecycle measures.

### fct_order_item

**TABLE PURPOSE:** represent seller-assigned marketplace items and additive eligible GMV without copying Order- or Payment-level totals.

**GRAIN:** one row per source `(order_id, order_item_id)`.

**LOGICAL PRIMARY KEY:** `(order_id, order_item_id)`.

**SOURCE/NATURAL KEY:** `(order_id, order_item_id)` from Olist Order Items.

**FOREIGN KEYS:** `seller_key -> dim_seller`; `origin_key -> dim_origin`; `purchase_date_key` and `seller_won_date_key -> dim_date`.

| Logical name | Semantic definition | Logical type | Nullable | Source | Derivation rule | Business constraints |
| --- | --- | --- | --- | --- | --- | --- |
| order_id | Marketplace Order identifier and degenerate dimension. | STRING | NO | Order Items | Preserved. | Nonblank; must resolve to exactly one Orders header. |
| order_item_id | Item sequence within an Order. | INTEGER | NO | Order Items | Preserved. | Positive; unique with `order_id`. |
| seller_key | Conformed seller responsible for the item. | ANALYTICAL_KEY | NO | Order Items | Resolve `seller_id` through `dim_seller`. | Referential integrity required. |
| origin_key | Acquisition origin for acquired sellers, otherwise technical N/A. | ANALYTICAL_KEY | NO | ClosedDeal/MQL lineage | Resolve seller acquisition origin; use `NOT_APPLICABLE` for e-commerce-only sellers. | Must not infer origin from downstream activity. |
| purchase_date_key | Role-playing purchase date. | ANALYTICAL_KEY | NO | Orders | Date portion of `order_purchase_timestamp`. | Referential integrity required. |
| order_purchase_timestamp | Exact Order purchase timestamp propagated to item grain. | TIMESTAMP | NO | Orders | Join by `order_id`. | Same for all items of an Order. |
| seller_won_date_key | Acquisition-date role for acquired seller, otherwise technical N/A. | ANALYTICAL_KEY | NO | Closed Deal lineage | Date portion of seller won timestamp or N/A. | Calendar member iff seller is acquired. |
| seller_won_timestamp | Exact acquisition timestamp for temporal evaluation. | TIMESTAMP | YES | Closed Deal lineage | Propagated only for acquired sellers. | NULL iff acquisition is not applicable. |
| order_status | Order status propagated from header. | STRING | NO | Orders | Join by `order_id`. | One of `created`, `approved`, `invoiced`, `processing`, `shipped`, `delivered`, `unavailable`, `canceled`. |
| item_price | Source item sale value excluding freight. | DECIMAL | NO | Order Items `price` | Preserved. | Non-negative. |
| freight_value | Source freight value retained for analysis but excluded from GMV. | DECIMAL | NO | Order Items | Preserved. | Non-negative; never added to eligible GMV. |
| order_item_count | Additive item-row indicator. | INTEGER | NO | Derived | Constant `1`. | Exactly 1; never use as an Order count. |
| is_acquired_seller | Whether seller has valid ClosedDeal acquisition lineage. | BOOLEAN | NO | Derived | TRUE when seller resolves to one accepted ClosedDeal. | Drives applicability of attribution fields. |
| is_eligible_order | Whether the Order meets the frozen status rule. | BOOLEAN | NO | Derived | `order_status = 'delivered'`. | Must match status exactly. |
| is_post_acquisition | Whether purchase is strictly after seller won timestamp. | BOOLEAN | YES | Derived | Compare purchase and won timestamps. | NULL for non-acquired seller; otherwise non-null. |
| is_within_90d_of_acquisition | Whether purchase is in `(won_timestamp, won_timestamp + 90 days]`. | BOOLEAN | YES | Derived | Timestamp comparison. | NULL for non-acquired seller; TRUE implies post-acquisition. |
| eligible_gmv_amount | Additive MVP GMV contribution of this item. | DECIMAL | NO | Derived | `item_price` when acquired seller, delivered Order, and strictly post-acquisition; otherwise 0. | Non-negative; freight and payment value excluded. |
| source_snapshot_id | Governed e-commerce/acquisition snapshot set. | STRING | NO | Acquisition metadata | Assigned to compatible source copies. | Nonblank and reproducible. |
| source_file_name | Non-personal Order Items source filename. | STRING | NO | Acquisition metadata | Constant for source table. | No personal path or credential. |

Zero is correct for `eligible_gmv_amount` on an observed but non-qualifying item because the row contributes zero to the governed additive measure. A row with missing price, status, timestamp, seller, or required lineage fails/quarantines instead of being coerced to zero. Order counts always use distinct identifiers; no Order total or `payment_value` is duplicated onto items.

### fct_marketing_spend

**TABLE PURPOSE:** hold future deterministic synthetic advertising-spend scenarios at a source-origin/day grain.

**GRAIN:** one row per `(spend_date, source_origin, scenario_id)`.

**LOGICAL PRIMARY KEY:** `(spend_date_key, origin_key, scenario_id)`.

**SOURCE/NATURAL KEY:** `(spend_date, source_origin, scenario_id)`, resolved through `dim_date` and `dim_origin`.

**FOREIGN KEYS:** `spend_date_key -> dim_date.date_key`; `origin_key -> dim_origin.origin_key`.

| Logical name | Semantic definition | Logical type | Nullable | Source | Derivation rule | Business constraints |
| --- | --- | --- | --- | --- | --- | --- |
| spend_date_key | Role-playing spend date. | ANALYTICAL_KEY | NO | Synthetic contract | Resolve generated date through `dim_date`. | Must resolve to a calendar member. |
| origin_key | Governed raw origin/channel mapping for spend. | ANALYTICAL_KEY | NO | Synthetic contract | Resolve declared `source_origin` through the approved mapping version. | `NOT_APPLICABLE` is forbidden; Campaign is absent. |
| scenario_id | Explicit synthetic scenario identity. | STRING | NO | Generator configuration | Supplied before generation. | Nonblank; alternative scenarios must not be summed. |
| methodology_version | Version of the generation method and constraints. | STRING | NO | Generator configuration | Supplied before generation. | Nonblank and stable within scenario. |
| generation_seed | Deterministic random seed. | INTEGER | NO | Generator configuration | Supplied, never inferred from outcomes. | Stable within scenario/methodology. |
| currency | Currency of spend values. | STRING | NO | Generator configuration | Explicit scenario parameter. | MVP accepted value `BRL`; no silent currency mixing. |
| spend_amount | Synthetic advertising cost for date/origin/scenario. | DECIMAL | NO | Generated | Deterministic method independent of downstream outcomes. | Greater than or equal to 0. |
| data_classification | Evidential classification of every spend row. | STRING | NO | Constant | Constant `SYNTHETIC`. | Exact accepted value `SYNTHETIC`; unequivocally synthetic and never presented as observed Olist data. |

Absence of a spend row means spend is not observed/generated for that grain and must not be interpreted as zero. A zero row is allowed only when explicitly produced by the declared methodology.

## Logical referential integrity

| Fact reference | Required policy |
| --- | --- |
| `fct_mql.origin_key -> dim_origin` | Non-null; missing raw origin resolves to governed unattributed member. |
| `fct_closed_deal.seller_key -> dim_seller` | Non-null; accepted acquisitions cannot use UNKNOWN seller. |
| `fct_closed_deal.origin_key -> dim_origin` | Non-null and equal to related MQL origin. |
| `fct_seller_lifecycle.seller_key -> dim_seller` | Non-null acquired seller. |
| `fct_seller_lifecycle.origin_key -> dim_origin` | Non-null and equal to acquisition event origin. |
| `fct_order_item.seller_key -> dim_seller` | Non-null; all source seller IDs are conformed before facts. |
| `fct_order_item.origin_key -> dim_origin` | Acquisition member when attributable; `NOT_APPLICABLE` otherwise. |
| `fct_marketing_spend.origin_key -> dim_origin` | Non-null governed origin; cannot use `NOT_APPLICABLE`. |
| All fact date keys -> `dim_date` | Non-null; use governed technical member only where the role is genuinely unknown, not observed, or not applicable. |

Rows with an invalid required business key are rejected or quarantined rather than silently attached to an UNKNOWN seller. Technical UNKNOWN members preserve referential integrity for genuinely missing descriptive context, not for bypassing candidate-key violations.

## Physical model boundary

The following remain explicitly deferred: PostgreSQL types and schema names, physical constraints, surrogate-key encoding, indexes, partitions, clustering, dbt materializations, incremental loading, late-arriving-dimension handling, and deployment/runtime choices.
