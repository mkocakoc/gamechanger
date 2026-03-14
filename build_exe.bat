@echo off
setlocal

set APP_NAME=GameChanger
set VERSION_FILE=src\version.py
set APP_VERSION=0.0.0
if "%SIGN_TIMESTAMP_URL%"=="" set SIGN_TIMESTAMP_URL=http://timestamp.digicert.com

if exist "%VERSION_FILE%" (
  for /f "delims=" %%v in ('py -c "import sys; sys.path.insert(0, r'src'); import version; print(version.__version__)"') do set APP_VERSION=%%v
)

where py >nul 2>&1
if %errorlevel% neq 0 (
  echo Python bulunamadi. Lutfen Python kur ve PATH'e ekle.
  pause
  exit /b 1
)

py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m pip install pyinstaller

set ICON_ARGS=
if exist assets\app.ico (
  set ICON_ARGS=--icon assets\app.ico
  echo Ikon bulundu: assets\app.ico
) else (
  echo Ikon bulunamadi, varsayilan ikon kullaniliyor.
)

py -m PyInstaller --clean --onefile --noconsole --name %APP_NAME% %ICON_ARGS% src\main.py

if not exist dist\%APP_NAME%.exe (
  echo EXE olusmadi, build basarisiz.
  pause
  exit /b 1
)

if not "%SIGNTOOL_PATH%"=="" if not "%SIGN_CERT_FILE%"=="" (
  echo Dijital imzalama deneniyor...
  if "%SIGN_CERT_PASSWORD%"=="" (
    "%SIGNTOOL_PATH%" sign /f "%SIGN_CERT_FILE%" /fd SHA256 /tr "%SIGN_TIMESTAMP_URL%" /td SHA256 "dist\%APP_NAME%.exe"
  ) else (
    "%SIGNTOOL_PATH%" sign /f "%SIGN_CERT_FILE%" /p "%SIGN_CERT_PASSWORD%" /fd SHA256 /tr "%SIGN_TIMESTAMP_URL%" /td SHA256 "dist\%APP_NAME%.exe"
  )
)

powershell -NoProfile -Command "Get-FileHash 'dist\%APP_NAME%.exe' -Algorithm SHA256 | ForEach-Object { '{0} *{1}' -f $_.Hash, '%APP_NAME%.exe' } | Set-Content 'dist\SHA256SUMS.txt'"

echo.
echo EXE hazir: dist\%APP_NAME%.exe
echo SHA256 hazir: dist\SHA256SUMS.txt
echo Surum: %APP_VERSION%
pause
