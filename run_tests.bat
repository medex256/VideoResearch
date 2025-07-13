@echo off
echo Running tests for Research Video Portal...

REM Install necessary test dependencies if needed
pip install -q pytest pytest-flask pytest-cov

REM Run tests with coverage
echo.
echo Running basic tests...
python -m pytest

echo.
echo Running tests with coverage report...
python -m pytest --cov=. --cov-report=term-missing

REM Run only API tests if specified
if "%1"=="api" (
    echo.
    echo Running API tests only...
    python -m pytest tests/test_api_endpoints.py tests/test_video_api.py tests/test_categories_api.py -v
)

REM Run with HTML coverage report if specified
if "%1"=="html" (
    echo.
    echo Generating HTML coverage report...
    python -m pytest --cov=. --cov-report=html
    echo HTML report generated in 'htmlcov' directory
)

echo.
echo Tests completed.
pause
