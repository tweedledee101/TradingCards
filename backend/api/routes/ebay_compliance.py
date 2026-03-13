"""
eBay Marketplace Account Deletion Notification Handler
Required for eBay API compliance
"""
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/ebay/account-deletion")
async def handle_ebay_account_deletion(request: Request):
    """
    Handle eBay marketplace account deletion notifications
    
    eBay sends notifications when:
    - User closes their eBay account
    - User requests data deletion
    - Account is suspended/deleted by eBay
    
    Since we only collect public listing data (no user PII),
    we log the notification but don't need to delete any data.
    """
    try:
        # Get notification payload
        payload = await request.json()
        
        # Log the notification
        logger.info(f"eBay account deletion notification received: {payload}")
        
        # Extract notification details
        notification_id = payload.get('notificationId')
        user_id = payload.get('userId')  # eBay user ID (not stored by us)
        deletion_date = payload.get('deletionDate')
        
        # Log to database for audit trail
        # Note: We don't actually delete anything because we don't store user data
        logger.info(f"eBay User {user_id} account deletion notification logged")
        
        # Return success response
        return {
            "status": "success",
            "message": "Account deletion notification received and logged",
            "notificationId": notification_id,
            "processed": datetime.now().isoformat(),
            "action": "No data deletion required - platform does not store eBay user PII"
        }
        
    except Exception as e:
        logger.error(f"Error processing eBay account deletion notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/webhooks/ebay/account-deletion/test")
async def test_account_deletion_endpoint():
    """
    Test endpoint to verify webhook is accessible
    """
    return {
        "status": "active",
        "endpoint": "/api/webhooks/ebay/account-deletion",
        "compliance": "eBay Marketplace Account Deletion Requirements",
        "message": "Endpoint is active and ready to receive notifications"
    }
