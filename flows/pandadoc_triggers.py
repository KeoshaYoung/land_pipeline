"""
PandaDoc document generation flows.
Triggers Make webhooks to create Offer Letters and PSAs.
"""

from prefect import flow, task
from prefect.blocks.system import Secret
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any


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
    # Only try to parse JSON if response has content
    if response.text and response.text.strip():
        try:
            return response.json()
        except Exception:
            return {"status": "accepted", "status_code": response.status_code}
    else:
        return {"status": "accepted", "status_code": response.status_code}


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
    offer_expiry_days: int = 14
) -> Dict[str, Any]:
    """
    Create an Offer Letter via PandaDoc.
    
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
        
    Returns:
        Webhook response
    """
    print(f"Creating Offer Letter for {property_address}")
    
    # Get webhook URL from Prefect Secret
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
    
    print("✅ Offer Letter created successfully")
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
    offer_expiry_days: int = 14
) -> Dict[str, Any]:
    """
    Create a Purchase & Sale Agreement via PandaDoc.
    
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
        
    Returns:
        Webhook response
    """
    print(f"Creating PSA for {property_address}")
    
    # Get webhook URL from Prefect Secret
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
    
    print("✅ PSA created successfully")
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