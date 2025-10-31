"""
Nightly backup flow - triggers Make webhook to export Airtable → CSV → Google Drive.
"""

from prefect import flow, task
from prefect.blocks.system import Secret
import httpx
from typing import List, Optional


@task(retries=2, retry_delay_seconds=10)
def trigger_make_backup(webhook_url: str, tables: List[str], subfolder: str) -> dict:
    """
    POST to Make webhook to trigger Airtable → CSV → Drive backup.
    
    Args:
        webhook_url: Make webhook URL (loaded from Secret block)
        tables: List of table names to back up (empty = all tables)
        subfolder: Optional subfolder name in /Backups/ (empty = date-based folder)
        
    Returns:
        Response from Make webhook
    """
    payload = {
        "tables": tables,
        "subfolder": subfolder
    }
    
    response = httpx.post(
        webhook_url,
        json=payload,
        timeout=60.0
    )
    response.raise_for_status()
    
    return response.json() if response.text else {"status": "triggered"}


@flow(name="nightly-backup", log_prints=True)
def nightly_backup(
    tables: Optional[List[str]] = None,
    subfolder: str = ""
) -> dict:
    """
    Trigger nightly Airtable backup via Make webhook.
    
    Args:
        tables: List of specific tables to backup (empty/None = all tables from registry)
        subfolder: Optional subfolder name (empty = creates YYYY-MM-DD folder)
        
    Returns:
        Webhook response
    """
    print("🔄 Starting nightly Airtable backup...")
    
    # Load webhook URL from Secret block
    webhook_secret = Secret.load("make-backup-webhook")
    webhook_url = webhook_secret.get()
    
    # Default to empty list if None
    if tables is None:
        tables = []
    
    print(f"Tables to backup: {tables if tables else 'ALL (from registry)'}")
    print(f"Subfolder: {subfolder if subfolder else 'YYYY-MM-DD (auto)'}")
    
    # Trigger the backup
    result = trigger_make_backup(webhook_url, tables, subfolder)
    
    print("✅ Backup triggered successfully")
    return result


if __name__ == "__main__":
    # Test locally
    nightly_backup()