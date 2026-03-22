"""
Nightly backup flow - triggers Make webhook to export Airtable → CSV → Google Drive.
"""

from prefect import flow, task
from prefect.blocks.system import Secret
import httpx
from typing import List, Optional, Union


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

    # Make webhooks often return empty body or non-JSON text with 200/202
    if response.text and response.text.strip():
        try:
            return response.json()
        except Exception:
            return {"status": "accepted", "status_code": response.status_code}
    else:
        return {"status": "triggered", "status_code": response.status_code}


@flow(name="nightly-backup", log_prints=True)
def nightly_backup(
    tables: Optional[List[str]] = None,
    subfolder: str = "",
    make_webhook_url: Optional[str] = None  # FIX: added to match deployment parameter config
) -> dict:
    """
    Trigger nightly Airtable backup via Make webhook.

    Args:
        tables: List of specific tables to backup (empty/None = all tables)
        subfolder: Optional subfolder name (empty = creates YYYY-MM-DD folder)
        make_webhook_url: Optional webhook URL override (default: loads from Secret)

    Returns:
        Webhook response
    """
    print("🔄 Starting nightly Airtable backup...")

    # Use provided URL or fall back to Secret block
    if make_webhook_url:
        webhook_url = make_webhook_url
        print("Using webhook URL from parameter")
    else:
        webhook_secret = Secret.load("make-backup-webhook")
        webhook_url = webhook_secret.get()
        print("Using webhook URL from Secret block")

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
    nightly_backup()
