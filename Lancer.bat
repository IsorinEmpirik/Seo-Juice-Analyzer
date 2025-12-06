@echo off
title SEO Juice Analyzer

echo.
echo ============================================================
echo           SEO Juice Analyzer - Demarrage
echo ============================================================
echo.

:: Se placer dans le dossier du script
cd /d "%~dp0"

:: Verifier que le venv existe
if not exist "venv\Scripts\python.exe" (
    echo [ERREUR] L'environnement virtuel n'existe pas.
    echo Veuillez d'abord executer: python -m venv venv
    echo Puis: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/3] Environnement virtuel detecte...

:: Attendre 2 secondes puis ouvrir le navigateur
echo [2/3] Ouverture du navigateur dans 2 secondes...
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Lancer l'application directement avec le python du venv
echo [3/3] Demarrage du serveur Flask...
echo.
echo ============================================================
echo   L'application est accessible sur : http://localhost:5000
echo   Appuyez sur CTRL+C pour arreter le serveur
echo ============================================================
echo.

venv\Scripts\python.exe run.py

:: En cas d'erreur
if errorlevel 1 (
    echo.
    echo [ERREUR] Le serveur s'est arrete de maniere inattendue.
    pause
)
