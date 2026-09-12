# KPI Contract

## Contract scope and status

This contract separates B2B seller acquisition from downstream e-commerce performance and distinguishes real Olist observations from controlled synthetic spend.

- **SUPPORTED:** source concepts exist; publication still depends on basic data-quality checks.
- **SYNTHETIC SCENARIO:** combines real Olist outcomes with controlled synthetic Advertising Spend and must be labeled accordingly.
- **COHORT-MATURE:** publishable only when the required observation window is complete at the declared cutoff.
- **NOT ACTIVE:** insufficient source observability or misleading semantics prevent an MVP KPI.

## Common conventions

- P is a half-open reporting interval: start inclusive and end exclusive.
- C is an AcquiredSeller cohort defined by ClosedDeal won_date.
- A is the frozen 90-day seller-activation window.
- S is an explicit source/reporting cutoff. For the current downstream snapshot it is the maximum observed Order purchase timestamp, `2018-10-17 17:30:18`.
- Counts use distinct source-supported conceptual identifiers, never raw row counts.
- First Known Acquisition Source follows the attribution contract: source_origin retains Lead origin, Channel uses the minimal frozen mapping, and Campaign is null in the MVP.
- An Eligible Order has source order_status exactly `delivered`.
- Acquired-seller downstream activity must have order_purchase_timestamp strictly later than that seller's won_date.
- Synthetic MarketingSpend is never presented as observed Olist spend.
- A complete slice with no qualifying records returns 0. Missing, inapplicable, or incomplete coverage returns null with a quality status.
- Division by zero returns null, never infinity.
- Monetary aggregation requires a common currency and an approved inclusion rule.
- Period filters follow each KPI's declared timestamp. Channel filters use normalized Lead origin for outcomes and compatible generated Channel for spend.
- Campaign filters are unavailable in the MVP. landing_page_id is not treated as Campaign.

## ACQUISITION KPIs

## Marketing Qualified Leads

**Status:** SUPPORTED — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How many Olist MQLs entered the observable seller-acquisition funnel?

### DEFINITION
Distinct Marketing Qualified Leads present in the Olist Marketing Funnel and first contacted in P.

### FORMULA
MQLs(P, d) = COUNT_DISTINCT(mql_id where first_contact_date is in P and acquisition source is in d)

### NUMERATOR
Distinct mql_id values after source-validity and duplicate checks.

### DENOMINATOR
Not applicable.

### GRAIN
source_origin/Channel/day or month and overall/period. landing_page_id may be a source-context drilldown. Campaign grain is unavailable in the MVP.

### TIME BASIS
first_contact_date.

### FILTER BEHAVIOR
Period filters first_contact_date. Channel uses the frozen source_origin mapping. Campaign filtering is unavailable in the MVP.

### ZERO / NULL BEHAVIOR
Return 0 for a complete slice with no MQLs; null when source coverage is incomplete.

### ATTRIBUTION DEPENDENCY
YES for Channel views; overall count is independent.

### KNOWN LIMITATIONS
The dataset begins with MQLs and does not represent all visitors, raw leads, or earlier interactions.

## Closed Deals

**Status:** SUPPORTED — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How many successful B2B seller-acquisition closes are observable?

### DEFINITION
Distinct valid ClosedDeal records linking an MQL to a seller. This is not an e-commerce Order.

### FORMULA
ClosedDeals(P, d) = COUNT_DISTINCT(closed_deal_identity where won_date is in P and Lead source is in d)

### NUMERATOR
Distinct valid source-qualified ClosedDeal identities after cardinality/duplicate rules.

### DENOMINATOR
Not applicable.

### GRAIN
source_origin/Channel/day or month and overall/period; Campaign grain is unavailable.

### TIME BASIS
Source won/close date.

### FILTER BEHAVIOR
Period filters won date. Channel inherits normalized source_origin through mql_id. Campaign filtering is unavailable.

### ZERO / NULL BEHAVIOR
Return 0 for a complete slice with no ClosedDeals; null when deal identity or source coverage is unresolved.

### ATTRIBUTION DEPENDENCY
YES for Channel views.

### KNOWN LIMITATIONS
Only successful close records are observed; absent rows do not reveal intermediate Opportunity state or a reason for loss.

