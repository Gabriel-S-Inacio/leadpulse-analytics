# Domain Model

## Purpose and scope

This document defines the MVP business language aligned with the selected public Olist datasets and a future controlled synthetic advertising-spend source. It is conceptual, not a physical database model: it does not prescribe tables, database types, physical keys, indexes, or schemas.

The model contains two related but distinct domains:

- **B2B seller acquisition:** Channel, Campaign, Lead, Opportunity, ClosedDeal, AcquiredSeller, and MarketingSpend.
- **E-commerce transactions:** Order and EndCustomer, with order items and payments as supporting source concepts.

## Source classification

### REAL-WORLD SOURCE

- **Olist Marketing Funnel:** public source with approximately 8,000 Marketing Qualified Leads (MQLs), their first known acquisition origin and landing page, and successful closed-deal links to sellers.
- **Olist Brazilian E-Commerce:** public source for sellers, orders, order items, payments, and end customers.

### CONTROLLED SYNTHETIC SOURCE

- **Advertising Spend:** a future generated source used to exercise cost metrics when no equivalent real spend is available.

Synthetic records must carry explicit provenance and must never be labeled, presented, or implied to be observed Olist data. Mixed real/synthetic metrics must be labeled as scenario or portfolio-analysis results.

## Core entities

### Channel

**Definition:** governed analytical grouping of acquisition origin, such as a normalized category derived from the Marketing Funnel origin.

**Domain purpose:** support comparable seller-acquisition and downstream-performance analysis across raw origin values.

**Conceptual identifier:** stable analytical channel code from a versioned normalization taxonomy.

**Essential attributes:** canonical name, retained raw origin, normalization rule/version, classification status, and active period.

**Relationships:** may group zero or more Campaigns; classifies Leads; directly classifies synthetic MarketingSpend when its methodology supplies a compatible origin.

**Relevant lifecycle events:** classification introduced, mapping revised, renamed, or retired.

**Ambiguities / decisions pending:** exact origin normalization and effective-dated behavior when mappings change.

### Campaign

**Definition:** governed marketing initiative with an explicit identity. It is not a synonym for Channel, origin, or landing page.

**Domain purpose:** provide campaign-level cost and outcome analysis only where a source supplies Campaign identity or an approved derivation exists.

**Conceptual identifier:** source-qualified campaign identifier from the future synthetic spend source or another explicitly governed source.

**Essential attributes:** campaign name, source provenance, Channel, lifecycle dates/status, and mapping confidence.

**Relationships:** belongs to one Channel for a governed effective period; may have MarketingSpend; may receive attributed Leads only through a defensible mapping.

**Relevant lifecycle events:** created, activated, paused, ended, remapped, or retired.

**Ambiguities / decisions pending:** the Olist Marketing Funnel does not provide a complete advertising-platform campaign identifier taxonomy. landing_page_id must be retained as its own source attribute and must not be relabeled as Campaign without an approved derived mapping.

### Lead (Marketing Qualified Lead)

**Definition:** one MQL represented in the Olist Marketing Funnel population. The public source begins at this qualified-lead stage and does not represent every anonymous visitor or every pre-qualification lead.

**Domain purpose:** anchor measurable B2B seller acquisition and the first known acquisition source.

**Conceptual identifier:** source mql_id.

**Essential attributes:** mql_id, first_contact_date, origin, landing_page_id, normalized Channel, optional derived Campaign, and attribution/provenance status.

**Relationships:** may have one successful ClosedDeal link in the public funnel data, subject to source uniqueness validation; may be associated conceptually with a sales Opportunity even though that stage is not independently observable.

**Relevant lifecycle events:** first known contact/MQL entry and successful close when a matching ClosedDeal exists. Intermediate sales-stage events are not invented.

**Ambiguities / decisions pending:** source uniqueness, missing origin/landing page treatment, and whether any defensible Opportunity proxy can be derived later.

### Opportunity

**Definition:** conceptual B2B sales process between an MQL and a successful close.

**Domain purpose:** preserve correct domain language for the commercial process without claiming an independently measurable source entity.

**Conceptual identifier:** unavailable as a reliable independent identifier in the selected public Marketing Funnel data.

**Essential attributes:** conceptually, an identifier, opening timestamp, stage history, and outcome would be needed; these are not assumed to exist for the MVP.

**Relationships:** would originate from a Lead and may result in a ClosedDeal if a future source provides defensible lineage.

