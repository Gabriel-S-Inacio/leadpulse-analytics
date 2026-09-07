# Attribution Model

## Purpose and source boundary

Attribution assigns an acquisition origin to the B2B seller funnel and propagates it to downstream seller activity. The public Olist Marketing Funnel provides the first known origin recorded for an MQL, not a complete sequence of pre-lead marketing touches.

The operational MVP model must therefore describe observable source association, not claim causal credit or a customer journey that the source cannot reproduce.

## Strategies considered

### First-touch attribution

Conceptually assigns all credit to the earliest eligible marketing touch.

- **Strengths:** simple, explainable, and acquisition-oriented.
- **Limitation for this source:** a true earliest touch cannot be proven because the public data does not provide complete timestamped interaction history before the MQL.

### Last-touch attribution

Conceptually assigns all credit to the latest eligible touch before conversion.

- **Strengths:** can emphasize conversion-closing activity when ordered touch history exists.
- **Limitation for this source:** the required touch sequence is absent, so selecting a last touch would be fabricated.

### Multi-touch attribution

Conceptually distributes credit across multiple interactions.

- **Strengths:** can represent longer journeys when identity and event coverage are reliable.
- **Limitation for this source:** there is no complete multi-touch history, identity stitching, or defensible weighting evidence. It is not suitable for the MVP.

## Operational MVP decision: First Known Acquisition Source

The MVP uses **First Known Acquisition Source**, based on the acquisition information available on the Olist MQL record:

- raw source: origin;
- first known acquisition date: first_contact_date;
- acquisition context: landing_page_id;
- normalized reporting dimension: Channel derived from origin through a governed mapping;
- Campaign: null unless an explicit, versioned derivation is later approved.

This model is conceptually close to first touch, but it is intentionally named differently because the source proves only the first origin known to the dataset, not the prospect's true first interaction.

## Attribution unit and propagation

1. Each Lead/MQL receives one normalized Channel from its retained origin value or the reserved Unattributed classification.
2. The Olist Lead receives no Campaign by default; landing_page_id remains acquisition context, not a campaign identifier.
3. A valid ClosedDeal and its AcquiredSeller inherit the Lead's First Known Acquisition Source through mql_id and seller_id lineage.
4. Order items supplied by that AcquiredSeller and related downstream GMV inherit the seller's acquisition source for analytical grouping.
5. The attribution is a downstream association with acquired-seller origin. It does not prove that marketing caused an individual Order.

## Attribution window

No lookback window is applied in the operational MVP. The public source provides first_contact_date and a source snapshot but not the earlier touch events required to evaluate a 90-day or any other pre-lead window.

The previous 90-day rule is removed from the operational contract. A future lookback window may be evaluated only if a new source supplies sufficiently complete, timestamped interaction history; it remains an OPEN DECISION rather than an existing capability.

## Channel normalization

- Retain raw origin exactly as supplied.
- Map origin to Channel through a documented, versioned taxonomy.
- Preserve mapping status and version so historical changes are auditable.
- Map missing or unrecognized origin to Unattributed; never silently drop the Lead.
- Use Organic or Direct only when an approved mapping from an observed origin supports that classification. Missing evidence is Unattributed, not Direct.

## Campaign limitation

The Olist Marketing Funnel does not provide a complete campaign identifier equivalent to an advertising-platform campaign taxonomy.

- Do not create or infer campaign_id from mql_id, origin, or landing_page_id.
- landing_page_id remains a source attribute.
- A future mapping from landing_page_id to Campaign is a derived business rule and requires documented evidence, ownership, versioning, and coverage.
- Campaign can exist fully in the controlled synthetic Advertising Spend source.
- Campaign-level CPL, Seller Acquisition Cost, GMV ROAS, or conversion reporting is unavailable for Olist outcomes until a compatible mapping is approved.
- Channel-level analysis is the initial supported acquisition view because Channel can be normalized from origin.

## Unattributed Leads

An MQL with missing or unmapped origin uses Channel = Unattributed and Campaign = null.

Unattributed Leads, ClosedDeals, AcquiredSellers, Orders, and GMV remain in overall totals and appear in a separate attribution bucket. They are not silently excluded, assigned to Direct, or allocated proportionally to known channels.

## Later source changes

The public source does not provide a complete history of changes to MQL origin. The observed origin is treated as the First Known Acquisition Source snapshot.

A corrected source record or taxonomy mapping may restate normalized Channel through the controlled reassignment process. A later seller Order, different landing page, or downstream EndCustomer activity never changes seller acquisition attribution.

## Multiple Orders for one AcquiredSeller

An AcquiredSeller is counted once for acquisition. All eligible order items and Orders associated with that seller through seller_id can be grouped under the seller's acquisition Channel.

This propagation measures downstream performance associated with the acquired seller. It is not repeat acquisition, EndCustomer acquisition, or causal advertising return. Multi-seller Orders may appear in more than one Channel slice and must be treated as non-additive across those slices.

## Synthetic MarketingSpend alignment

Advertising Spend is a controlled synthetic source, not an observed Olist fact.

- It must be labeled CONTROLLED_SYNTHETIC and carry scenario/methodology version.
- Channel values must use the same governed taxonomy as normalized Olist origin before channel-level ratios are computed.
- Campaign-level spend may exist synthetically, but campaign-level outcome ratios remain unsupported unless a defensible Olist outcome mapping exists.
- Results combining synthetic spend with real outcomes must be labeled scenario metrics, never historical Olist advertising performance.

## Historical reassignment

Historical attribution is not changed silently. A correction must:

1. identify whether the raw origin, Channel mapping, or lineage changed;
2. apply a versioned rule;
3. recompute Lead, ClosedDeal, AcquiredSeller, Order, GMV, and dependent ratio slices consistently;
4. disclose the affected periods and synthetic scenarios.

Partial reassignment is prohibited because it would create inconsistent numerators and denominators.

## Known limitations

- First Known Acquisition Source is observable association, not true first touch, incrementality, or causal attribution.
- Pre-MQL and multi-touch history are unavailable.
- origin quality and taxonomy coverage constrain Channel reporting.
- Campaign-level attribution is not natively supported by the public funnel source.
- seller_id lineage associates acquired sellers with downstream transactions but does not prove causal marketing impact.
- Multi-seller Orders are non-additive across seller-attribution slices.
- Synthetic spend supports controlled scenarios only and cannot establish real historical cost efficiency.

## OPEN DECISIONS

- Approve the origin-to-Channel taxonomy and mapping ownership.
- Decide whether a defensible landing_page_id-to-Campaign mapping exists; default remains no Campaign.
- Define the controlled synthetic spend-generation and disclosure methodology.
- Determine whether a future interaction source justifies true first-touch, last-touch, multi-touch, or a lookback window.
- Set rules for historical mapping restatements and their published version labels.
