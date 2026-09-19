@echo off
echo ==============================================================================
echo Building Supermarket Shelf Price Tag Generator Standalone Windows Executable
echo ==============================================================================

set PYTHON_CMD=python
where %PYTHON_CMD% >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) else (
        echo [ERROR] Python was not found in PATH or standard installation directory.
        pause
        exit /b 1
    )
)

echo [1/3] Verifying and installing requirements...
%PYTHON_CMD% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/3] Compiling executable with PyInstaller...
%PYTHON_CMD% -m PyInstaller price_tag_generator.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller compilation failed.
    pause
    exit /b 1
)

echo [3/3] Build complete!
echo Executable is located at: dist\PriceTagGenerator.exe
echo ==============================================================================
pause
