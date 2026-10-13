@echo off
rem ---------------------------------------------------------------
rem  Masaustune tek tiklamali kisayol olusturur. Bir kez calistirin.
rem ---------------------------------------------------------------
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0masaustu_kisayolu.ps1"
if errorlevel 1 (
    echo.
    echo Kisayol olusturulamadi. Yukaridaki mesaji okuyun.
    pause
)
