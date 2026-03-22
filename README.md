# Land Pipeline — Young Legacy Veterans Consulting LLC

Automated land acquisition and disposition pipeline for wholesale land flipping in Georgia.

**Business Model:** Buy at 70% of assessed value, sell at 80-90%. Target $5k-$10k profit per deal at volume.
**Target Market:** 5-30 acres, vacant land, Georgia (starting Lincoln County)

---

## Airtable Structure

**Base:** Land Operations (`appH47oqHREWCJQ5E`)

### Tables

| Table | Purpose | Key Views |
|---|---|---|
| Lead Intake | Raw imports from PropStream and web sources | Export All, New Today, Has Contact Info, Needs Enrichment, De-dupe Candidates, Skip Trace Needed, Out of State Owners |
| Contacts | Unified seller + buyer contact records | Export All, Sellers with Active Offers, No Response Follow Up Needed, Multiple Properties |
| Opportunities | Seller-side deal pipeline | Export All, Kanban by Stage, Needs Follow Up, Stale Offers, Won This Month |
| Parcels | Master property registry | Export All, Active Inventory, Sold, Offer Ready, List Trigger |
| Offers | PandaDoc offer tracking | All Offers, Sent Not Viewed, Viewed No Response, Completed |
| Listings | Buyer-facing property marketing | All Listings, Active Listings, Needs Assets, Price Reduced, Days on Market 30+ |
| Buyers/Deals | Buyer pipeline + deal management | Active Deals, Won Deals, All Deals, Follow-up Needed, Hot Leads, This Week's Follow-ups, By Property, Lead Source, Kanban by Temperature |
| Transactions | Deal-level P&L tracking | Unposted, By Property, All Transactions, This Month, Needs QBO Sync, By Property P&L |
| Automations Log | Debugging + audit trail | Recent, Errors Only, Last 24 Hours, By Source, Unresolved Errors |
| KPIs | Weekly performance dashboard | All Records, Last 12 Weeks, Monthly Summary, Quarterly Summary |
| Backup Log | Automated backup tracking | All Backups, Failed Backups, Unverified |
| Email Templates | Standardized outreach templates | Grid View, Active Templates, Email Sequences, SMS Templates |
| Web Leads | Web form + ad lead capture | All Web Leads, Not Converted, Buyers, Sellers |

### Relationship Chain

```
Web Leads ──────────────────────────────────────────► Contacts
                                                           │
Lead Intake ──► Parcels ◄──────────────────────────────────┤
                   │                                       │
                   ├──► Offers ◄── Opportunities ◄─────────┤
                   │                                       │
                   ├──► Listings ──► Buyers/Deals ──────────┤
                   │                      │
                   └──► Transactions ◄────┘
```

### Key Formulas

**Lead Intake**
```
Lead Hash: LOWER(SUBSTITUTE({APN} & "-" & {County} & "-" & {State}, " ", ""))
Skip Trace Needed: IF(AND({Owner Phone} = "", {Owner Email} = "", {Needs Enrichment} = FALSE()), TRUE(), FALSE())
Out of State Owner: IF(AND(LEN({Owner State}) > 0, {Owner State} != "GA", {Owner State} != "Georgia"), TRUE(), FALSE())
```

**Parcels**
```
Property ID: LOWER(SUBSTITUTE({APN} & "-" & {County} & "-" & {State}, " ", ""))
Max Offer: ROUND({Assessed Value} * 0.70, 0)
Offer Ready: AND({Assessed Value} > 0, {Max Offer} > 0, LEN({Owner Name}) > 0, LEN({Owner Email}) > 0, LEN({APN}) > 0, {Acreage} > 0)
```

**Offers**
```
Expires On: DATEADD({Sent Date}, 14, 'days')
```

**Listings**
```
Days on Market: IF({Status} = "Sold", DATETIME_DIFF({Sold Date}, {Created}, 'days'), DATETIME_DIFF(TODAY(), {Created}, 'days'))
Price Reduced: IF(AND({Original List Price} > 0, {List Price} < {Original List Price}), TRUE(), FALSE())
```

**Buyers/Deals**
```
Days Since Contact: IF({Last Contact Date}, DATETIME_DIFF(TODAY(), {Last Contact Date}, 'days'), DATETIME_DIFF(TODAY(), {Created}, 'days'))
Follow-up Needed: IF(OR({Stage} = "Closed", {Stage} = "Dead"), FALSE(), IF({Days Since Contact} = 0, TRUE(), OR({Days Since Contact} > 7, AND({Next Follow-up Date} != "", IS_BEFORE({Next Follow-up Date}, TODAY())))))
```

