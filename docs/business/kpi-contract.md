# KPI Contract

## Contract scope and status

This contract separates B2B seller acquisition from downstream e-commerce performance and distinguishes real Olist observations from controlled synthetic spend.

- **SUPPORTED:** source concepts exist; publication still depends on basic data-quality checks.
- **SYNTHETIC SCENARIO:** combines real Olist outcomes with controlled synthetic Advertising Spend and must be labeled accordingly.
- **PROVISIONAL:** the source supports the concept, but a material business rule remains open; do not publish as final until approved.
- **NOT ACTIVE:** insufficient source observability or misleading semantics prevent an MVP KPI.

## Common conventions

- P is a half-open reporting interval: start inclusive and end exclusive.
- C is an AcquiredSeller cohort defined by seller-acquired date.
- W is an explicitly reported downstream observation window after acquisition.
- Counts use distinct source-supported conceptual identifiers, never raw row counts.
- First Known Acquisition Source follows the attribution contract: Channel is normalized from Lead origin; Campaign is null unless a governed derivation exists.
- Synthetic MarketingSpend is never presented as observed Olist spend.
- A complete slice with no qualifying records returns 0. Missing, inapplicable, or incomplete coverage returns null with a quality status.
- Division by zero returns null, never infinity.
- Monetary aggregation requires a common currency and an approved inclusion rule.
- Period filters follow each KPI's declared timestamp. Channel filters use normalized Lead origin for outcomes and compatible generated Channel for spend.
- Campaign outcome filters are not supported by default for Olist. landing_page_id is not treated as Campaign.

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
Channel/day or month and overall/period. landing_page_id may be a source-context drilldown. Campaign grain is unavailable by default.

### TIME BASIS
first_contact_date.

### FILTER BEHAVIOR
Period filters first_contact_date. Channel uses normalized origin. Campaign returns no Olist-attributed result unless a governed mapping is later approved.

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
Channel/day or month and overall/period; no default Campaign grain.

### TIME BASIS
Source won/close date.

### FILTER BEHAVIOR
Period filters won date. Channel inherits normalized origin through mql_id. Campaign remains unsupported without a governed mapping.

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
Channel/day or month and overall/period; no default Campaign grain.

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
Channel/day or month; Campaign/day only within the synthetic source; overall/scenario period.

### TIME BASIS
Generated spend date or allocated interval.

### FILTER BEHAVIOR
Every result requires scenario and CONTROLLED_SYNTHETIC provenance. Channel must use the governed origin taxonomy. Synthetic Campaign does not create Campaign identity for Olist outcomes.

### ZERO / NULL BEHAVIOR
Return 0 only when an applicable, complete scenario intentionally generates no spend; null when no compatible scenario exists.

### ATTRIBUTION DEPENDENCY
NO; origin is directly assigned by the generation methodology.

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
Channel/month and overall/scenario period. Campaign-level CPL is not supported by default.

### TIME BASIS
Generated spend date for cost and first_contact_date for MQLs, both in P.

### FILTER BEHAVIOR
Channel mappings must be compatible. landing_page_id is not substituted for Campaign.

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
MQLToAcquiredSeller(C, d) = COUNT_DISTINCT(mql_id in cohort C with valid ClosedDeal and seller_id) / COUNT_DISTINCT(mql_id in cohort C)

### NUMERATOR
Distinct cohort MQLs with source-supported valid ClosedDeal and AcquiredSeller lineage, observed by the reporting cutoff.

### DENOMINATOR
Distinct MQLs whose first_contact_date places them in cohort C.

### GRAIN
Channel/cohort month and overall/cohort period.

### TIME BASIS
first_contact_date defines the cohort; conversion is observed through the stated reporting cutoff.

### FILTER BEHAVIOR
Channel filters normalized cohort-MQL origin. Campaign remains unavailable without approved derivation.

### ZERO / NULL BEHAVIOR
Positive complete denominator with no conversions returns 0. Zero denominator or incomplete lineage returns null.

### ATTRIBUTION DEPENDENCY
YES for Channel views.

### KNOWN LIMITATIONS
Recent cohorts are right-censored, and no maturity window has been approved.

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
Channel/month and overall/scenario period. Campaign-level calculation is not supported by default.

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

## Orders from Acquired Sellers

**Status:** PROVISIONAL — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How many marketplace Orders contain at least one item supplied by an AcquiredSeller?

