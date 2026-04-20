#!/bin/bash
# Get Cognito token and hit production API
TOKEN=$(aws --profile ragnarok cognito-idp admin-initiate-auth \
  --user-pool-id us-east-1_7WksfnG6T \
  --client-id 7lbcmb2cg1o9c0n2s4tuvftjdk \
  --auth-flow ADMIN_USER_PASSWORD_AUTH \
  --auth-parameters 'USERNAME=gierlich2009@gmail.com,PASSWORD=FamilyMan33*1' \
  --query 'AuthenticationResult.IdToken' --output text)

echo "Token length: ${#TOKEN}"
echo ""
echo "=== Opportunities ==="
curl -s -H "Authorization: Bearer $TOKEN" \
  https://58y8e35x26.execute-api.us-east-1.amazonaws.com/api/opportunities | python3 -m json.tool 2>&1 | head -60
