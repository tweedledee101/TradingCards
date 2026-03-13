@echo off
REM Deploy eBay Compliance Lambda to AWS
REM Usage: deploy-ebay-compliance.bat <hosted-zone-id>

setlocal

set STACK_NAME=cardpulse-ebay-compliance
set TEMPLATE_FILE=aws\cloudformation\ebay-compliance-lambda.yaml
set REGION=us-east-1

if "%1"=="" (
    echo Usage: deploy-ebay-compliance.bat ^<hosted-zone-id^>
    echo.
    echo Find your Hosted Zone ID:
    echo   aws route53 list-hosted-zones --query "HostedZones[?Name==`jgaffiliated.com.`].Id" --output text
    exit /b 1
)

set HOSTED_ZONE_ID=%1

echo Deploying eBay Compliance Lambda...
echo    Stack: %STACK_NAME%
echo    Region: %REGION%
echo    Domain: cardpulse.jgaffiliated.com
echo.

aws cloudformation deploy ^
    --template-file %TEMPLATE_FILE% ^
    --stack-name %STACK_NAME% ^
    --parameter-overrides DomainName=cardpulse.jgaffiliated.com HostedZoneId=%HOSTED_ZONE_ID% ^
    --capabilities CAPABILITY_NAMED_IAM ^
    --region %REGION%

if %ERRORLEVEL% neq 0 (
    echo Deployment failed!
    exit /b 1
)

echo.
echo Deployment complete!
echo.

echo Stack Outputs:
aws cloudformation describe-stacks ^
    --stack-name %STACK_NAME% ^
    --region %REGION% ^
    --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" ^
    --output table

echo.
echo eBay Compliance Endpoint:
aws cloudformation describe-stacks ^
    --stack-name %STACK_NAME% ^
    --region %REGION% ^
    --query "Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue" ^
    --output text

echo.
echo Next Steps:
echo    1. Copy the API endpoint URL above
echo    2. Go to eBay Developer Portal
echo    3. Configure marketplace account deletion notification endpoint
echo    4. Test with: curl https://cardpulse.jgaffiliated.com/api/webhooks/ebay/account-deletion