### DEFINITION
Distinct eligible order_id values linked through OrderItem seller_id to at least one AcquiredSeller.

### FORMULA
Orders(P, d) = COUNT_DISTINCT(order_id where purchase timestamp is in P, status is eligible, and at least one acquired seller source is in d)

### NUMERATOR
Distinct eligible Orders with acquired-seller participation.

### DENOMINATOR
Not applicable.

### GRAIN
Channel/day or month and overall/period. Seller-level analysis uses distinct seller_id/order_id participation.

### TIME BASIS
Source Order purchase timestamp.

### FILTER BEHAVIOR
Channel inherits each participating AcquiredSeller's origin. A multi-seller Order can appear in more than one Channel, so Channel totals are non-additive; overall deduplicates order_id.

### ZERO / NULL BEHAVIOR
Return 0 when complete and no eligible Orders exist; null while eligible-status or lineage coverage is unresolved.

### ATTRIBUTION DEPENDENCY
YES for Channel views.

### KNOWN LIMITATIONS
Eligible Order statuses remain open, and multi-seller Orders complicate additive attribution.

## GMV (Marketplace Sales Value Proxy)

**Status:** PROVISIONAL — REAL-WORLD SOURCE.

### BUSINESS QUESTION
What marketplace item value was generated by AcquiredSellers?

### DEFINITION
Gross marketplace sales-value proxy from eligible OrderItems supplied by AcquiredSellers. It is not Olist corporate revenue, net revenue, profit, or cash collected.

### FORMULA
ProvisionalGMV(P, d) = SUM(order_item_price where Order purchase timestamp is in P, Order is eligible, and seller source is in d)

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
Return 0 for complete eligible coverage with no item value; null when order eligibility, item value, currency, or seller lineage is incomplete.

### ATTRIBUTION DEPENDENCY
YES for Channel views.

### KNOWN LIMITATIONS
The preliminary formula uses item price and excludes freight. Status, cancellation, refund, discount, freight, and adjustment rules require approval.

## Orders per Acquired Seller

**Status:** PROVISIONAL — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How many seller-order participations does an acquired-seller cohort generate during a defined observation window?

### DEFINITION
Distinct seller_id/order_id pairs generated by cohort C within W, divided by all AcquiredSellers in C, including sellers with zero Orders.

### FORMULA
OrdersPerAcquiredSeller(C, W, d) = COUNT_DISTINCT(seller_id, order_id in W for C and d) / COUNT_DISTINCT(acquired seller_id in C and d)

### NUMERATOR
Distinct eligible seller-order participations in W after seller acquisition.

### DENOMINATOR
All distinct AcquiredSellers in cohort C, not only activated sellers.

### GRAIN
Channel/cohort month/observation window and overall cohort/window.

### TIME BASIS
ClosedDeal won date defines cohort; Order purchase timestamp defines inclusion in W.

### FILTER BEHAVIOR
Channel uses seller acquisition origin. Campaign remains unsupported by default.

### ZERO / NULL BEHAVIOR
Positive complete denominator with no Orders returns 0. Zero denominator or undefined/incomplete W returns null.

### ATTRIBUTION DEPENDENCY
YES.

### KNOWN LIMITATIONS
Cannot be finalized until W and eligible Order statuses are approved; shorter source coverage right-censors recent cohorts.

## GMV per Acquired Seller

**Status:** PROVISIONAL — REAL-WORLD SOURCE.

### BUSINESS QUESTION
How much downstream GMV does an acquired-seller cohort generate per acquired seller during W?

### DEFINITION
Eligible GMV from cohort C during W divided by all AcquiredSellers in C, including zero-GMV sellers.

### FORMULA
GMVPerAcquiredSeller(C, W, d) = ProvisionalGMV(C, W, d) / COUNT_DISTINCT(acquired seller_id in C and d)

### NUMERATOR
Eligible OrderItem price for cohort sellers during W.

### DENOMINATOR
All distinct AcquiredSellers in cohort C.

### GRAIN
Channel/cohort month/observation window and overall cohort/window.

### TIME BASIS
ClosedDeal won date defines cohort; Order purchase timestamp defines inclusion in W.

### FILTER BEHAVIOR
Channel uses seller acquisition origin. Campaign remains unsupported by default.

### ZERO / NULL BEHAVIOR
Positive complete denominator with zero GMV returns 0. Zero denominator, undefined W, or incomplete GMV returns null.

