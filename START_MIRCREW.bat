@echo off
setlocal enabledelayedexpansion
title MIRCREW DASHBOARD
cls

:: --- COLORI ---
set "cyan=[96m"
set "red=[91m"
set "yellow=[93m"
set "reset=[0m"

:: --- POSIZIONAMENTO CMD A SINISTRA (Metodo Ultra-Compatibile) ---
:: Ridimensiona la finestra
mode con: cols=90 lines=32
:: La sposta a sinistra usando un comando PowerShell piu semplice
powershell -command "$ws = New-Object -ComObject wscript.shell; $null = $ws.AppActivate('MIRCREW DASHBOARD'); Sleep -m 200; $ws.SendKeys('%{LEFT}')"

echo %cyan%
echo  __  __ ___ ____   ____ ____  _______        __
echo ^|  \/  ^|_ _^|  _ \ / ___^|  _ \^| ____\ \      / /
echo ^| ^|\/^| ^|^| ^|^| ^|_) ^| ^|   ^| ^|_) ^|  _^|  \ \ /\ / / 
echo ^| ^|  ^| ^|^| ^|^|  _ ^< ^| ^|___^|  _ <^| ^|___  \ V  V /  
echo ^|_^|  ^|_^|___^|_^| \_\\____^|_^| \_\_____^|  \_/\_/   
echo.
echo %reset%

:: --- 1. VERIFICA FILE ---
if not exist "mircrew_manager.py" (
    echo %red%[!] ERRORE: mircrew_manager.py non trovato nella cartella.%reset%
    pause && exit
)
if not exist "templates\index.html" (
    echo %red%[!] ERRORE: Cartella templates o index.html mancante.%reset%
    pause && exit
)

:: --- 2. CONTROLLO LIBRERIE ---
echo [*] Controllo librerie in corso...
pip install flask requests playwright flask-cors >nul 2>&1
python -m playwright install chromium >nul 2>&1

:: --- 3. KILL CHROME E AVVIO DEBUG ---
taskkill /F /IM chrome.exe /T >nul 2>&1
set "CHROME_DATA=%LOCALAPPDATA%\MirCrew_Manager_Data"

echo %yellow%[*] Avvio Chrome Debug a destra...%reset%
:: Lanciamo Chrome forzando posizione e dimensione
start chrome.exe --remote-debugging-port=9222 --user-data-dir="%CHROME_DATA%" "https://mircrew-releases.org/ucp.php?mode=login" --window-position=960,0 --window-size=960,1040 --new-window

echo.
echo %cyan%========================================================
echo  1. Fai il LOGIN su MirCrew (finestra a destra)
echo  2. Spunta 'Loggami automaticamente'
echo  3. Quando vedi la Home, premi un tasto qui sotto
echo ========================================================%reset%
echo.
pause

:: --- 4. AVVIO SERVER E SITO ---
echo %yellow%[*] Lancio interfaccia e server...%reset%
start http://127.0.0.1:5000

:: Esecuzione Python (senza nascondere errori stavolta)
python mircrew_manager.py

if %errorlevel% neq 0 (
    echo.
    echo %red%[!] Il server si e fermato. Controlla i messaggi sopra.%reset%
    pause
)