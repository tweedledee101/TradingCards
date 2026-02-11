@echo off
REM Apply database migration for inventory system

echo Applying database migration...

REM Apply migration
psql -U postgres -d trading_cards -f backend\models\migration_001.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Migration applied successfully!
    echo.
    echo New tables created:
    echo   - inventory
    echo   - inventory_sales
    echo   - watchlist
    echo.
    echo Updated tables:
    echo   - active_listings ^(added listing_title, listing_url^)
    echo   - price_trends ^(added momentum_score^)
    echo.
    echo Restart your API server to use new features:
    echo    python -m backend.api.run
) else (
    echo.
    echo Migration failed. Check the error messages above.
    exit /b 1
)
