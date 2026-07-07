@echo off
echo.
echo  =========================================
echo   11:11:11 EVOXU  -  Backend Setup
echo  =========================================
echo.

REM Copy .env if not present
if not exist .env (
  copy .env.example .env
  echo  [1/5] Created .env from template
  echo        ^> Edit .env and set your DB_PASSWORD before continuing!
  echo.
  pause
) else (
  echo  [1/5] .env already exists
)

echo.
echo  [2/5] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
  echo  ERROR: pip install failed. Make sure Python and pip are installed.
  pause
  exit /b 1
)

echo.
echo  [3/5] Creating MySQL database...
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS evoxu_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo.
echo  [4/5] Creating and running database migrations...
python manage.py makemigrations resellers store
if %ERRORLEVEL% neq 0 (
  echo  ERROR: makemigrations failed. Check your models.
  pause
  exit /b 1
)
python manage.py migrate
if %ERRORLEVEL% neq 0 (
  echo  ERROR: Migrations failed. Check your .env DB settings.
  pause
  exit /b 1
)

echo.
echo  [5/5] Seeding demo data (Aravind, Sibi, Bhupan)...
python manage.py seed_demo
if %ERRORLEVEL% neq 0 (
  echo  ERROR: Seeding failed.
  pause
  exit /b 1
)

echo.
echo  [Bonus] Creating Django admin superuser...
echo         Username: admin  ^|  Password: Admin@1111  ^|  Email: admin@111-11-11.shop
set DJANGO_SUPERUSER_PASSWORD=Admin@1111
python manage.py createsuperuser --noinput --username admin --email admin@111-11-11.shop
if %ERRORLEVEL% neq 0 (
  echo  (Admin already exists — skipping)
)

echo.
echo  =========================================
echo   Setup complete!  Run start.bat to launch
echo  =========================================
echo.
pause
