@echo off
setlocal
cd /d "%~dp0"

where cloudflared >nul 2>&1
if errorlevel 1 (
  echo ERRO: cloudflared nao foi encontrado no PATH.
  exit /b 1
)

taskkill /IM cloudflared.exe /F >nul 2>&1

powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000 -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if not errorlevel 1 goto servidor_pronto

powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath python -ArgumentList '-m uvicorn server:app --host 127.0.0.1 --port 8000' -WorkingDirectory '%CD%' -RedirectStandardOutput '%CD%\server.stdout.log' -RedirectStandardError '%CD%\server.stderr.log'"

echo Aguardando o servidor local...
ping 127.0.0.1 -n 11 >nul

:servidor_pronto
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000 -TimeoutSec 5; if ($r.StatusCode -ne 200) { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
  echo ERRO: o servidor nao iniciou. Consulte server.stderr.log.
  exit /b 1
)

del /q tunnel.stdout.log tunnel.stderr.log >nul 2>&1
powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath cloudflared -ArgumentList 'tunnel --url http://127.0.0.1:8000 --no-autoupdate' -WorkingDirectory '%CD%' -RedirectStandardOutput '%CD%\tunnel.stdout.log' -RedirectStandardError '%CD%\tunnel.stderr.log'"

echo Aguardando o Cloudflare gerar o endereco publico...
ping 127.0.0.1 -n 9 >nul
powershell -NoProfile -Command "$m = Select-String -Path tunnel.stderr.log -Pattern 'https://[-a-z0-9]+\.trycloudflare\.com' -AllMatches; if ($m) { Write-Host ''; Write-Host 'ENDERECO PUBLICO:' -ForegroundColor Green; Write-Host $m.Matches[0].Value -ForegroundColor Cyan } else { Write-Host 'O tunel nao iniciou. Consulte tunnel.stderr.log.' -ForegroundColor Red; exit 1 }"

echo.
echo O servidor e o tunel continuarao ativos em segundo plano.
pause