## Acquired Sellers

**Status:** SUPPORTED — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How many distinct sellers were acquired through the observable marketing funnel?

### DEFINITION
Distinct seller_id values linked to a valid ClosedDeal.

### FORMULA
AcquiredSellers(P, d) = COUNT_DISTINCT(seller_id where seller_acquired_at is in P and Lead source is in d)

### NUMERATOR
Distinct acquired seller_id values.

### DENOMINATOR
Not applicable.

### GRAIN
source_origin/Channel/day or month and overall/period; Campaign grain is unavailable.

### TIME BASIS
seller_acquired_at, derived from the linked valid ClosedDeal won date.

### FILTER BEHAVIOR
Period filters seller acquisition. Channel inherits normalized Lead origin. EndCustomer filters never apply to this KPI.

### ZERO / NULL BEHAVIOR
Return 0 for complete coverage with no acquired sellers; null when seller/deal lineage is incomplete.

### ATTRIBUTION DEPENDENCY
YES for Channel views.

### KNOWN LIMITATIONS
Requires validated seller_id and mql_id cardinality and does not prove the seller was new to the platform before the observed close.

## Marketing Spend

**Status:** SYNTHETIC SCENARIO — CONTROLLED SYNTHETIC SOURCE.

### BUSINESS QUESTION
What advertising cost is assigned to a controlled analytical scenario?

### DEFINITION
Sum of generated spend observations under one disclosed scenario and methodology version.

### FORMULA
MarketingSpend(P, d, s) = SUM(spend_amount where spend_date is in P, origin is in d, and scenario is s)

### NUMERATOR
Synthetic spend amount in a common currency.

### DENOMINATOR
Not applicable.

### GRAIN
source_origin/Channel/day and overall/scenario period.

### TIME BASIS
Generated spend date or allocated interval.

### FILTER BEHAVIOR
Every result requires scenario and SYNTHETIC provenance. source_origin and Channel must follow the frozen mapping. Campaign is absent.

### ZERO / NULL BEHAVIOR
Return 0 only when an applicable, complete scenario intentionally generates no spend; null when no compatible scenario exists.

### ATTRIBUTION DEPENDENCY
NO; source_origin is directly assigned and Channel is deterministically mapped by the generation methodology.

### KNOWN LIMITATIONS
Not observed cost and unsuitable for claims about Olist's historical advertising efficiency.

## CPL (Cost per MQL)

**Status:** SYNTHETIC SCENARIO.

### BUSINESS QUESTION
Under a controlled spend scenario, how much generated advertising cost corresponds to each observed MQL?

### DEFINITION
Compatible synthetic MarketingSpend divided by real MQLs for the same Channel and period.

### FORMULA
ScenarioCPL(P, d, s) = MarketingSpend(P, d, s) / MQLs(P, d)

### NUMERATOR
Controlled synthetic MarketingSpend for Channel d in P and scenario s.

### DENOMINATOR
Distinct observed MQLs with first_contact_date in P and First Known Acquisition Source in Channel d.

### GRAIN
source_origin/Channel/month and overall/scenario period.

### TIME BASIS
Generated spend date for cost and first_contact_date for MQLs, both in P.

### FILTER BEHAVIOR
source_origin/Channel mappings must be compatible. Campaign filtering is unavailable.

### ZERO / NULL BEHAVIOR
Zero denominator returns null. Missing/incompatible scenario spend returns null. Complete zero spend with positive MQLs returns 0 and remains labeled synthetic.

### ATTRIBUTION DEPENDENCY
YES.

### KNOWN LIMITATIONS
This is a scenario ratio, not observed historical CPL, and period matching does not establish causality.

## MQL → Acquired Seller Conversion Rate

**Status:** SUPPORTED — REAL-WORLD SOURCE.

### BUSINESS QUESTION
What share of an MQL cohort is linked to a successfully acquired seller?

### DEFINITION
Cohort conversion from MQL to a valid ClosedDeal with seller_id. This metric does not invent an intermediate Opportunity.

