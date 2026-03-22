"""
PandaDoc document generation flows.
Triggers Make webhooks to create Offer Letters and PSAs.
Writes results back to Airtable Offers table and Automations Log.
"""

from prefect import flow, task
from prefect.blocks.system import Secret
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from airtable_utils import create_airtable_record, update_airtable_record, log_automation


@task(retries=2, retry_delay_seconds=5)
def call_pandadoc_webhook(webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call a Make webhook to trigger PandaDoc document creation.

    Args:
        webhook_url: The Make webhook URL
        payload: JSON payload with document data

    Returns:
        Response from the webhook
    """
    response = httpx.post(
        webhook_url,
        json=payload,
        timeout=30.0
    )
    response.raise_for_status()

    # Make webhooks often return empty body with 200/202 status
    if response.text and response.text.strip():
        try:
            return response.json()
        except Exception:
            return {"status": "accepted", "status_code": response.status_code}
    else:
        return {"status": "accepted", "status_code": response.status_code}


@task(retries=2, retry_delay_seconds=5)
def create_offer_record(
    parcel_record_id: Optional[str],
    offer_amount: str,
    sent_date: str,
    expiry_date: str,
    doc_id: Optional[str] = None,
    pandadoc_url: Optional[str] = None,
    contact_record_id: Optional[str] = None,
    opportunity_record_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a record in the Airtable Offers table after document generation.

    Args:
        parcel_record_id: Airtable record ID for the linked Parcel (starts with "rec")
        offer_amount: Dollar amount of the offer
        sent_date: Date offer was sent (YYYY-MM-DD)
        expiry_date: Date offer expires (YYYY-MM-DD)
        doc_id: PandaDoc document ID (if returned by webhook)
        pandadoc_url: PandaDoc document URL (if returned by webhook)
        contact_record_id: Airtable record ID for linked Contact
        opportunity_record_id: Airtable record ID for linked Opportunity

    Returns:
        Created Airtable Offers record
    """
    fields = {
        "Template": "Offer Letter",
        "Doc Status": "Sent",
        "Sent Date": sent_date,
        "Offer Amount": float(offer_amount) if offer_amount else 0,
    }

    if parcel_record_id:
        fields["Property"] = [{"id": parcel_record_id}]
    if contact_record_id:
        fields["Contact"] = [{"id": contact_record_id}]
    if opportunity_record_id:
        fields["Opportunity"] = [{"id": opportunity_record_id}]
    if doc_id:
        fields["Doc ID"] = doc_id
    if pandadoc_url:
        fields["PandaDoc URL"] = pandadoc_url

    return create_airtable_record("Offers", fields)


@flow(name="create-offer-letter", log_prints=True)
def create_offer_letter(
    seller_name: str,
    seller_email: str,
    property_address: str,
    apn: str,
    county: str,
    state: str = "GA",
    acreage: str = "0",
    offer_amount: str = "0",
    offer_expiry_days: int = 14,
    make_webhook_url: Optional[str] = None,  # optional override — default loads from Secret
    parcel_record_id: Optional[str] = None,  # Airtable rec ID for writeback
    contact_record_id: Optional[str] = None,
    opportunity_record_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an Offer Letter via PandaDoc and write results back to Airtable.

    Args:
        seller_name: Full name of the seller
        seller_email: Seller's email address
        property_address: Full property address
        apn: Assessor's Parcel Number
        county: County name
        state: State abbreviation (default: GA)
        acreage: Property acreage
        offer_amount: Offer price (without $ or commas)
        offer_expiry_days: Days until offer expires (default: 14)
        make_webhook_url: Optional webhook URL override
        parcel_record_id: Airtable Parcels record ID for linking Offer record
        contact_record_id: Airtable Contacts record ID for linking Offer record
        opportunity_record_id: Airtable Opportunities record ID for linking Offer record

    Returns:
        Webhook response
    """
    print(f"Creating Offer Letter for {property_address}")

    # Load webhook URL — use parameter override or fall back to Secret
    if make_webhook_url:
        webhook_url = make_webhook_url
    else:
        webhook_secret = Secret.load("pandadoc-offer-webhook")
        webhook_url = webhook_secret.get()

    # Calculate dates
    today = datetime.now().strftime("%Y-%m-%d")
    expiry_date = (datetime.now() + timedelta(days=offer_expiry_days)).strftime("%Y-%m-%d")

    # Build payload
    payload = {
        "Seller": {
            "FullName": seller_name,
            "Email": seller_email
        },
        "Property": {
            "Address": property_address,
            "APN": apn,
            "County": county,
            "State": state,
            "Acreage": str(acreage)
        },
        "Offer": {
            "Amount": str(offer_amount),
            "ExpiryDate": expiry_date
        },
        "Pricing": {
            "Date": today
        }
    }

    print(f"Offer Amount: ${offer_amount}")
    print(f"Expiry Date: {expiry_date}")

    # Call webhook
    result = call_pandadoc_webhook(webhook_url, payload)

    # Write Offer record back to Airtable
    doc_id = result.get("doc_id") or result.get("id")
    pandadoc_url = result.get("url") or result.get("pandadoc_url")

    offer_record = create_offer_record(
        parcel_record_id=parcel_record_id,
        offer_amount=offer_amount,
        sent_date=today,
        expiry_date=expiry_date,
        doc_id=doc_id,
        pandadoc_url=pandadoc_url,
        contact_record_id=contact_record_id,
        opportunity_record_id=opportunity_record_id,
    )
    print(f"✅ Offer record created in Airtable: {offer_record.get('id')}")

    # Log to Automations Log
    log_automation(
        action_type="Offer Generated",
        source="Prefect",
        status="Success",
        related_table="Offers",
        payload=json.dumps({"property_address": property_address, "offer_amount": offer_amount}),
    )

    print("✅ Offer Letter flow complete")
    return result


@flow(name="create-psa", log_prints=True)
def create_psa(
    seller_name: str,
    seller_email: str,
    property_address: str,
    apn: str,
    county: str,
    state: str = "GA",
    acreage: str = "0",
    offer_amount: str = "0",
    earnest_money: str = "0",
    closing_date: str = None,
    buyer_company: str = "Young Legacy Veterans Consulting LLC",
    buyer_signatory: str = "Managing Member",
    buyer_title: str = "Managing Member",
    inspection_days: str = "30",
    title_firm: str = "TBD",
    title_email: str = "closings@example.com",
    reserved_rights: str = "None",
    rollback_responsibility: str = "Buyer",
    offer_expiry_days: int = 14,
    make_webhook_url: Optional[str] = None,  # optional override — default loads from Secret
    parcel_record_id: Optional[str] = None,
    contact_record_id: Optional[str] = None,
    opportunity_record_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Purchase & Sale Agreement via PandaDoc and write results back to Airtable.

    Args:
        seller_name: Full name of the seller
        seller_email: Seller's email address
        property_address: Full property address
        apn: Assessor's Parcel Number
        county: County name
        state: State abbreviation (default: GA)
        acreage: Property acreage
        offer_amount: Purchase price (without $ or commas)
        earnest_money: Earnest money deposit (without $ or commas)
        closing_date: Target closing date (YYYY-MM-DD, default: 45 days)
        buyer_company: Buyer company name
        buyer_signatory: Name of person signing for buyer
        buyer_title: Title of person signing
        inspection_days: Due diligence period in days
        title_firm: Title/closing attorney firm name
        title_email: Title/closing attorney email
        reserved_rights: Mineral/timber rights reserved (if any)
        rollback_responsibility: Who pays rollback taxes (Buyer/Seller)
        offer_expiry_days: Days until offer expires (default: 14)
        make_webhook_url: Optional webhook URL override
        parcel_record_id: Airtable Parcels record ID for linking
        contact_record_id: Airtable Contacts record ID for linking
        opportunity_record_id: Airtable Opportunities record ID for linking

    Returns:
        Webhook response
    """
    print(f"Creating PSA for {property_address}")

    # Load webhook URL — use parameter override or fall back to Secret
    if make_webhook_url:
        webhook_url = make_webhook_url
    else:
        webhook_secret = Secret.load("pandadoc-psa-webhook")
        webhook_url = webhook_secret.get()

    # Calculate dates
    today = datetime.now().strftime("%Y-%m-%d")
    expiry_date = (datetime.now() + timedelta(days=offer_expiry_days)).strftime("%Y-%m-%d")

    if not closing_date:
        closing_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")

    # Build payload
    payload = {
        "Seller": {
            "FullName": seller_name,
            "Email": seller_email
        },
        "Buyer": {
            "CompanyName": buyer_company,
            "SignatoryName": buyer_signatory,
            "Title": buyer_title,
            "InspectionPeriodDays": str(inspection_days),
            "RollbackTaxResponsibility": rollback_responsibility
        },
        "Property": {
            "Address": property_address,
            "APN": apn,
            "County": county,
            "State": state,
            "Acreage": str(acreage),
            "ReservedRights": reserved_rights
        },
        "Offer": {
            "Amount": str(offer_amount),
            "Earnest": str(earnest_money),
            "ClosingDate": closing_date,
            "ExpiryDate": expiry_date
        },
        "TitleOrEscrow": {
            "FirmName": title_firm,
            "Email": title_email
        },
        "Pricing": {
            "Date": today
        }
    }

    print(f"Purchase Price: ${offer_amount}")
    print(f"Earnest Money: ${earnest_money}")
    print(f"Closing Date: {closing_date}")

    # Call webhook
    result = call_pandadoc_webhook(webhook_url, payload)

    # Log to Automations Log
    log_automation(
        action_type="Doc Sent",
        source="Prefect",
        status="Success",
        related_table="Offers",
        payload=json.dumps({"property_address": property_address, "offer_amount": offer_amount}),
    )

    print("✅ PSA flow complete")
    return result


if __name__ == "__main__":
    # Example usage for testing
    create_offer_letter(
        seller_name="Test Seller",
        seller_email="test@example.com",
        property_address="123 Test St, Atlanta, GA 30301",
        apn="12-345-67-890",
        county="Fulton",
        acreage="5.0",
        offer_amount="25000"
    )
