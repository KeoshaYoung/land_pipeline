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
    # Load credentials
    api_key_secret = Secret.load("airtable-api-key")
    api_key = api_key_secret.get()
    
    base_id_secret = Secret.load("airtable-land-ops-base-id")
    base_id = base_id_secret.get()
    
    # Build URL
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    
    # Build params
    params = {}
    if view:
        params["view"] = view
    if filter_formula:
        params["filterByFormula"] = filter_formula
    if max_records:
        params["maxRecords"] = max_records
    
    # Make request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
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
    # Load credentials
    api_key_secret = Secret.load("airtable-api-key")
    api_key = api_key_secret.get()
    
    base_id_secret = Secret.load("airtable-land-ops-base-id")
    base_id = base_id_secret.get()
    
    # Build URL
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    
    # Make request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {"fields": fields}
    
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
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
    # Load credentials
    api_key_secret = Secret.load("airtable-api-key")
    api_key = api_key_secret.get()
    
    base_id_secret = Secret.load("airtable-land-ops-base-id")
    base_id = base_id_secret.get()
    
    # Build URL
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}/{record_id}"
    
    # Make request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {"fields": fields}
    
    response = httpx.patch(url, headers=headers, json=payload, timeout=30.0)
    response.raise_for_status()
    
    return response.json()


@task(retries=2, retry_delay_seconds=5)
def log_automation(
    action: str,
    status: str = "Success",
    record_url: Optional[str] = None,
    payload: Optional[str] = None,
    error_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log an automation action to Automations Log table.
    
    Args:
        action: Description of what happened
        status: Success, Error, or Warning
        record_url: Optional URL to affected record
        payload: Optional JSON payload
        error_message: Optional error message
        
    Returns:
        Created log record
    """
    fields = {
        "Action": action,
        "Status": status
    }
    
    if record_url:
        fields["Record URL"] = record_url
    if payload:
        fields["Payload"] = payload
    if error_message:
        fields["Error Message"] = error_message
    
    return create_airtable_record("Automations Log", fields)


if __name__ == "__main__":
    # Test by getting Lead Intake records
    records = get_airtable_records(
        table_name="Lead Intake",
        view="New Today",
        max_records=5
    )
    print(f"Found {len(records)} records")
