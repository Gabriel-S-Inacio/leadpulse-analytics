# MVP Conceptual Dimensional Model

## Purpose and boundary

This document designs the MVP analytical model from business-process grain and frozen semantics. It is a conceptual model: names describe analytical responsibilities, not implemented relations or executable DDL.

The design must answer the prioritized acquisition, activation, and downstream-performance questions without treating AcquiredSeller as EndCustomer, ClosedDeal as Order, GMV as corporate revenue, or Campaign as an available dimension.

## Prioritized business questions

1. How many MQLs does each source_origin generate?
2. What is the MQL-to-AcquiredSeller conversion rate by origin?
3. How many acquired sellers activate within 90 days?
4. What is Seller Activation Rate by origin?
5. How much GMV do acquired sellers generate?
6. What is GMV per Activated Seller?
7. How many Orders are generated per Activated Seller?
8. How long do sellers take to activate?
9. How much future controlled synthetic spend is associated with each origin?
10. What are future scenario Seller Acquisition Cost and GMV ROAS by origin?

## Business process grains

### MQL process

**Chosen grain:** one row per source `mql_id`, representing the first MQL record observed by LeadPulse.

`mql_id` is unique in the profiled source, and `first_contact_date` is the cohort event. This grain supports additive MQL event counting and retains `landing_page_id` as context without inventing a Campaign.

### Closed deal process

**Chosen grain:** one row per valid successful seller-acquisition close, identified by source `mql_id` in the current contract.

The observed copy has unique `mql_id`, unique `seller_id`, and a 1:1 mapping. The fact remains separate from MQL because won_date is a distinct event and only successful outcomes exist in Closed Deals. The `(mql_id, seller_id)` pair is retained as a lineage check; source contracts must be revalidated on refresh.

### Acquired seller and lifecycle process

**Chosen grain:** no duplicate acquisition event fact. Acquisition is represented canonically by `fct_closed_deal`; the seller entity is represented by `dim_seller`; a derived `fct_seller_lifecycle` has one versioned-snapshot row per acquired `seller_id`, observation cutoff, lifecycle rule version, and source snapshot for activation evaluation.

This separation avoids storing event timestamps and derived metrics in `dim_seller`. The lifecycle grain is justified because activation combines a ClosedDeal event, later Order Items, eligibility rules, a reporting cutoff, and 90-day cohort maturity.

### Order item process

**Chosen grain:** one row per source `(order_id, order_item_id)`.

GMV and seller assignment exist at Order Item grain. Preserving this grain prevents whole-Order value from being copied to multiple sellers. Order header context needed by the MVP is propagated to the item fact under governed rules; a second order fact is not required.

### Marketing spend process

**Chosen grain:** one row per `(spend_date, source_origin, scenario_id)`.

This is the frozen future synthetic-source grain. `source_origin` aligns with outcomes through `dim_origin`, and `scenario_id` prevents different synthetic scenarios from being summed together. No rows exist until deterministic generation is separately authorized.

## Fact model

### fct_mql

**PURPOSE:** count MQL acquisition entries and provide the denominator/cohort for MQL-to-AcquiredSeller conversion.

**GRAIN:** one row per `mql_id`.

**NATURAL SOURCE KEY:** `mql_id`.

**FOREIGN KEYS:** contact date role of `dim_date`; `dim_origin`.

**DEGENERATE DIMENSIONS:** `mql_id`, `landing_page_id`, source/provenance identifier.

**MEASURES:** `mql_count = 1`.

**EVENT TIMESTAMP:** `first_contact_date`.

**ADDITIVITY:** `mql_count` is additive across disjoint contact-date and origin slices because the fact has one row per MQL.

**SOURCE:** Olist Marketing Qualified Leads.

**BUSINESS RULES:** preserve raw source_origin; apply only the frozen minimal Channel mapping; missing/unknown origin maps to the `unattributed` origin member; Campaign is absent.

**KNOWN RISKS:** the source begins at MQL rather than visitor/lead creation; conversion cohorts are right-censored and require an explicit as-of cutoff.

**MVP STATUS:** INCLUDE.

### fct_closed_deal

**PURPOSE:** represent the successful B2B acquisition event and count ClosedDeals/AcquiredSellers without adding nullable close fields to `fct_mql`.

**GRAIN:** one row per valid ClosedDeal/converted `mql_id`.

