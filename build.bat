@echo off
echo ================================
echo Building calculation_engine.exe
echo ================================
echo.

REM Clean previous builds
echo Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist calculation_engine.spec del calculation_engine.spec
if exist calculation_engine.exe del calculation_engine.exe
echo.

REM Build the executable to main folder
echo Building executable...
pyinstaller --onefile --distpath . --hidden-import=encodings calculation_engine.py
echo.

REM Check if build was successful
if exist calculation_engine.exe (
    echo ================================
    echo BUILD SUCCESSFUL!
    echo ================================
    echo Executable location: calculation_engine.exe
    echo.
    
    REM Clean up build artifacts
    echo Cleaning up build artifacts...
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist
    if exist calculation_engine.spec del calculation_engine.spec
    echo.
) else (
    echo ================================
    echo BUILD FAILED!
    echo ================================
    echo Check the errors above.
    echo.
)

pause