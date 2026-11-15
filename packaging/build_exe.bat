@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo ============================================================
echo   Z.O.S.M.A. Native Desktop HUD Builder (PyInstaller)
echo ============================================================
echo.

python -m PyInstaller --noconfirm --clean packaging\zosma.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    exit /b 1
)

echo.
echo [SUCCESS] Build complete: dist\ZOSMA_HUD\ZOSMA.exe
echo           To quick-sync updated modules/ or data/ without full rebuild:
echo           python packaging\sync_updates.py
endlocal