**Transactions**
```
Net Profit: IF({Type} = "Income", {Amount}, IF({Type} = "Expense", {Amount} * -1, 0))
```

### Airtable-Native Automations

| Automation | Trigger | Action |
|---|---|---|
| Auto-flag Needs Enrichment | New record in Lead Intake | Set Needs Enrichment = checked |
| Auto-set Contact Type to Buyer | New record in Buyers/Deals | Set Contact Type = Buyer on linked Contact |

---

## Prefect Deployments

| Deployment | Schedule | Parameters | Status |
|---|---|---|---|
| `lead_ingest/nightly_ingest` | Daily 2:00 AM ET | none | ✅ Active — verified |
| `nightly-backup/nightly_backup` | Daily 2:05 AM ET | tables, subfolder, make_webhook_url | ✅ Active — verified |
| `create-offer-letter/pandadoc-offer` | Manual trigger | seller_name, seller_email, property_address, apn, county, offer_amount, make_webhook_url, parcel_record_id | ✅ Active |
| `create-psa/pandadoc-psa` | Manual trigger | seller_name, seller_email, property_address, apn, county, offer_amount, earnest_money, make_webhook_url, parcel_record_id | ✅ Active |

### Known Issues Fixed

**SignatureMismatchError — `make_webhook_url` parameter mismatch** ✅ Resolved
- Deployment was passing `make_webhook_url` but flow functions only accepted `tables` and `subfolder`
- Fix: Added `make_webhook_url: Optional[str] = None` to `nightly_backup`, `create_offer_letter`, and `create_psa` flow signatures
- Fix: Removed `make_webhook_url: null` from `prefect.yaml` deployment parameter blocks
- All 4 deployments redeployed and verified working March 21, 2026

### Prefect Secrets Required

| Secret | Description |
|---|---|
| `github_pat` | GitHub personal access token |
| `make-backup-webhook` | Nightly backup webhook URL |
| `pandadoc-offer-webhook` | Offer letter webhook URL |
| `pandadoc-psa-webhook` | PSA webhook URL |
| `airtable-api-key` | Airtable API key |
| `airtable-land-ops-base-id` | Land Operations base ID (`appH47oqHREWCJQ5E`) |

---

## Make Scenarios

| Scenario | Trigger | Flow | Status |
|---|---|---|---|
| Nightly CSV Backup | Webhook from Prefect (2:05 AM ET) | Airtable → CSV → Google Drive `/Backups/YYYY-MM-DD/` | ✅ Active — verified |
| PandaDoc - Create Offer Letter | Webhook from Prefect | Webhook → PandaDoc Create Document → Airtable Offers create record | ✅ Active — verified |
| PandaDoc - Create PSA | Webhook from Prefect | Webhook → PandaDoc Create Document → Airtable Offers create record | ✅ Active — verified |
| REAPI Lead Import — GA Land | Daily 1:00 AM ET | REAPI PropertySearch → Iterator → Filter → Airtable Search (dedupe) → Lead Intake create record → Automations Log | ✅ Active — verified |

### Nightly CSV Backup — Table Coverage

| Table | Backed Up |
|---|---|
| Lead Intake | ✅ |
| Contacts | ✅ |
| Parcels | ✅ |
| Opportunities | ✅ |
| Offers | ✅ |
| Listings | ✅ |
| Buyers/Deals | ✅ |
| Transactions | ✅ |
| Email Templates | ✅ |
| Web Leads | ✅ |
| Backup Log | ✅ |
| Automations Log | ❌ Intentionally excluded — debug data only |
| KPIs | ❌ Intentionally excluded — calculated from source tables |

### REAPI Lead Import — Configuration

**API:** RealEstateAPI.com (Backend Secret key stored in Prefect Secret block `reapi-api-key`)

**Search parameters:**
```json
{
  "state": "GA",
  "property_type": "LAND",
  "lot_size_min": 217800,
  "lot_size_max": 1306800,
  "size": 500
}
```

**Target counties (10 high-growth GA counties):**
Jackson, Barrow, Walton, Newton, Jasper, Morgan, Effingham, Bryan, Long, Dawson

**Filter logic:**
- County must match one of 10 target counties (OR)
- `corporateOwned` = false (AND)
- `ownerOccupied` = false (AND)
- `assessedValue` > 0 (AND)
- Lead Hash not already in Lead Intake (dedupe check)

**Field mapping:**