**NATURAL SOURCE KEY:** `mql_id`; `seller_id` is an observed alternate unique key, and `(mql_id, seller_id)` is the lineage pair.

**FOREIGN KEYS:** won-date role and inherited MQL contact-date role of `dim_date`; `dim_origin`; `dim_seller`.

**DEGENERATE DIMENSIONS:** `mql_id`, source/provenance identifier. Closed-deal descriptive fields remain source attributes and do not become dimensions in the MVP.

**MEASURES:** `closed_deal_count = 1`; `acquired_seller_count = 1` under the validated 1:1 contract.

**EVENT TIMESTAMP:** `won_date`; `first_contact_date` is retained only as cohort context.

**ADDITIVITY:** both count indicators are additive across disjoint won/contact cohorts and origins in the observed 1:1 source. Distinct seller counting remains the defensive semantic definition.

**SOURCE:** Olist Closed Deals enriched only with MQL lineage for contact cohort and First Known Acquisition Source.

**BUSINESS RULES:** only valid rows with non-null linked `mql_id` and `seller_id`; origin comes from the MQL acquisition event; no Opportunity is inferred.

**KNOWN RISKS:** only successful deals are present; 462 observed ClosedDeal sellers do not appear in the e-commerce seller snapshot; future cardinality drift would invalidate additive acquired-seller indicators.

**MVP STATUS:** INCLUDE.

### fct_seller_lifecycle

**PURPOSE:** materialize reproducible, versioned acquisition-to-activation evaluations without placing event outcomes in `dim_seller`.

**GRAIN:** one row per acquired `seller_id`, observation cutoff, lifecycle rule version, and source snapshot.

**NATURAL SOURCE KEY:** no independent source key exists because this is derived. The derivation identity is `(seller_id, observation_cutoff_timestamp, lifecycle_rule_version, source_snapshot_id)`.

**FOREIGN KEYS:** `dim_seller`; `dim_origin`; won-date, activation-date, and observation-cutoff roles of `dim_date`.

**DEGENERATE DIMENSIONS:** lifecycle rule version, source snapshot identifier, and observation cutoff timestamp.

**MEASURES:** mature-seller indicator, activated-within-90-days indicator, `time_to_first_order_days`. Acquisition total remains canonical in `fct_closed_deal`.

**EVENT TIMESTAMP:** `won_date`, nullable first eligible `order_purchase_timestamp`, and explicit observation cutoff.

**ADDITIVITY:** maturity and activation indicators are additive only across disjoint cohorts/origins within one selected cutoff, rule version, and source snapshot. Duration is non-additive and must be summarized by a distribution.

**SOURCE:** derived from `fct_closed_deal` and eligible, post-win `fct_order_item` events under the frozen 90-day rule.

**BUSINESS RULES:** eligible means delivered; purchase must be in `(won_date, won_date + 90 days]`; only time-mature cohorts enter the activation-rate denominator; missing downstream events mean not observed activated, not proven real-world inactivity.

**KNOWN RISKS:** empirical cutoff is not a source-provided extraction timestamp; snapshot mismatch can look like non-activation; queries that fail to select one snapshot version will double count sellers.

**MVP STATUS:** INCLUDE as a derived lifecycle mart, not a raw-source fact.

### fct_order_item

**PURPOSE:** central downstream transaction fact for seller-order participation and GMV.

**GRAIN:** one row per `(order_id, order_item_id)`.

**NATURAL SOURCE KEY:** `(order_id, order_item_id)`.

**FOREIGN KEYS:** purchase-date role and acquired-seller won-date cohort role of `dim_date`; `dim_seller`; attributed `dim_origin` when acquisition lineage exists.

**DEGENERATE DIMENSIONS:** `order_id`, `order_item_id`, `order_status`, eligibility/post-acquisition rule indicators, and source/provenance identifier. `product_id` remains available in raw lineage while `dim_product` is deferred; it is not exposed as an unsupported analytical dimension.

**MEASURES:** `order_item_count = 1`, `item_price`, and retained `freight_value`; acquisition-window state is derived from event timestamps. Only eligible `item_price` contributes to GMV; freight is never a GMV component.

**EVENT TIMESTAMP:** `order_purchase_timestamp`. Seller acquisition date is cohort context, not the Order Item event.

