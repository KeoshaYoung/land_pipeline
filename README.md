# Land Pipeline - Young Legacy Veterans Consulting LLC

Automated land acquisition and disposition pipeline.

## Airtable Structure

**Base:** Land Operations (`appH47oqHREWCJQ5E`)

### Tables:
- Lead Intake
- Contacts
- Opportunities
- Parcels
- Offers
- Listings
- Buyers/Deals
- Transactions
- Automations Log
- KPIs
- Backup Registry

## Prefect Deployments

1. **lead_ingest/nightly_ingest** - Daily at 2:00 AM ET
2. **nightly-backup/nightly_backup** - Daily at 2:05 AM ET
3. **create-offer-letter/pandadoc-offer** - Manual trigger
4. **create-psa/pandadoc-psa** - Manual trigger

## Prefect Secrets Required

- `github_pat` - GitHub personal access token (if private repo)
- `make-backup-webhook` - Nightly backup webhook URL
- `pandadoc-offer-webhook` - Offer letter webhook URL
- `pandadoc-psa-webhook` - PSA webhook URL
- `airtable-api-key` - Airtable API key
- `airtable-land-ops-base-id` - Land Operations base ID

## Make Scenarios

1. **Nightly CSV Backup** - Airtable → CSV → Google Drive
2. **PandaDoc - Create Offer Letter** - Webhook → PandaDoc
3. **PandaDoc - Create PSA** - Webhook → PandaDoc

## Google Drive Structure
```
/LandOps/
  ├── Raw_Exports/
  ├── Canva_Bulk/
  ├── Reports/
  ├── Contracts/
  ├── Property_Folders/
  └── Backups/
      └── YYYY-MM-DD/ (auto-created daily)
```

## Future Integrations

- DataTree API (enrichment)
- QuickBooks Online (accounting)
- HubSpot (buyer CRM)
- PropStream (lead source)