### FORMULA
MQLToAcquiredSeller(C, d, S) = COUNT_DISTINCT(seller_id linked to an MQL in C by a valid ClosedDeal with won_date <= S) / COUNT_DISTINCT(mql_id in C)

### NUMERATOR
Distinct AcquiredSeller seller_id values with source-supported lineage to cohort MQLs and won_date no later than reporting cutoff S. The observed 1:1 mql_id-to-seller_id contract prevents double counting and is revalidated on refresh.

### DENOMINATOR
Distinct MQLs whose first_contact_date places them in cohort C.

### GRAIN
Channel/cohort month and overall/cohort period.

### TIME BASIS
first_contact_date defines the cohort; conversion is observed through the stated reporting cutoff.

### FILTER BEHAVIOR
source_origin/Channel filters use the cohort MQL's frozen acquisition mapping. Campaign filtering is unavailable.

### ZERO / NULL BEHAVIOR
Positive valid denominator with no observed conversions by S returns 0 with the cohort's as-of/incomplete status. Zero denominator or incomplete lineage returns null.

### ATTRIBUTION DEPENDENCY
YES for Channel views.

### KNOWN LIMITATIONS
No source-backed conversion-maturity SLA exists. Every result therefore carries an explicit reporting cutoff and follow-up age; incomplete cohorts cannot be described as final or compared as equally mature.

## Seller Acquisition Cost

**Status:** SYNTHETIC SCENARIO.

### BUSINESS QUESTION
Under a controlled spend scenario, how much paid-media cost corresponds to each acquired B2B seller?

### DEFINITION
Compatible synthetic MarketingSpend divided by distinct AcquiredSellers. This is the MVP's seller-specific paid-media acquisition cost; it may be described as B2B CAC in business discussion but is not EndCustomer CAC or fully loaded CAC.

### FORMULA
ScenarioSellerAcquisitionCost(P, d, s) = MarketingSpend(P, d, s) / AcquiredSellers(P, d)

### NUMERATOR
Controlled synthetic advertising spend for Channel d and period P.

### DENOMINATOR
Distinct sellers whose valid ClosedDeal won date is in P and whose Lead origin maps to Channel d.

### GRAIN
source_origin/Channel/month and overall/scenario period.

### TIME BASIS
Generated spend date for cost and seller-acquired date for sellers, both in P.

### FILTER BEHAVIOR
Uses B2B AcquiredSeller only. EndCustomer and Order customer identifiers are prohibited from the denominator.

### ZERO / NULL BEHAVIOR
Zero acquired sellers returns null. Missing/incompatible synthetic spend returns null. Complete zero scenario spend with positive sellers returns 0.

### ATTRIBUTION DEPENDENCY
YES.

### KNOWN LIMITATIONS
Not fully loaded acquisition cost: excludes payroll, sales expense, tools, overhead, and all unobserved real cost. Period matching may not align causal spend and seller cohorts.

## DOWNSTREAM PERFORMANCE KPIs

## Activated Sellers

**Status:** COHORT-MATURE — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How many acquired sellers begin fulfilled marketplace activity within 90 days of acquisition?

### DEFINITION
Distinct AcquiredSellers with at least one Order Item on a delivered Order whose purchase timestamp is strictly after won_date and no later than won_date plus 90 days. Only sellers with 90 complete observation days at cutoff S are evaluable.

### FORMULA
ActivatedSellers(C, d, S) = COUNT_DISTINCT(acquired seller_id with first eligible order_purchase_timestamp in (won_date, won_date + 90 days] and won_date + 90 days <= S)

### NUMERATOR
Distinct mature-cohort sellers meeting the 90-day activation event.

### DENOMINATOR
Not applicable.

### GRAIN
source_origin/Channel/cohort month and overall cohort.

### TIME BASIS
won_date defines cohort and maturity; first eligible order_purchase_timestamp defines activation.

### FILTER BEHAVIOR
Channel comes from the acquired Lead. Order status must be delivered. Campaign and EndCustomer do not participate.

### ZERO / NULL BEHAVIOR
Return 0 for a mature, complete cohort with no activated sellers. Return null/not mature when 90-day follow-up is incomplete.

### ATTRIBUTION DEPENDENCY
YES for source_origin/Channel views.