| REAPI Field | Airtable Field | Transform |
|---|---|---|
| `address.county` | County | Direct |
| `address.state` | State | Direct |
| `apn` | APN | Direct |
| `address.address` | Address | Direct |
| `address.city` | City | Direct |
| `address.zip` | Zip | Direct |
| `lotSquareFeet` | Acreage | `round(x / 43560, 2)` |
| `owner1FirstName` + `owner1LastName` | Owner Name | Concatenate |
| `mailAddress.address` | Seller Mailing Address | Direct |
| `mailAddress.state` | Owner State | Direct |
| `assessedValue` | Est. Market Value | Direct |
| `latitude` | Lat | Direct |
| `longitude` | Lon | Direct |

**Note:** `size: 500` pulls 500 statewide GA records and filters to target counties in Make. Future optimization: run one HTTP call per county (10 x 50 records) using Make repeater for guaranteed county coverage.

### Make — Known Issues Fixed

**Nightly CSV Backup:**
- Scenario was Inactive — never ran until March 22, 2026
- Airtable OAuth connection broken (400 error) — reconnected
- Duplicate Google Drive connection deleted — consolidated to one
- CSV modules referencing wrong source module numbers — remapped
- Offers module had record limit of 10 — removed
- Lead Intake output fields updated — added Lead Score, Owner State, Out of State Owner, Skip Trace Needed, Zoning Type
- 3 new table branches added — Email Templates, Web Leads, Backup Log

**PandaDoc - Create Offer Letter:**
- Airtable module was writing to Automations Log instead of Offers — fixed
- Airtable module fields were all empty — mapped Doc ID, PandaDoc URL, Offer Amount, Sent Date, Template, Doc Status
- Send a document was off — sellers never received emails — fixed
- Seller Date field empty — set to now
- Duplicate Offer records (Prefect + Make both writing) — removed Prefect writeback, Make owns Offers table

**PandaDoc - Create PSA:**
- Scenario was Inactive — never ran — fixed
- No Airtable writeback module at all — added
- Send a document was off — fixed
- Seller Date empty — fixed
- Subject and Message fields empty — configured
- Property.LegalDescription token added to template and synced to Make

---

## PandaDoc Templates

| Template | Type | Status |
|---|---|---|
| Offer Letter | Offer | ✅ Created & tested |
| Purchase & Sale Agreement (PSA) | Contract | ✅ Created |
| Assignment Agreement | Contract | ✅ Created |

**Note:** PSA and Assignment Agreement are contract-stage documents. Do not trigger these from the Offers table — they belong to the Transactions stage.

---

## AI Integration

**Platform:** Claude API (replacing Sintra AI)

| Role | Former Sintra Agent | Claude API Implementation | Priority |
|---|---|---|---|
| Property Research | Dexter | Make scenario → Claude API → Airtable Parcels | Phase 1 |
| Follow-up Sequences | Milli | Make scenario → Claude API → Email Templates → Gmail | Phase 1 |
| Email Responses | Emmie | Make scenario → Claude API → Gmail | Phase 2 |
| Buyer Inquiries | Cassie | Make scenario → Claude API → Buyers/Deals | Phase 5 |
| Copywriting | Penn | Claude API on demand | Phase 4 |
| Social Media | Soshie | Claude API on demand | Phase 4 |
| SEO | Seomi | Claude API on demand | Phase 11 |
| Web Builder | Commet | Claude API on demand | Phase 8 |

---

## Email Templates

All templates use `{{token}}` format for variable injection.

### Seller Templates

| Template | Sequence Step | Use Case |
|---|---|---|
| Seller - Initial Offer | 1 | First outreach with cash offer |
| Seller - Day 3 Follow Up | 2 | Soft reminder |
| Seller - Day 7 Follow Up | 3 | Value-add follow up with flexibility messaging |
| Seller - Day 14 Final Follow Up | 4 | Final notice before offer expiry |
| Seller - Counter Offer Response | 5 | Response to seller counter |

### Buyer Templates

| Template | Sequence Step | Use Case |
|---|---|---|
| Buyer - Initial Inquiry | 1 | Response to buyer inquiry with property details |
| Buyer - Follow Up | 2 | Follow up on buyer conversation |
| Buyer - Offer Made | 3 | Acknowledge buyer offer received |

### Standard Tokens

