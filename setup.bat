@echo off
REM Setup script for Windows

echo Setting up Trading Card Platform...
echo.

REM Check Python
python --version
echo.

REM Install dependencies
echo Installing Python dependencies...
pip install -r backend\requirements.txt

echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Configure .env: copy backend\.env.example backend\.env
echo   2. Setup database
echo   3. Test pipeline: python backend\test_pipeline.py
echo   4. Start API: python -m backend.api.run
echo.
pause