### KNOWN LIMITATIONS
The source cutoff is inferred from the maximum observed Order purchase timestamp rather than a supplied extraction timestamp. The 462 ClosedDeal sellers absent from the e-commerce seller snapshot may reflect source coverage, so non-activation means no qualifying event observed in the linked snapshots. Refunds or chargebacks after delivery are not observable.

## Orders from Acquired Sellers

**Status:** SUPPORTED — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How many marketplace Orders contain at least one item supplied by an AcquiredSeller?

### DEFINITION
Distinct delivered order_id values linked through OrderItem seller_id to at least one AcquiredSeller, with purchase strictly after that seller's won_date.

### FORMULA
OverallOrders(P) = COUNT_DISTINCT(order_id where order_status = delivered, purchase timestamp is in P, and at least one acquired-seller item is post-win)

SellerChannelOrders(P, d) = COUNT_DISTINCT(seller_id, order_id for delivered post-win seller participation in P and d)

### NUMERATOR
Distinct Orders overall; distinct seller_id/order_id participations for seller or Channel slices.

### DENOMINATOR
Not applicable.

### GRAIN
Channel/day or month and overall/period. Seller-level analysis uses distinct seller_id/order_id participation.

### TIME BASIS
Source Order purchase timestamp.

### FILTER BEHAVIOR
Channel inherits each participating AcquiredSeller's origin. A multi-seller Order can appear in more than one Channel, so Channel totals are non-additive; overall deduplicates order_id.

### ZERO / NULL BEHAVIOR
Return 0 when a complete slice has no qualifying Orders; null when lineage or source coverage is incomplete.

### ATTRIBUTION DEPENDENCY
YES for Channel views.

### KNOWN LIMITATIONS
Multi-seller Orders make seller and Channel slices non-additive. Refund/chargeback events are unavailable.

## GMV (Marketplace Sales Value Proxy)

**Status:** SUPPORTED — REAL-WORLD SOURCE.

### BUSINESS QUESTION
What marketplace item value was generated by AcquiredSellers?

### DEFINITION
Marketplace item-value proxy from OrderItems supplied by AcquiredSellers on delivered, post-win Orders. It is not Olist corporate revenue, net revenue, profit, or cash collected.

### FORMULA
GMV(P, d) = SUM(order_items.price where order_status = delivered, order_purchase_timestamp is in P, order_purchase_timestamp > won_date, and seller source is in d)

### NUMERATOR
Eligible OrderItem price associated through seller_id with AcquiredSellers.

### DENOMINATOR
Not applicable.

### GRAIN
AcquiredSeller/day or month, Channel/day or month, and overall/period.

### TIME BASIS
Source Order purchase timestamp.

### FILTER BEHAVIOR
Channel inherits the supplying seller's acquisition source. Each OrderItem belongs to one seller slice, avoiding whole-Order duplication.

### ZERO / NULL BEHAVIOR
Return 0 for complete coverage with no qualifying item value; null when item value, currency context, or seller lineage is incomplete.

### ATTRIBUTION DEPENDENCY
YES for Channel views.

### KNOWN LIMITATIONS
Freight and payment_value are intentionally excluded. The source has no complete refund/chargeback fact and no row-level currency column; BRL context is an explicit dataset-level assumption.

## Seller Activation Rate

**Status:** COHORT-MATURE — REAL-WORLD SOURCE.

### BUSINESS QUESTION
What share of an acquired-seller cohort begins fulfilled marketplace activity within 90 days?

### DEFINITION
Activated Sellers divided by all AcquiredSellers whose full 90-day window is observable at cutoff S.

### FORMULA
SellerActivationRate(C, d, S) = ActivatedSellers(C, d, S) / COUNT_DISTINCT(acquired seller_id where won_date + 90 days <= S)

### NUMERATOR
Distinct Activated Sellers under the frozen 90-day rule.

### DENOMINATOR
All distinct AcquiredSellers in the same cohort with 90 complete observation days, including mature non-activators.

### GRAIN
source_origin/Channel/cohort month and overall mature cohort.

### TIME BASIS
won_date defines cohort and maturity; first eligible order_purchase_timestamp determines activation.

