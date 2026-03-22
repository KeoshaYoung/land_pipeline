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

| Scenario | Trigger | Flow |
|---|---|---|
| Nightly CSV Backup | Schedule (2:05 AM ET) | Airtable → CSV → Google Drive `/Backups/YYYY-MM-DD/` |
| PandaDoc - Create Offer Letter | Webhook from Prefect | Webhook → PandaDoc API → Airtable Offers update |
| PandaDoc - Create PSA | Webhook from Prefect | Webhook → PandaDoc API → Airtable Offers update |

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
| Phase 1 | Lead ingest + enrichment automation | 🟡 20% | flow_leads.py built — Make automation pending |
| Phase 2 | Offer generation | ✅ 100% | Crash fixed, Airtable writeback added, all deployments verified |
| Phase 3 | Contract + reporting automation | 🟡 40% | Templates done, webhooks pending |
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
4. ⏳ Audit Make scenarios — **starting next session**
5. ⏳ Audit PandaDoc templates + webhooks
6. ⏳ Complete Airtable data migration — link existing contacts to Parcels, clean deprecated fields
7. ⏳ Build Phase 1 Make automation — lead import, dedupe, enrichment trigger
8. ⏳ Build Claude API integrations — Dexter (property research), Milli (follow-ups)
9. ⏳ Send follow-up on Hogan + Mogannam offers (Day 3/7/14 sequence)

---

## Future Integrations

| Integration | Purpose | Phase |
|---|---|---|
| DataTree API | Property enrichment | Phase 1 |
| QuickBooks Online | Accounting + tax prep | Phase 3 |
| PropStream | Lead source | Active |
| Gmail API | Email automation | Phase 1 |
| Google Drive API | Document filing | Phase 3 |

---

## Current Deal Activity

| # | Owner | Acres | Assessed | Offer Sent | Status |
|---|---|---|---|---|---|
| #2 | Christopher Mogannam | 8.9 | $51,500 | $36,050 (70%) | Awaiting response |
| #4 | James Hogan | 20.7 | $126,000 | $88,200 (70%) | Awaiting response |
| #7 | Randy Vonsmith | 24.4 | $17,800 | Needs research | Zoning check needed |
| #9 | Steven Maloy | 35.7 | $36,880 | Needs research | Over 30 acres — borderline |
| #10 | Robert Allen | 9.0 | $74,200 | Needs research | Good candidate |

**Note:** Original offers sent Nov 4, 2025 were at ~20% of assessed value based on old business model. Current model is 70% of assessed. Consider sending revised offers.
