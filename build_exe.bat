@echo off
setlocal
setlocal enabledelayedexpansion

set APP_NAME=GameChanger
set VERSION_FILE=src\version.py
set APP_VERSION=0.0.0
if "%SIGN_TIMESTAMP_URL%"=="" set SIGN_TIMESTAMP_URL=http://timestamp.digicert.com

if exist "%VERSION_FILE%" (
  for /f "usebackq delims=" %%v in (`powershell -NoProfile -Command "(Get-Content '%VERSION_FILE%' | Select-String '__version__').Line -replace '.*\"([^\"]+)\".*','$1'"`) do (
    if not "%%v"=="" set APP_VERSION=%%v
  )
)

for /f "tokens=1-4 delims=." %%a in ("%APP_VERSION%") do (
  set V1=%%a
  set V2=%%b
  set V3=%%c
  set V4=%%d
)
if "%V1%"=="" set V1=0
if "%V2%"=="" set V2=0
if "%V3%"=="" set V3=0
if "%V4%"=="" set V4=0

where py >nul 2>&1
if %errorlevel% neq 0 (
  echo Python bulunamadi. Lutfen Python kur ve PATH'e ekle.
  pause
  exit /b 1
)

py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m pip install pyinstaller

if not exist build mkdir build

set VERSION_INFO_FILE=build\version_info.txt
(
  echo # UTF-8
  echo VSVersionInfo^
  echo (^\
  echo   ffi=FixedFileInfo^
  echo   (^\
  echo     filevers=^(!V1!, !V2!, !V3!, !V4!^),^
  echo     prodvers=^(!V1!, !V2!, !V3!, !V4!^),^
  echo     mask=0x3f,^
  echo     flags=0x0,^
  echo     OS=0x40004,^
  echo     fileType=0x1,^
  echo     subtype=0x0,^
  echo     date=^(0, 0^)^\
  echo     ^),^
  echo   kids=[^
  echo     StringFileInfo^
  echo     ^([^
  echo       StringTable^
  echo       ^('040904B0',^
  echo         [StringStruct^('CompanyName', 'GameChanger OSS'^),^
  echo         StringStruct^('FileDescription', 'GameChanger - Windows game performance helper'^),^
  echo         StringStruct^('FileVersion', '%APP_VERSION%'^),^
  echo         StringStruct^('InternalName', '%APP_NAME%'^),^
  echo         StringStruct^('LegalCopyright', 'MIT License'^),^
  echo         StringStruct^('OriginalFilename', '%APP_NAME%.exe'^),^
  echo         StringStruct^('ProductName', '%APP_NAME%'^),^
  echo         StringStruct^('ProductVersion', '%APP_VERSION%'^)]^
  echo       ^)^\
  echo     ]^\
  echo   ^),^
  echo   VarFileInfo^([VarStruct^('Translation', [1033, 1200]^)]^)^\
  echo )
) > "%VERSION_INFO_FILE%"

set ICON_ARGS=
if exist assets\app.ico (
  set ICON_ARGS=--icon assets\app.ico
  echo Ikon bulundu: assets\app.ico
) else (
  echo Ikon bulunamadi, varsayilan ikon kullaniliyor.
)

py -m PyInstaller --clean --onefile --noconsole --name %APP_NAME% --version-file "%VERSION_INFO_FILE%" %ICON_ARGS% src\main.py

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