### FILTER BEHAVIOR
Channel uses seller acquisition origin. Campaign and EndCustomer do not participate.

### ZERO / NULL BEHAVIOR
A positive mature denominator with no activations returns 0. Zero denominator or incomplete 90-day follow-up returns null/not mature.

### ATTRIBUTION DEPENDENCY
YES for source_origin/Channel views.

### KNOWN LIMITATIONS
The static source cutoff is inferred. Later source corrections publish a new lifecycle source/rule/cutoff version; previously published version rows remain reproducible rather than being overwritten.

## Orders per Activated Seller

**Status:** COHORT-MATURE — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How many delivered seller-order participations occur per activated seller during the first 90 days after acquisition?

### DEFINITION
Delivered post-win seller/order participations in days (0, 90] divided by Activated Sellers for the same mature cohort.

### FORMULA
OrdersPerActivatedSeller(C, d, S) = COUNT_DISTINCT(seller_id, order_id in (won_date, won_date + 90 days]) / ActivatedSellers(C, d, S)

### NUMERATOR
Distinct delivered seller_id/order_id participations for cohort sellers during their 90-day windows.

### DENOMINATOR
Distinct Activated Sellers in the same mature cohort.

### GRAIN
source_origin/Channel/cohort month and overall mature cohort.

### TIME BASIS
won_date defines cohort/window; order_purchase_timestamp defines included activity.

### FILTER BEHAVIOR
Uses delivered Orders and seller acquisition source. Campaign and EndCustomer filters are unavailable.

### ZERO / NULL BEHAVIOR
Zero Activated Sellers returns null. A positive denominator with no additional qualifying activity cannot occur because the activation event itself is a qualifying seller/order pair.

### ATTRIBUTION DEPENDENCY
YES for source_origin/Channel views.

### KNOWN LIMITATIONS
This is seller-order participation, not an additive count of unique marketplace Orders across Channel slices.

## GMV per Activated Seller

**Status:** COHORT-MATURE — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How much marketplace item value is generated per activated seller during the first 90 days after acquisition?

### DEFINITION
Official GMV generated in days (0, 90] divided by Activated Sellers for the same mature cohort.

### FORMULA
GMVPerActivatedSeller(C, d, S) = SUM(eligible order_items.price in (won_date, won_date + 90 days]) / ActivatedSellers(C, d, S)

### NUMERATOR
Order Item price from delivered, post-win Orders during each mature cohort seller's 90-day window.

### DENOMINATOR
Distinct Activated Sellers in the same mature cohort.

### GRAIN
source_origin/Channel/cohort month and overall mature cohort.

### TIME BASIS
won_date defines cohort/window; order_purchase_timestamp defines included GMV.

### FILTER BEHAVIOR
Uses the frozen GMV, eligibility, and acquisition-source rules. Campaign and EndCustomer filters are unavailable.

### ZERO / NULL BEHAVIOR
Zero Activated Sellers returns null. Positive denominator with zero GMV returns 0 only if source completeness is valid.

### ATTRIBUTION DEPENDENCY
YES for source_origin/Channel views.

### KNOWN LIMITATIONS
Inherits GMV's exclusion of freight, Payments, and unobserved refunds.

## Time to First Order

**Status:** COHORT-MATURE — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How quickly do acquired sellers first generate delivered marketplace activity?

### DEFINITION
Elapsed fractional days from won_date to the first delivered Order purchase timestamp for Activated Sellers within 90 days.

### FORMULA
TimeToFirstOrder(seller_id) = MIN(eligible order_purchase_timestamp) - won_date, constrained to (0, 90 days]

### NUMERATOR
Not applicable; this is a duration distribution.

### DENOMINATOR
Not applicable. The reported population is Activated Sellers in mature cohorts.

### GRAIN
AcquiredSeller detail; summarized by source_origin/Channel and ClosedDeal cohort month.

### TIME BASIS
won_date and first eligible order_purchase_timestamp.

### FILTER BEHAVIOR
Only delivered post-win activity participates. Campaign and EndCustomer do not participate.

### ZERO / NULL BEHAVIOR
Non-activated or immature sellers have null duration and are excluded from percentiles, while remaining visible in activation denominators. Zero/negative duration is invalid.