**Relevant lifecycle events:** conceptually opened, progressed, won, or lost; these events are not reconstructed from absent public fields.

**Ambiguities / decisions pending:** whether Opportunity is observable or derivable without equating MQL presence or ClosedDeal with an intermediate stage. Until resolved, Opportunity KPIs are not active.

### ClosedDeal

**Definition:** successful B2B commercial close through which an MQL becomes linked to a seller operating on Olist.

**Domain purpose:** represent marketing conversion/seller acquisition, not an e-commerce purchase.

**Conceptual identifier:** source-qualified closed-deal row identity; mql_id is the known Lead link and seller_id is the known acquired-seller link. Their cardinality and uniqueness must be validated rather than assumed.

**Essential attributes:** mql_id, seller_id, close/won date when supplied, retained source attributes, and lineage status.

**Relationships:** links one source Lead to an AcquiredSeller when source lineage is valid; is upstream of later Order activity through seller_id.

**Relevant lifecycle events:** successful close recorded and later source correction, if any. Lost or intermediate states are not inferred from absence of a ClosedDeal row.

**Ambiguities / decisions pending:** duplicate-row handling, source uniqueness, and any correction/cancellation semantics available in the source.

### AcquiredSeller

**Definition:** marketplace seller acquired through a valid Olist Marketing Funnel ClosedDeal. It is the B2B acquired party, not the e-commerce buyer.

**Domain purpose:** bridge seller acquisition to downstream marketplace activity and ensure marketing conversion is not confused with end-customer acquisition.

**Conceptual identifier:** source seller_id.

**Essential attributes:** seller_id, linked mql_id, seller-acquired date from the valid ClosedDeal, acquisition Channel, optional Campaign, and lineage confidence.

**Relationships:** results from a ClosedDeal; supplies zero or more order items; can participate in zero or more Orders; inherits acquisition source from its Lead.

**Relevant lifecycle events:** acquired through successful close and first observed eligible order-item participation. Later seller operating states are not invented without source support.

**Ambiguities / decisions pending:** duplicate seller_id links, seller activation definition/window, and treatment of sellers already present before funnel acquisition.

### MarketingSpend

**Definition:** controlled synthetic advertising-cost observation for a known time period and analytical origin.

**Domain purpose:** enable clearly labeled scenario calculations for CPL, Seller Acquisition Cost, and GMV ROAS where the public sources have no real advertising-spend fact.

**Conceptual identifier:** deterministic synthetic observation identity at the generated grain.

**Essential attributes:** spend date/period, amount, currency, Channel, optional Campaign, generation-method version, scenario identifier, and CONTROLLED_SYNTHETIC provenance.

**Relationships:** maps directly to a Channel and optionally Campaign; is compared with real MQL, AcquiredSeller, and downstream GMV outcomes only when the generation/mapping methodology makes the slice compatible.

**Relevant lifecycle events:** generated, validated, versioned, superseded, or withdrawn.

**Ambiguities / decisions pending:** generation methodology, realistic constraints, campaign taxonomy, currency, time grain, and rules preventing synthetic values from being presented as observed facts.

### Order

**Definition:** e-commerce transaction placed on the marketplace by an EndCustomer. An Order may contain items supplied by more than one seller.

**Domain purpose:** measure downstream commercial activity after seller acquisition.

**Conceptual identifier:** source order_id.

**Essential attributes:** order identifier, purchase timestamp, status, EndCustomer reference, and order-item relationships.

**Relationships:** belongs to an EndCustomer; contains one or more order items; each order item references a seller through seller_id; may have one or more payment records.

**Relevant lifecycle events:** placed, approved, delivered, cancelled, or otherwise transitioned according to source status.

**Ambiguities / decisions pending:** eligible order statuses, cancellation/refund handling, and non-additivity when one Order contains items from multiple sellers.

### EndCustomer

**Definition:** final buyer represented in the Olist e-commerce data. This entity is deliberately named EndCustomer in internal LeadPulse contracts to avoid confusion with the B2B AcquiredSeller.

**Domain purpose:** provide buyer context for marketplace Orders, not measure seller acquisition.

**Conceptual identifier:** governed buyer identity derived from the source customer identifiers; the choice between order-scoped and cross-order identity must follow source semantics.

**Essential attributes:** source customer references and available location/context attributes, subject to privacy-safe use.

**Relationships:** places Orders; has no implied identity or equivalence with Lead, ClosedDeal, or AcquiredSeller.

**Relevant lifecycle events:** first and subsequent observed Orders. Acquisition by Olist marketing is not inferred.