**ADDITIVITY:** item price is additive across items, sellers, origins, and purchase periods after the delivered/post-win filters. Freight is separately additive but not GMV. Order count is not additive at this grain.

**SOURCE:** Olist Order Items joined to Orders for status/purchase context and to validated ClosedDeal/MQL lineage for acquired-seller attribution.

**BUSINESS RULES:** GMV equals delivered, post-win acquired-seller `item_price`; `payment_value` is absent; First Known Acquisition Source is propagated from the seller's acquisition event; e-commerce-only sellers receive a not-applicable acquisition member and are excluded from acquired-seller KPIs.

**KNOWN RISKS:** one Order may contain multiple items and sellers; summing an order indicator would double count; Channel slices of Orders are non-additive; source does not expose complete refunds.

**MVP STATUS:** INCLUDE.

### fct_marketing_spend

**PURPOSE:** support future, explicitly synthetic CPL, Seller Acquisition Cost, and GMV ROAS scenarios at a compatible origin/date grain.

**GRAIN:** one row per `(spend_date, source_origin, scenario_id)`.

**NATURAL SOURCE KEY:** `(spend_date, source_origin, scenario_id)`.

**FOREIGN KEYS:** spend-date role of `dim_date`; `dim_origin`.

**DEGENERATE DIMENSIONS:** `scenario_id`, methodology version, generation seed, currency, SYNTHETIC classification.

**MEASURES:** `spend_amount`.

**EVENT TIMESTAMP:** `spend_date`.

**ADDITIVITY:** spend is additive across dates and origins only within the same scenario, methodology version, and currency. It is non-additive across alternative scenarios.

**SOURCE:** future deterministic LeadPulse-generated source; no current records.

**BUSINESS RULES:** non-negative BRL scenario values, frozen origin mapping, no Campaign, deterministic seed, explicit labeling, and no downstream-outcome leakage.

**KNOWN RISKS:** synthetic cost cannot be represented as observed Olist performance; mixing scenarios or currencies produces invalid totals.

**MVP STATUS:** INCLUDE in the conceptual model; population is deferred.

### fct_order

**PURPOSE:** considered for one-row-per-order measures.

**GRAIN:** would be one row per `order_id`.

**NATURAL SOURCE KEY:** `order_id`.

**FOREIGN KEYS:** would include purchase date and EndCustomer, but neither creates value for the prioritized seller-attributed questions beyond context already available to Order Items.

**DEGENERATE DIMENSIONS:** order status and order identifier.

**MEASURES:** no approved additive MVP measure; payment totals are not GMV.

**EVENT TIMESTAMP:** `order_purchase_timestamp`.

**ADDITIVITY:** an order indicator would be additive overall but cannot allocate one multi-seller Order additively across sellers/origins.

**SOURCE:** Olist Orders.

**BUSINESS RULES:** delivered eligibility would still apply.

**KNOWN RISKS:** duplicates the Order context propagated to `fct_order_item` and encourages fragile whole-Order attribution to sellers.

**MVP STATUS:** REJECT. Reconsider only if future prioritized order-level or EndCustomer questions require a header-grain fact.

## Dimension model

### dim_date

**PURPOSE:** one conformed calendar used through role-playing foreign keys.

**BUSINESS VALUE:** consistent daily, monthly, quarterly, and yearly slicing across acquisition, activation, Orders, and future spend.

**SOURCE:** generated deterministic calendar bounded to source dates plus controlled future coverage.

**NATURAL KEY:** calendar date.

**SCD STRATEGY:** Type 0; calendar attributes do not change.

**ATTRIBUTES:** calendar date, day, month, month name/number, quarter, year, weekday, and weekend indicator. Holiday/fiscal attributes are not required.

**USED BY WHICH FACTS:** all included facts through contact, won, purchase, activation, cutoff, or spend roles.

**MVP STATUS:** INCLUDE.

### dim_origin

**PURPOSE:** conform raw acquisition source and minimal normalized Channel across real outcomes and synthetic spend.

**BUSINESS VALUE:** answers every prioritized by-origin question without repeating mapping logic or introducing Campaign.

**SOURCE:** distinct Marketing Funnel origin values plus governed technical members.

**NATURAL KEY:** stable `origin_member_code`; raw null cannot serve as a key.

**SCD STRATEGY:** Type 1 for the static MVP, with mapping version and explicit restatement on correction. Type 2 is deferred until effective-dated source history exists.