### ATTRIBUTION DEPENDENCY
YES for source_origin/Channel summaries.

### KNOWN LIMITATIONS
Report count, minimum, P25, median, P75, P90, P95, and maximum; do not impute non-activators or infer causality.

## GMV ROAS

**Status:** SYNTHETIC SCENARIO.

### BUSINESS QUESTION
Under a controlled spend scenario, how much attributed downstream marketplace value corresponds to each generated spend unit?

### DEFINITION
Attributed downstream GMV proxy divided by compatible synthetic MarketingSpend. The name must remain GMV ROAS to prevent interpretation as Olist revenue return or accounting return.

### FORMULA
ScenarioGMVROAS(P, d, s) = GMV(P, d) / MarketingSpend(P, d, s)

### NUMERATOR
Eligible OrderItem price in P supplied by AcquiredSellers whose Lead origin maps to Channel d.

### DENOMINATOR
Compatible controlled synthetic MarketingSpend for Channel d, P, and scenario s.

### GRAIN
source_origin/Channel/month and overall/scenario period.

### TIME BASIS
Order purchase timestamp for GMV and generated spend date for cost, both in P.

### FILTER BEHAVIOR
Requires compatible source_origin/Channel mapping and an explicit synthetic scenario. Campaign filtering is unavailable.

### ZERO / NULL BEHAVIOR
Positive complete spend with zero GMV returns 0. Zero/missing/incompatible spend or incomplete GMV returns null.

### ATTRIBUTION DEPENDENCY
YES.

### KNOWN LIMITATIONS
Not causal ROAS, corporate revenue return, or profit. It combines real downstream marketplace item value with generated cost and must retain synthetic-scenario labeling.

## NOT ACTIVE / REMOVED FROM MVP CONTRACT

### Opportunities

No active count or conversion KPI: the selected public funnel source does not provide a defensible independent Opportunity identifier and lifecycle. ClosedDeal is not used as a synonym for Opportunity.

### End Customers acquired

No marketing-acquisition KPI: e-commerce EndCustomers are buyers and are not the B2B sellers acquired by the Marketing Funnel.

### Revenue

Renamed to GMV (Marketplace Sales Value Proxy). Full order value is not claimed as Olist corporate or recognized revenue.

### Generic CAC

Replaced by Seller Acquisition Cost to make the B2B acquired entity explicit. It uses synthetic spend and is not EndCustomer CAC or fully loaded CAC.

### Generic ROAS

Replaced by GMV ROAS with synthetic-scenario and marketplace-value qualifiers.

### Simplified Marketing ROI

Not publishable for the MVP. Calculating (GMV - MarketingSpend) / MarketingSpend would misrepresent GMV as revenue or profit. A defensible future formula would require an observed revenue or contribution-margin measure and real or explicitly scenario-based cost; until then this KPI remains an OPEN DECISION.

## ANALYTICAL DIMENSIONS

### MVP dimensions

- **Period/date:** required, governed by each KPI's declared timestamp and one reporting timezone.
- **source_origin:** retained source-native Marketing Funnel origin.
- **Channel:** minimal deterministic acquisition dimension mapped from source_origin.
- **AcquiredSeller:** lineage and drilldown dimension for downstream performance.
- **landing_page_id:** source-native acquisition context; explicitly not Campaign.
- **Synthetic scenario:** mandatory for every spend-dependent KPI.

### Unavailable MVP dimension

- **Campaign:** absent from Olist outcomes and from the synthetic spend MVP contract. Campaign-level ratios remain unavailable rather than fabricate linkage.

EndCustomer, geography, product category, payment method, and other e-commerce dimensions are deferred to avoid scope creep. Order status is a fixed eligibility rule, not a marketing-acquisition dimension.

## OPEN DECISIONS

- Decide whether Opportunity can be observed or defensibly derived.
- Select the reporting timezone and late-arriving/correction behavior.
- Define refund/chargeback treatment if a future source exposes those events.
- Establish a source-backed snapshot timestamp and conversion-maturity SLA for future refreshes.
- Revisit Campaign only if a source-backed, governed identifier becomes available.
- Determine whether any real revenue or contribution-margin source can support a future ROI metric.
