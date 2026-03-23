import json
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VERIFICATION_TOKEN = "CPT-7k9mX2nQ8vL4pR6wH3jF5sY1tN0zB"
ENDPOINT_URL = "https://ragnarokgamez.com/api/webhooks/ebay/account-deletion"

def lambda_handler(event, context):
    logger.info(f"Request: {json.dumps(event)}")
    
    try:
        http_method = event.get('httpMethod', 'POST')
        
        if http_method == 'GET':
            query_params = event.get('queryStringParameters', {}) or {}
            challenge_code = query_params.get('challenge_code')
            
            if challenge_code:
                logger.info(f"eBay validation: {challenge_code}")
                hash_input = f"{challenge_code}{VERIFICATION_TOKEN}{ENDPOINT_URL}"
                response_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'challengeResponse': response_hash})
                }
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})
            }
        
        body = json.loads(event.get('body', '{}'))
        notification_id = body.get('notificationId')
        
        logger.info(f"Notification: {notification_id}")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'success', 'notificationId': notification_id})
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'error', 'message': str(e)})
        }