**ATTRIBUTES:** raw `source_origin`, normalized `channel`, classification, mapping version, and source-value status. Classification distinguishes observed, explicit unknown, missing/unrecognized, and not applicable.

**USED BY WHICH FACTS:** `fct_mql`, `fct_closed_deal`, `fct_seller_lifecycle`, `fct_order_item`, and future `fct_marketing_spend`.

**MVP STATUS:** INCLUDE.

Mapping preservation:

- `source_origin` keeps the exact observed raw value when present.
- normalized `channel` is semantically equivalent to the observed origin except `direct_traffic → direct` and `unknown`/null/unrecognized → `unattributed`.
- a separate `not_applicable` technical member represents e-commerce sellers with no funnel-acquisition lineage; it is not merged into `unattributed`.
- `classification` records why the member exists; no Campaign column is introduced.

### dim_seller

**PURPOSE:** conform the marketplace seller entity across acquisition, lifecycle, and Order Item processes.

**BUSINESS VALUE:** provides a stable seller join while keeping event-specific acquisition and activation data in facts.

**SOURCE:** union of seller_id values from Olist Sellers and Closed Deals. Funnel-only sellers receive placeholder descriptive attributes rather than being dropped.

**NATURAL KEY:** `seller_id`.

**SCD STRATEGY:** Type 1 for the MVP snapshot; the source provides no seller-attribute history. Future effective-dated changes require a separate decision.

**ATTRIBUTES:** seller_id, seller city/state/ZIP context when observed, and source-coverage classification (`both`, `funnel_only`, or `ecommerce_only`).

**USED BY WHICH FACTS:** `fct_closed_deal`, `fct_seller_lifecycle`, and `fct_order_item`.

**MVP STATUS:** INCLUDE.

Seller acquisition fields are deliberately excluded: won_date is an event, source_origin belongs to acquisition/attribution, and activation fields are derived lifecycle outcomes. `business_segment`, `lead_type`, and `lead_behaviour_profile` describe the close/lead snapshot rather than stable seller identity.

### dim_end_customer

**PURPOSE:** would conform final marketplace buyers.

**BUSINESS VALUE:** none of the prioritized MVP questions analyzes buyer behavior.

**SOURCE:** Olist Customers.

**NATURAL KEY:** `customer_unique_id` would represent cross-order identity; `customer_id` is order-scoped and cannot be used interchangeably.

**SCD STRATEGY:** not selected; source history and privacy-safe requirements must be evaluated first.

**ATTRIBUTES:** deferred.

**USED BY WHICH FACTS:** no included MVP fact.

**MVP STATUS:** DEFER. EndCustomer remains explicitly separate from AcquiredSeller.

### dim_product

**PURPOSE:** would support product/category analysis of Order Items.

**BUSINESS VALUE:** product analysis is outside the prioritized MVP questions.

**SOURCE:** Olist Products and category translation.

**NATURAL KEY:** `product_id`.

**SCD STRATEGY:** not selected; no product history is provided.

**ATTRIBUTES:** deferred; product_id remains available in raw lineage for a future governed extension.

**USED BY WHICH FACTS:** future extension of `fct_order_item`.

**MVP STATUS:** DEFER.

### dim_geography

**PURPOSE:** considered for conformed geographic analysis.

**BUSINESS VALUE:** no prioritized MVP question requires geography, and the geolocation source has substantial duplicate rows.

**SOURCE:** Olist Sellers, Customers, and Geolocation.

**NATURAL KEY:** no governed common geographic entity key has been approved.

**SCD STRATEGY:** not applicable in the MVP.

**ATTRIBUTES:** minimal seller city/state/ZIP context stays in `dim_seller`; no separate geography dimension is created.

**USED BY WHICH FACTS:** none.

**MVP STATUS:** REJECT as a standalone MVP dimension; reconsider if geography becomes a business requirement.

### dim_business_segment

**PURPOSE:** could describe the business segment recorded at successful close.

**BUSINESS VALUE:** potentially useful for acquisition segmentation, but not required by the prioritized origin questions.

**SOURCE:** Olist Closed Deals.

**NATURAL KEY:** normalized business-segment value, not yet governed.

**SCD STRATEGY:** not selected; source provides a close-time value without history.