**Ambiguities / decisions pending:** which source customer identifier supports cross-order identity and what EndCustomer analysis is necessary for the MVP.

## Supporting source concepts

- **OrderItem:** joins an Order to a seller via order_id and seller_id and supplies item-level marketplace sales value. It is the operative bridge for downstream seller performance.
- **Payment:** records how an Order was paid and may have multiple rows per Order. It must not be summed as GMV without a separate, validated payment metric.
- **LandingPage:** retained through landing_page_id as acquisition context. It is not automatically a Campaign.

These concepts are included for semantic lineage and do not prescribe additional physical models.

## Data lineage concept

~~~text
Olist Marketing Funnel
        |
        | mql_id -> ClosedDeal -> seller_id
        v
AcquiredSeller
        |
        | seller_id
        v
Olist Order Items
        |
        | order_id
        v
Olist Orders
~~~

seller_id is the primary known bridge between the public Marketing Funnel and E-Commerce datasets. At transaction level, the bridge is realized through order items, because Orders themselves may include multiple sellers. No physical join implementation is defined here.

## Corrected conceptual funnel

~~~text
Marketing Source (first known origin / landing page)
                         |
                    MQL / Lead
                         |
          Sales Process / Opportunity
              (not independently observed)
                         |
                    ClosedDeal
                         |
                  AcquiredSeller
                         |
           Order Items / Orders
                         |
        GMV / downstream performance
~~~

- **Marketing conversion** is the transition from MQL/Lead to a valid ClosedDeal and AcquiredSeller.
- **Downstream seller performance** is the later Order/GMV activity associated through seller_id.
- A seller can be acquired and still have no eligible Order. Acquisition and activation are therefore different events.
- Anonymous Visitor/Interaction history is not part of the selected public-source contract.

## Entity distinctions

- Lead, conceptual Opportunity, ClosedDeal, and AcquiredSeller belong to the **B2B seller-acquisition funnel**.
- Order and EndCustomer belong to the **B2C marketplace transaction domain**.
- ClosedDeal is the commercial close that onboards/acquires a seller; Order is a later marketplace transaction.
- AcquiredSeller is the seller acquired by the B2B funnel; EndCustomer is the buyer placing an Order.
- EndCustomer counts must never be used as seller-acquisition counts or as the denominator of Seller Acquisition Cost.
- Order value/GMV is downstream marketplace activity and is not Olist corporate revenue.

## Domain invariants

1. mql_id identifies the public MQL/Lead; seller_id identifies the seller bridge; order_id identifies an e-commerce Order. These identifiers are not interchangeable.
2. A valid ClosedDeal links a Lead to an AcquiredSeller through source-supported lineage.
3. ClosedDeal and Order are never synonyms: the former is B2B seller acquisition, the latter is downstream e-commerce activity.
4. AcquiredSeller and EndCustomer are never synonyms and do not share an acquisition KPI.
5. A Campaign is not manufactured from origin or landing_page_id. Any mapping from landing page to Campaign is explicitly derived and governed.
6. Channel may be normalized from retained raw origin; unmapped/missing origin remains visible as Unattributed.
7. Opportunity is not counted unless a defensible independent record or derivation is approved.
8. Seller downstream activity is linked through seller_id at OrderItem grain; multi-seller Orders require explicit non-additivity handling.
9. MVP GMV is a marketplace sales-value proxy from eligible order items, not Olist corporate or accounting revenue.
10. Synthetic MarketingSpend is always distinguishable from real-world Olist records in storage, calculations, and presentation.
11. Missing, inapplicable, or incomplete data is not equivalent to zero.
12. Monetary aggregation requires a common currency and an approved inclusion rule.

## OPEN DECISIONS

- Approve the Channel taxonomy and versioned mapping from Marketing Funnel origin.
- Decide whether any landing_page_id to Campaign mapping is defensible; otherwise keep Campaign null for Olist outcomes.
- Define and validate the controlled synthetic spend-generation methodology and disclosure.
- Determine whether Opportunity is observable or can be derived without inventing lifecycle states.
- Define eligible Order statuses and cancellation/refund treatment.
- Define GMV inclusions, including item price, freight, discounts, and adjustments.
- Define seller activation event and observation window.
- Confirm source identifier uniqueness/cardinality and treatment of duplicate funnel links.
- Set reporting timezone and late-arriving/correction policy.
- Decide whether EndCustomer analysis is needed beyond Order context.