| Token | Source |
|---|---|
| `{{owner_name}}` | Parcels → Owner Name |
| `{{buyer_name}}` | Buyers/Deals → Buyer Name |
| `{{property_address}}` | Parcels → Address |
| `{{acreage}}` | Parcels → Acreage |
| `{{county}}` | Parcels → County |
| `{{apn}}` | Parcels → APN |
| `{{zoning}}` | Parcels → Zoning Type |
| `{{offer_amount}}` | Offers → Offer Amount |
| `{{list_price}}` | Listings → List Price |
| `{{expiry_date}}` | Offers → Expires On |
| `{{images_folder}}` | Listings → Images Folder |
| `{{sender_name}}` | Static — your name |
| `{{sender_phone}}` | Static — your phone |

---

## Google Drive Structure

```
/LandOps/
  ├── Raw_Exports/
  ├── Canva_Bulk/
  ├── Reports/
  ├── Contracts/
  ├── Property_Folders/
  └── Backups/
      └── YYYY-MM-DD/    (auto-created daily by Make)
```

---

## Business Process

### Lead Scoring Framework

| Factor | Points |
|---|---|
| Base score | +5 |
| 5-30 acres | +1 |
| Assessed value in range | +1 |
| Out-of-state owner | +1 |
| Long hold time | +1 |
| Delinquent taxes | +1 |
| Too small/large | -2 |
| Recent purchase (<12 months) | -2 |
| Local owner | -1 |
| Bad zoning (Conservation/Private Preserve) | -2 |

**Threshold:** Score ≥ 6 → Create Parcel record and trigger enrichment

### Offer Strategy

| Stage | % of Assessed Value |
|---|---|
| Initial offer | 70% |
| Max negotiation | 70% (firm) |
| Target sale price | 80-90% |
| Target profit per deal | $5,000 - $10,000 |

**Offer expiry:** 14 days
**Follow-up sequence:** Day 3, Day 7, Day 14

### Deal Structure

- **Primary model:** Wholesale (assignment or double-close)
- **Assignment fee:** When possible, assign contract to end buyer
- **Double-close:** When assignment not possible or buyer prefers clean title

---

## Phase Status

| Phase | Description | Status | Notes |
|---|---|---|---|
| Phase 0 | Business foundation + tech stack | ✅ 100% | LLC, bank account, tools configured |
| Phase 1 | Lead ingest + enrichment automation | 🟡 50% | REAPI lead import live, enrichment + scoring pending |
| Phase 2 | Offer generation | ✅ 100% | Crash fixed, Airtable writeback, Make scenarios verified, sellers receive emails |
| Phase 3 | Contract + reporting automation | 🟡 50% | Templates done, PSA flow live, PandaDoc webhooks active |
| Phase 4 | Marketing auto-distribution | 🟡 30% | Accounts created, no posts |
| Phase 5 | Buyer pipeline automation | ⏳ 20% | Tables ready, workflows pending |
| Phase 6 | Closing + double-close automation | ⏳ 5% | Assignment template only |
| Phase 7 | Analytics + optimization | ⏳ 10% | KPI table rebuilt, dashboard pending |
| Phase 8 | Investor portal + website | ⏳ 0% | Month 6+ |
| Phase 9 | AI deployment (Claude API) | 🟡 10% | Platform decided, builds pending |
| Phase 10 | Team building + delegation | ⏳ 0% | Month 4+ |
| Phase 11 | Advanced marketing | ⏳ 0% | Month 6+ |
| Phase 12 | Scale + systematize | ⏳ 0% | Year 1-2 |

---

## Immediate Next Steps

1. ✅ Fix Prefect `SignatureMismatchError` — resolved, all deployments verified
2. ✅ Airtable full audit + rebuild — all 13 tables restructured, 40+ fields added, 25+ views added
3. ✅ Prefect code overhaul — real lead ingest, Airtable writeback on offers, proper logging
4. ✅ Make audit — all 3 scenarios fixed, activated, and verified
5. ✅ PandaDoc audit — both templates verified, sellers now receive documents via email
6. ✅ REAPI Lead Import built and activated — 10 target GA counties, daily at 1AM
7. ⏳ Build Claude API property enrichment flow — research each lead, update Lead Score
8. ⏳ Build Milli replacement — automated Day 3/7/14 follow-up sequences on sent offers
9. ⏳ Optimize REAPI import — one HTTP call per county using Make repeater

---

## Future Integrations

| Integration | Purpose | Phase |
|---|---|---|
| Claude | Property enrichment | Phase 1 |
| QuickBooks Online | Accounting + tax prep | Phase 3 |
| REAPI | Lead source | Active |
| Gmail API | Email automation | Phase 1 |
| Google Drive API | Document filing | Phase 3 |