**ATTRIBUTES:** deferred.

**USED BY WHICH FACTS:** future extension of `fct_closed_deal` and lifecycle marts.

**MVP STATUS:** DEFER.

### dim_lead_profile

**PURPOSE:** considered for lead_type and lead_behaviour_profile combinations.

**BUSINESS VALUE:** not required by prioritized questions; behaviour profile is null for 21.02% of Closed Deals and contains multi-valued labels.

**SOURCE:** Olist Closed Deals.

**NATURAL KEY:** no stable governed profile key exists.

**SCD STRATEGY:** not applicable.

**ATTRIBUTES:** source fields remain preserved outside the MVP dimensional surface.

**USED BY WHICH FACTS:** none.

**MVP STATUS:** REJECT as a standalone dimension. Reconsider only with a concrete question and normalization contract.

## Seller modeling decision

`dim_seller` contains seller identity, stable observed seller descriptors, and source-coverage classification. Acquisition remains in `fct_closed_deal`; activation remains in `fct_seller_lifecycle`.

- **won_date:** factual event timestamp on `fct_closed_deal` and lifecycle milestone, never a static seller attribute.
- **source_origin:** property of the MQL acquisition event. It is conformed through `dim_origin` and propagated as governed attribution context to downstream facts, not stored as intrinsic seller identity.
- **business_segment:** close-time descriptor with no demonstrated stability; deferred rather than placed on the seller dimension.
- **lead_type / lead_behaviour_profile:** lead/close snapshot descriptors, outside the MVP dimensional surface.
- **seller geography:** stable descriptive context may remain directly on `dim_seller`; a separate geography dimension has no current value.

## Date model

One `dim_date` is role-played; separate physical date dimensions are not designed.

| Role-playing key | Fact usage |
| --- | --- |
| contact_date_key | MQL event; ClosedDeal conversion cohort |
| won_date_key | ClosedDeal event; seller lifecycle cohort; Order Item acquisition context |
| purchase_date_key | Order Item event; lifecycle activation milestone source |
| activation_date_key | Nullable first eligible Order date on seller lifecycle |
| observation_cutoff_date_key | Lifecycle maturity evaluation |
| spend_date_key | Future synthetic spend event |

Exact timestamps remain on event/lifecycle facts where ordering or duration is required; a date key does not replace time-of-day semantics.

## Order counting and GMV

`fct_order_item` is the central transaction fact. `fct_order` is rejected for the MVP because it would duplicate header context without solving seller attribution.

- Overall eligible Orders: distinct `order_id` after delivered, acquired-seller, and post-win rules.
- Seller/origin Orders: distinct `(seller_id, order_id)` participation; these slices are non-additive across sellers/origins.
- Never sum `order_item_count` as an Order count.
- GMV: additive sum of eligible `item_price` at item grain.
- Never copy an Order-level payment total onto items or use payment_value as seller GMV.

If distinct counting becomes operationally expensive, a future purpose-built aggregate may be added without changing the canonical transaction grain. That is not justification for a second source-level fact now.

## Activation modeling

The model chooses option **B: materialized versioned seller lifecycle snapshot**.

`fct_seller_lifecycle` represents acquired seller, first eligible Order, nullable activation date, 90-day activation indicator, cohort-maturity indicator, observation cutoff, and `time_to_first_order_days`. Its logical identity includes seller, cutoff, rule version, and source snapshot. Rows are immutable across published versions. It is not a dimension and does not replace the canonical ClosedDeal acquisition count.

This design makes the maturity denominator and historical cutoff reproducible, prevents metrics from becoming mutable seller attributes, and avoids recomputing first-event logic independently in every KPI. Consumers must select exactly one published lifecycle version.

## Additivity

| Measure | Classification | Rule |
| --- | --- | --- |
| mql_count | ADDITIVE | Sum across disjoint contact-date/origin slices at one row per MQL. |
| acquired_seller_count | ADDITIVE under current contract | Sum from `fct_closed_deal`; validate unique seller_id on every refresh. |
| order_item_price / GMV | ADDITIVE | Sum eligible item price; do not add freight or Payments. |
| order_count | NON-ADDITIVE at item grain | Use distinct order_id overall or distinct seller_id/order_id by seller slice. |
| activated_seller_count | SEMI-ADDITIVE | Sum only across disjoint cohorts/origins at the same cutoff/rule version. |
| marketing_spend | ADDITIVE within scenario | Never sum across scenario, methodology, or incompatible currency versions. |

