@echo off
rem ---------------------------------------------------------------
rem  Indirilenler Duzenleyici - arayuzu acan baslatici
rem
rem  Onceki surumlerde masaustu kisayolu kullanin; bu dosya
rem  Python kurulu degilse ya da PATH'te degilse kullanilir.
rem ---------------------------------------------------------------
cd /d "%~dp0"

rem gercek yorumlayiciyi sor (App Execution Alias sorununu onler)
set "PYEXE="
for /f "usebackq delims=" %%P in (`python -c "import sys,os;d=os.path.dirname(sys.executable);w=os.path.join(d,'pythonw.exe');print(w if os.path.exists(w) else sys.executable)" 2^>nul`) do set "PYEXE=%%P"

if not defined PYEXE (
    echo.
    echo   Python bulunamadi.
    echo   Lutfen https://www.python.org/downloads/ adresinden Python 3.8+ kurun
    echo   ve kurulumda "Add Python to PATH" secenegini isaretleyin.
    echo.
    pause
    exit /b 1
)

rem pythonw.exe konsul penceresi acmaz; yoksa python.exe ile devam et
if exist "%PYEXE%" (
    "%PYEXE%" "%~dp0indirilenler_duzenleyici.py"
) else (
    "%PYEXE:~0,-4%.exe" "%~dp0indirilenler_duzenleyici.py"
)
