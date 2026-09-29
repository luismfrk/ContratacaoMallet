@echo off
setlocal
cd /d "%~dp0"

where cloudflared >nul 2>&1
if errorlevel 1 (
  echo ERRO: cloudflared nao foi encontrado no PATH.
  exit /b 1
)

rem Quick Tunnels geram um endereco temporario. Reinicie somente o tunel desta aplicacao.
powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cloudflared.exe' -and $_.CommandLine -like '*http://127.0.0.1:8000*' }; $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000 -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if not errorlevel 1 goto servidor_pronto

powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath python -ArgumentList '-m uvicorn server:app --host 127.0.0.1 --port 8000' -WorkingDirectory '%CD%' -RedirectStandardOutput '%CD%\server.stdout.log' -RedirectStandardError '%CD%\server.stderr.log'"

echo Aguardando o servidor local...
powershell -NoProfile -Command "$ok = $false; for ($i = 0; $i -lt 45; $i++) { try { $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 2; if ($r.StatusCode -eq 200) { $ok = $true; break } } catch {}; Start-Sleep -Seconds 1 }; if (-not $ok) { exit 1 }"
if errorlevel 1 (
  echo ERRO: o servidor nao iniciou. Consulte server.stderr.log.
  exit /b 1
)

:servidor_pronto
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 5; if ($r.StatusCode -ne 200) { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
  echo ERRO: o servidor nao iniciou. Consulte server.stderr.log.
  exit /b 1
)

del /q tunnel.stdout.log tunnel.stderr.log >nul 2>&1
powershell -NoProfile -Command "$ErrorActionPreference = 'Stop'; $root = (Get-Location).Path; $log = Join-Path $root 'tunnel.stderr.log'; $urlFile = Join-Path $root 'cloudflare-url.txt'; Remove-Item $urlFile -Force -ErrorAction SilentlyContinue; $p = Start-Process -WindowStyle Hidden -PassThru -FilePath cloudflared -ArgumentList @('tunnel', '--protocol', 'http2', '--url', 'http://127.0.0.1:8000', '--no-autoupdate') -WorkingDirectory $root -RedirectStandardOutput (Join-Path $root 'tunnel.stdout.log') -RedirectStandardError $log; $url = $null; for ($i = 0; $i -lt 60; $i++) { if ($p.HasExited) { Write-Host 'cloudflared encerrou inesperadamente. Consulte tunnel.stderr.log.' -ForegroundColor Red; exit 1 }; if (Test-Path $log) { $text = Get-Content -Raw $log -ErrorAction SilentlyContinue; if ($text -match 'https://[-a-z0-9]+\.trycloudflare\.com') { $url = $Matches[0]; break } }; Start-Sleep -Seconds 1 }; if (-not $url) { Write-Host 'O Cloudflare nao forneceu um endereco em 60 segundos. Consulte tunnel.stderr.log.' -ForegroundColor Red; exit 1 }; Set-Content -Path $urlFile -Value $url -Encoding ascii; Write-Host ''; Write-Host 'ENDERECO PUBLICO ATUAL:' -ForegroundColor Green; Write-Host $url -ForegroundColor Cyan; Write-Host 'Endereco salvo em cloudflare-url.txt.' -ForegroundColor Gray"
if errorlevel 1 exit /b 1

echo.
echo O servidor e o tunel continuam ativos em segundo plano.
echo Quick Tunnel usa endereco temporario: ele muda quando o tunel e reiniciado.
pause
