"""
Airtable utilities for Land Operations base.
"""

from prefect import task
from prefect.blocks.system import Secret
import httpx
from typing import Dict, List, Any, Optional


@task(retries=2, retry_delay_seconds=5)
def get_airtable_records(
    table_name: str,
    view: Optional[str] = None,
    filter_formula: Optional[str] = None,
    max_records: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get records from Airtable table.

    Args:
        table_name: Name of the table (e.g., "Lead Intake")
        view: Optional view name
        filter_formula: Optional Airtable formula for filtering
        max_records: Maximum number of records to return

    Returns:
        List of record dictionaries
    """
    api_key, base_id = _load_credentials()

    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = _build_headers(api_key)

    params = {}
    if view:
        params["view"] = view
    if filter_formula:
        params["filterByFormula"] = filter_formula
    if max_records:
        params["maxRecords"] = max_records

    all_records = []
    offset = None

    while True:
        if offset:
            params["offset"] = offset

        response = httpx.get(url, headers=headers, params=params, timeout=30.0)
        response.raise_for_status()

        data = response.json()
        all_records.extend(data.get("records", []))

        offset = data.get("offset")
        if not offset:
            break

    return all_records


@task(retries=2, retry_delay_seconds=5)
def create_airtable_record(
    table_name: str,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new record in Airtable.

    Args:
        table_name: Name of the table
        fields: Dictionary of field names and values

    Returns:
        Created record data
    """
    api_key, base_id = _load_credentials()

    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = _build_headers(api_key)

    response = httpx.post(url, headers=headers, json={"fields": fields}, timeout=30.0)
    response.raise_for_status()

    return response.json()


@task(retries=2, retry_delay_seconds=5)
def update_airtable_record(
    table_name: str,
    record_id: str,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing record in Airtable.

    Args:
        table_name: Name of the table
        record_id: Airtable record ID (starts with "rec")
        fields: Dictionary of field names and values to update

    Returns:
        Updated record data
    """
    api_key, base_id = _load_credentials()

    url = f"https://api.airtable.com/v0/{base_id}/{table_name}/{record_id}"
    headers = _build_headers(api_key)

    response = httpx.patch(url, headers=headers, json={"fields": fields}, timeout=30.0)
    response.raise_for_status()

    return response.json()


@task(retries=2, retry_delay_seconds=5)
def log_automation(
    action_type: str,
    source: str = "Prefect",
    status: str = "Success",
    related_table: Optional[str] = None,
    record_url: Optional[str] = None,
    payload: Optional[str] = None,
    error_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log an automation action to Automations Log table.

    Valid action_type values (must match Airtable single select):
        Lead Imported, Dedupe Check, Enrichment Triggered, Offer Generated,
        Doc Sent, Doc Status Updated, Follow-up Sent, Listing Published,
        Record Sync, KPI Updated, Backup Run, Other

    Valid source values:
        Prefect, Make, Airtable, Sintra, Manual

    Valid related_table values:
        Lead Intake, Parcels, Contacts, Opportunities, Offers,
        Listings, Buyers/Deals, Transactions, KPIs, Email Templates, Multiple

    Args:
        action_type: Type of action (single select — see valid values above)
        source: System that triggered the action (single select)
        status: Success, Error, or Warning
        related_table: Which Airtable table was affected (single select)
        record_url: Optional URL to affected record
        payload: Optional JSON payload string
        error_message: Optional error message

    Returns:
        Created log record
    """
    fields = {
        "Action Type": action_type,   # single select — replaces old free-text "Action"
        "Source": source,             # single select — new field
        "Status": status,
    }

    if related_table:
        fields["Related Table"] = related_table   # single select — new field
    if record_url:
        fields["Record URL"] = record_url
    if payload:
        fields["Payload"] = payload
    if error_message:
        fields["Error Message"] = error_message

    return create_airtable_record("Automations Log", fields)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_credentials():
    """Load Airtable API key and base ID from Prefect Secret blocks."""
    api_key = Secret.load("airtable-api-key").get()
    base_id = Secret.load("airtable-land-ops-base-id").get()
    return api_key, base_id


def _build_headers(api_key: str) -> Dict[str, str]:
    """Build standard Airtable request headers."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


if __name__ == "__main__":
    records = get_airtable_records(
        table_name="Lead Intake",
        view="New Today",
        max_records=5
    )
    print(f"Found {len(records)} records")
