"""
Lead ingestion flow - fetches new leads from Airtable Lead Intake
and performs deduplication checks.
"""

from prefect import flow, task, get_run_logger
from typing import List, Dict, Any

from airtable_utils import (
    get_airtable_records,
    update_airtable_record,
    log_automation,
)


@task(retries=3, retry_delay_seconds=10)
def fetch_new_leads() -> List[Dict[str, Any]]:
    """
    Fetch records from Lead Intake where Needs Enrichment = checked.
    Uses the 'Needs Enrichment' view.

    Returns:
        List of Airtable record dicts
    """
    records = get_airtable_records(
        table_name="Lead Intake",
        view="Needs Enrichment",
    )
    return records


@task(retries=2, retry_delay_seconds=5)
def check_for_duplicates(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check each lead's Lead Hash against existing Parcels records.
    Flags duplicates by setting Dedupe Flag = True in Lead Intake.

    Args:
        records: List of Lead Intake records to check

    Returns:
        List of non-duplicate records ready for enrichment
    """
    logger = get_run_logger()
    clean_records = []

    # Fetch all existing Lead Hashes from Parcels
    parcel_records = get_airtable_records(
        table_name="Parcels",
        filter_formula="NOT({Property ID} = '')"
    )
    existing_hashes = {
        r["fields"].get("Property ID", "").lower()
        for r in parcel_records
    }

    for record in records:
        fields = record.get("fields", {})
        lead_hash = fields.get("Lead Hash", "").lower()
        record_id = record.get("id")

        if lead_hash and lead_hash in existing_hashes:
            # Flag as duplicate
            update_airtable_record(
                table_name="Lead Intake",
                record_id=record_id,
                fields={"Dedupe Flag": True, "Needs Enrichment": False}
            )
            logger.warning(f"Duplicate detected — Lead Hash: {lead_hash} | Record: {record_id}")
        else:
            clean_records.append(record)

    logger.info(f"{len(records)} leads checked — {len(records) - len(clean_records)} duplicates flagged — {len(clean_records)} clean")
    return clean_records


@task(retries=2, retry_delay_seconds=5)
def score_lead(record: Dict[str, Any]) -> int:
    """
    Calculate lead score based on documented scoring framework.

    Scoring:
        Base: +5
        5-30 acres: +1
        Assessed value > 0: +1
        Out-of-state owner: +1 (requires Owner State field)
        Acreage < 5 or > 30: -2
        Zoning = Conservation or Private Preserve: -2

    Args:
        record: Lead Intake Airtable record

    Returns:
        Integer score (0-10)
    """
    fields = record.get("fields", {})
    score = 5  # base

    acreage = float(fields.get("Acreage") or 0)
    assessed_value = float(fields.get("Est. Market Value") or 0)
    owner_state = (fields.get("Owner State") or "").strip().upper()
    zoning = (fields.get("Zoning Type") or fields.get("Zoning") or "").lower()

    # Additions
    if 5 <= acreage <= 30:
        score += 1
    if assessed_value > 0:
        score += 1
    if owner_state and owner_state not in ("GA", "GEORGIA"):
        score += 1  # out-of-state owner

    # Deductions
    if acreage < 5 or acreage > 30:
        score -= 2
    if any(term in zoning for term in ["conservation", "private preserve"]):
        score -= 2

    return max(0, min(10, score))  # clamp to 0-10


@flow(name="lead_ingest", log_prints=True)
def lead_ingest() -> Dict[str, Any]:
    """
    Nightly lead ingestion flow.

    Steps:
        1. Fetch leads flagged Needs Enrichment from Lead Intake
        2. Deduplicate against existing Parcels
        3. Score each clean lead
        4. Write Lead Score back to Lead Intake
        5. Log summary to Automations Log

    Returns:
        Summary dict with counts
    """
    logger = get_run_logger()
    print("🔄 Starting lead ingest...")

    # Step 1 — Fetch leads
    raw_leads = fetch_new_leads()
    print(f"Found {len(raw_leads)} leads needing enrichment")

    if not raw_leads:
        print("No new leads — exiting")
        log_automation(
            action_type="Lead Imported",
            source="Prefect",
            status="Success",
            related_table="Lead Intake",
            payload='{"leads_found": 0}',
        )
        return {"leads_found": 0, "duplicates": 0, "scored": 0}

    # Step 2 — Deduplicate
    clean_leads = check_for_duplicates(raw_leads)
    duplicates = len(raw_leads) - len(clean_leads)

    # Step 3 & 4 — Score and write back
    scored = 0
    for record in clean_leads:
        record_id = record.get("id")
        score = score_lead(record)

        update_airtable_record(
            table_name="Lead Intake",
            record_id=record_id,
            fields={"Lead Score": score}
        )
        scored += 1
        print(f"Lead {record_id} scored: {score}/10")

    # Step 5 — Log summary
    summary = {
        "leads_found": len(raw_leads),
        "duplicates": duplicates,
        "scored": scored,
    }

    log_automation(
        action_type="Lead Imported",
        source="Prefect",
        status="Success",
        related_table="Lead Intake",
        payload=str(summary),
    )

    print(f"✅ Lead ingest complete — {scored} leads scored, {duplicates} duplicates flagged")
    return summary


if __name__ == "__main__":
    lead_ingest()
