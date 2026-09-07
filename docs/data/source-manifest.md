# Source Manifest

## Acquisition policy

The preferred mechanism is the official Kaggle CLI, invoked by `scripts/acquire_olist_data.py`. The script can also organize CSVs or ZIP archives previously downloaded from the official Kaggle dataset pages. It never embeds credentials, uses unofficial mirrors, or overwrites divergent raw files.

Every acquired CSV is recorded locally in `data/raw/manifest.json` with its source dataset, acquisition method, relative path, byte size, and SHA-256. Dataset version is explicitly `UNKNOWN_NOT_CAPTURED` until a reliable metadata-capture mechanism is added. The local manifest and profiling outputs are intentionally ignored because they describe a particular local copy. Versioned documentation records the reproducible procedure and canonical source identifiers instead of coupling Git to an unverified download.

## Olist Marketing Funnel

- **Source name:** Marketing Funnel by Olist
- **Provider:** Olist, distributed through Kaggle
- **Source type:** public, anonymized and sampled real-world dataset
- **Public dataset identifier:** `olistbr/marketing-funnel-olist`
- **Acquisition method:** official Kaggle CLI download; fallback is manual download from the official page followed by `import-local`
- **Source URL/reference:** `https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist`
- **License/usage notes:** CC BY-NC-SA 4.0 is declared on the official dataset page; downstream use must preserve attribution, non-commercial, and share-alike obligations as applicable
- **Expected files:** `olist_marketing_qualified_leads_dataset.csv`, `olist_closed_deals_dataset.csv`
- **Role inside LeadPulse:** B2B seller-acquisition funnel, First Known Acquisition Source, ClosedDeal, and AcquiredSeller lineage
- **Classification:** REAL-WORLD SOURCE
- **Refresh behavior:** static public snapshot; acquired on demand, never treated as an incremental production feed
- **Limitations:** approximately 8,000 sampled MQLs; no complete pre-MQL touch history, advertising spend, campaign taxonomy, or independently identifiable Opportunity lifecycle

## Olist Brazilian E-Commerce

- **Source name:** Brazilian E-Commerce Public Dataset by Olist
- **Provider:** Olist, distributed through Kaggle
- **Source type:** public, anonymized real-world dataset
- **Public dataset identifier:** `olistbr/brazilian-ecommerce`
- **Acquisition method:** official Kaggle CLI download; fallback is manual download from the official page followed by `import-local`
- **Source URL/reference:** `https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce`
- **License/usage notes:** UNKNOWN in this environment; verify the license displayed in the official Kaggle metadata before redistribution or external publication
- **Expected MVP files:** `olist_sellers_dataset.csv`, `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_customers_dataset.csv`, `olist_order_payments_dataset.csv`
- **Other expected files:** `olist_geolocation_dataset.csv`, `olist_order_reviews_dataset.csv`, `olist_products_dataset.csv`, `product_category_name_translation.csv`
- **Role inside LeadPulse:** connect AcquiredSeller through `seller_id` to OrderItem/Order activity and derive a carefully qualified GMV proxy
- **Classification:** REAL-WORLD SOURCE
- **Refresh behavior:** static public snapshot; acquired on demand, never treated as an incremental production feed
- **Limitations:** e-commerce Customer is the final buyer, not the acquired B2B seller; Order and payment multiplicities require seller-grain handling; refund/chargeback facts and row-level currency are unavailable

## Controlled Synthetic Advertising Spend

- **Source name:** Controlled Synthetic Advertising Spend
- **Provider:** LeadPulse-generated under the frozen conceptual contract in `docs/business/analytics-semantics.md`
- **Source type:** controlled synthetic source
- **Public dataset identifier:** not applicable
- **Acquisition method:** future deterministic generation process; contract defined but generation not implemented
- **Source URL/reference:** not applicable
- **License/usage notes:** OPEN DECISION before any distributable synthetic artifact is created
- **Expected files:** `synthetic_advertising_spend.csv` when the generation phase is explicitly authorized
- **Role inside LeadPulse:** enable explicitly labeled cost scenarios for CPL, Seller Acquisition Cost, and GMV ROAS
- **Classification:** CONTROLLED SYNTHETIC SOURCE
- **Refresh behavior:** versioned regeneration by scenario/methodology, never mixed with real data without provenance labels
- **Limitations:** cannot support claims about Olist's observed historical advertising cost or return; Campaign is absent from the MVP contract; numerical distribution parameters remain future implementation inputs

## Local provenance procedure

1. Run `python scripts/acquire_olist_data.py status` to inspect tool and file availability without reading credential values.
2. Use `download` only when the official Kaggle CLI is available, or use `import-local` with files downloaded from the canonical pages above.
3. The acquisition script validates expected filenames, refuses divergent overwrites, and writes deterministic SHA-256 inventory to `data/raw/manifest.json`.
4. Run `python scripts/profile_olist_data.py`; detailed results stay in `data/raw/_profiling/`.
5. Review manifest completeness and profiling errors before any modeling phase.

## Current local acquisition status

- **Status:** complete for the two selected real-world datasets.
- **Method:** manual Kaggle download followed by controlled local import with `scripts/acquire_olist_data.py import-local`.
- **Imported files:** 11 CSVs: two Marketing Funnel files and nine Brazilian E-Commerce files.
- **Uncompressed size:** 127,062,183 bytes.
- **Local checksum manifest:** `data/raw/manifest.json`, ignored by Git; it records filename, byte size, SHA-256, canonical dataset identifier, and acquisition method for every imported CSV.
- **Dataset version:** `UNKNOWN_NOT_CAPTURED`; the file-level hashes identify this copy, but Kaggle version metadata was not captured during the manual download.
- **Credentials:** none stored, read, or documented by LeadPulse.

The local files and hashes are empirical evidence for this workspace only. They remain unversioned and can be reproduced from the canonical source references plus the controlled import procedure.
