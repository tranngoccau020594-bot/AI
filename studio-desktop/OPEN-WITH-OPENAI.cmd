@echo off
setlocal
set "STUDIO_APP_DIR=%~dp0"
if not exist "%STUDIO_APP_DIR%Independent Studio.exe" (
  echo Extract the entire app ZIP first. Keep this CMD beside Independent Studio.exe.
  pause
  exit /b 1
)
echo Close any running Independent Studio window before continuing.
echo The API key is used only for this launch and is not saved to a file.
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; $secret=Read-Host 'OpenAI API key (hidden input)' -AsSecureString; $pointer=[System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret); try { $env:STUDIO_API_KEY=[System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer); if ([string]::IsNullOrWhiteSpace($env:STUDIO_API_KEY)) { throw 'API key is empty' }; $env:STUDIO_API_BASE='https://api.openai.com/v1'; $env:STUDIO_IMAGE_MODEL='gpt-image-1'; Start-Process -FilePath (Join-Path $env:STUDIO_APP_DIR 'Independent Studio.exe') -WorkingDirectory $env:STUDIO_APP_DIR -Wait } finally { $env:STUDIO_API_KEY=$null; [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer); $secret.Dispose() }"
if errorlevel 1 (
  echo Startup failed. No API key was saved by this launcher.
  pause
  exit /b 1
)
endlocal