Rates, per-seller ratios, durations, medians, and percentiles are non-additive and must be recomputed from their components at the requested grain.

## Bus matrix

`R:<role>` indicates a role-playing use of the conformed dimension.

| Fact | dim_date | dim_origin | dim_seller |
| --- | --- | --- | --- |
| fct_mql | R: contact | Yes | — |
| fct_closed_deal | R: contact, won | Yes | Yes |
| fct_seller_lifecycle | R: won, activation, cutoff | Yes | Yes |
| fct_order_item | R: purchase, seller acquisition | Yes, attributed | Yes |
| fct_marketing_spend | R: spend | Yes | — |

`dim_date` and `dim_origin` are conformed across all included facts. `dim_seller` is conformed across acquisition and downstream seller processes. Scenario, order identifiers, landing page, status, and product reference remain degenerate context rather than standalone MVP dimensions.

## KPI traceability

| KPI / question | Source fact(s) | Required dimensions | Aggregation notes |
| --- | --- | --- | --- |
| MQLs by origin | fct_mql | contact-date role, dim_origin | Sum mql_count. |
| MQL → AcquiredSeller Conversion | fct_mql + fct_closed_deal | contact-date role, dim_origin | Divide converted seller count by MQL count at the same contact cohort/origin and cutoff; do not join facts row-by-row in the consumption layer. |
| Acquired Sellers | fct_closed_deal | won/contact-date roles, dim_origin, dim_seller | Distinct seller_id is canonical; count indicator is safe only while 1:1 contract holds. |
| Activated Sellers within 90 days | fct_seller_lifecycle | won-date role, dim_origin, dim_seller | Sum activation indicator only for mature cohort rows at one cutoff/rule version. |
| Seller Activation Rate | fct_seller_lifecycle | won-date and cutoff roles, dim_origin | Sum activated indicator / sum mature indicator; incomplete cohorts excluded. |
| Orders from Acquired Sellers | fct_order_item | purchase-date role, dim_origin, dim_seller | Distinct order_id overall; distinct seller_id/order_id by seller/origin. |
| GMV from Acquired Sellers | fct_order_item | purchase-date role, dim_origin, dim_seller | Sum delivered, post-win item_price only. |
| GMV per Activated Seller | fct_order_item + fct_seller_lifecycle | won-date cohort role, dim_origin, dim_seller | 90-day cohort GMV / activated sellers using conformed cohort/origin and same mature population. |
| Orders per Activated Seller | fct_order_item + fct_seller_lifecycle | won-date cohort role, dim_origin, dim_seller | Distinct seller/order pairs in 90 days / activated sellers; same mature population. |
| Time to First Order | fct_seller_lifecycle | won/activation-date roles, dim_origin, dim_seller | Distribution of duration; never sum or impute non-activators. |
| Synthetic Marketing Spend | fct_marketing_spend | spend-date role, dim_origin | Sum only within one scenario/methodology/currency. |
| Scenario Seller Acquisition Cost | fct_marketing_spend + fct_closed_deal | date roles, dim_origin | Compatible scenario spend / acquired sellers; never use EndCustomer. |
| Scenario GMV ROAS | fct_marketing_spend + fct_order_item | date roles, dim_origin | Eligible item-price GMV / compatible scenario spend; not corporate return. |

Cross-fact ratios use separately aggregated components at conformed dimensional grain. They do not join raw fact rows to each other, which would multiply observations.

## Physical model deferred

This decision does not select:

- database or PostgreSQL schemas;
- surrogate-key data types;
- primary/foreign-key enforcement syntax;
- indexes or partitions;
- dbt materializations;
- incremental or late-arriving-data strategy;
- physical naming beyond conceptual analytical responsibilities.

Those choices require a later architecture and implementation phase.

## Remaining modeling risks

- The empirical e-commerce cutoff is not a source-provided extraction timestamp.
- Funnel-only sellers make observed non-activation sensitive to cross-source snapshot coverage.
- Future source refreshes must revalidate the observed ClosedDeal 1:1 cardinality.
- Refund/chargeback facts and timezone are unresolved upstream limitations.
- Cross-fact cohort ratios require one governed semantic layer even though their components share conformed dimensions.