### ATTRIBUTION DEPENDENCY
YES.

### KNOWN LIMITATIONS
Inherits provisional GMV semantics and cohort-window right-censoring.

## Acquired Seller Activation Rate

**Status:** PROVISIONAL / NOT PUBLISHABLE until activation rules are approved.

### BUSINESS QUESTION
What share of an acquired-seller cohort records meaningful marketplace activity within W?

### DEFINITION
Proposed activation is at least one eligible OrderItem participation within W after the seller's ClosedDeal won date. This definition is not final.

### FORMULA
SellerActivationRate(C, W, d) = COUNT_DISTINCT(acquired seller_id with at least one eligible OrderItem in W) / COUNT_DISTINCT(acquired seller_id in C)

### NUMERATOR
Distinct cohort sellers meeting the approved activation event within W.

### DENOMINATOR
All distinct AcquiredSellers in cohort C.

### GRAIN
Channel/cohort month/observation window and overall cohort/window.

### TIME BASIS
ClosedDeal won date defines cohort; first eligible Order purchase timestamp determines activation within W.

### FILTER BEHAVIOR
Channel uses seller acquisition origin; EndCustomer does not participate.

### ZERO / NULL BEHAVIOR
Positive complete denominator with no activated sellers returns 0. Until event eligibility and W are approved, the KPI is null/not published.

### ATTRIBUTION DEPENDENCY
YES.

### KNOWN LIMITATIONS
Activation may require a stronger event than first OrderItem, and available e-commerce coverage can censor both early and late cohorts.

## GMV ROAS

**Status:** SYNTHETIC SCENARIO and PROVISIONAL.

### BUSINESS QUESTION
Under a controlled spend scenario, how much attributed downstream marketplace value corresponds to each generated spend unit?

### DEFINITION
Attributed downstream GMV proxy divided by compatible synthetic MarketingSpend. The name must remain GMV ROAS to prevent interpretation as Olist revenue return or accounting return.

### FORMULA
ScenarioGMVROAS(P, d, s) = AttributedProvisionalGMV(P, d) / MarketingSpend(P, d, s)

### NUMERATOR
Eligible OrderItem price in P supplied by AcquiredSellers whose Lead origin maps to Channel d.

### DENOMINATOR
Compatible controlled synthetic MarketingSpend for Channel d, P, and scenario s.

### GRAIN
Channel/month and overall/scenario period. Campaign-level GMV ROAS is unsupported by default.

### TIME BASIS
Order purchase timestamp for GMV and generated spend date for cost, both in P.

### FILTER BEHAVIOR
Requires compatible Channel taxonomy and explicit synthetic scenario. Campaign cannot be joined through landing_page_id without approved derivation.

### ZERO / NULL BEHAVIOR
Positive complete spend with zero GMV returns 0. Zero/missing/incompatible spend or incomplete GMV returns null.

### ATTRIBUTION DEPENDENCY
YES.

### KNOWN LIMITATIONS
Not causal ROAS, corporate revenue return, or profit. It combines real downstream marketplace value with generated cost and inherits provisional GMV rules.

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
- **Channel:** initial supported acquisition dimension, normalized from retained Marketing Funnel origin.
- **AcquiredSeller:** lineage and drilldown dimension for downstream performance.
- **landing_page_id:** source-native acquisition context; explicitly not Campaign.
- **Synthetic scenario:** mandatory for every spend-dependent KPI.

### Conditional dimension

- **Campaign:** supported inside synthetic spend, but not supported for Olist outcome attribution until an approved mapping exists. Campaign-level ratios must remain unavailable rather than fabricate linkage.

EndCustomer, geography, product category, payment method, and other e-commerce dimensions are deferred to avoid scope creep. Order status is an eligibility rule, not a marketing-acquisition dimension.

## OPEN DECISIONS

- Approve origin-to-Channel taxonomy and campaign-mapping policy.
- Define and validate synthetic Advertising Spend generation, currency, grain, and disclosures.
- Decide whether Opportunity can be observed or defensibly derived.
- Approve eligible Order statuses and cancellation/refund treatment.
- Approve final GMV calculation, including item price, freight, discounts, and adjustments.
- Define seller activation event and observation window W.
- Define a maturity/as-of policy for MQL conversion cohorts.
- Set reporting timezone and late-arriving/correction behavior.
- Determine whether any real revenue or contribution-margin source can support a future ROI metric.
