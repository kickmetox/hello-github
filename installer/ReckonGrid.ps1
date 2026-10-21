# ReckonGrid starten. Andreas Meyer, ame@sellerbach.de
# Sichtbares Fenster. HttpListener, bei Fehlschlag eingebauter Socket-Server auf 127.0.0.1.
param(
  [string]$Root = '',
  [ValidateSet('auto', 'http', 'socket')]
  [string]$Server = 'auto'
)

$ErrorActionPreference = 'Stop'

function Resolve-AppRoot([string]$Hint) {
  if ($Hint) {
    $hintIndex = Join-Path $Hint 'index.html'
    if (Test-Path -LiteralPath $hintIndex) { return (Resolve-Path -LiteralPath $Hint).Path }
    return $null
  }
  $candidates = New-Object System.Collections.Generic.List[string]
  $candidates.Add((Join-Path $PSScriptRoot 'app'))
  $candidates.Add((Join-Path $PSScriptRoot 'dist'))
  $parent = Split-Path -Parent $PSScriptRoot
  if ($parent) {
    $candidates.Add((Join-Path $parent 'dist'))
    $candidates.Add((Join-Path $parent 'app'))
  }
  foreach ($candidate in $candidates) {
    if (-not $candidate) { continue }
    $index = Join-Path $candidate 'index.html'
    if (Test-Path -LiteralPath $index) {
      return (Resolve-Path -LiteralPath $candidate).Path
    }
  }
  return $null
}

function Get-MimeType([string]$path) {
  switch ([IO.Path]::GetExtension($path).ToLowerInvariant()) {
    '.html' { 'text/html; charset=utf-8' }
    '.htm' { 'text/html; charset=utf-8' }
    '.js' { 'text/javascript; charset=utf-8' }
    '.mjs' { 'text/javascript; charset=utf-8' }
    '.css' { 'text/css; charset=utf-8' }
    '.json' { 'application/json; charset=utf-8' }
    '.map' { 'application/json; charset=utf-8' }
    '.svg' { 'image/svg+xml' }
    '.png' { 'image/png' }
    '.jpg' { 'image/jpeg' }
    '.jpeg' { 'image/jpeg' }
    '.gif' { 'image/gif' }
    '.webp' { 'image/webp' }
    '.ico' { 'image/x-icon' }
    '.woff' { 'font/woff' }
    '.woff2' { 'font/woff2' }
    '.ttf' { 'font/ttf' }
    '.txt' { 'text/plain; charset=utf-8' }
    '.wasm' { 'application/wasm' }
    default { 'application/octet-stream' }
  }
}

function Resolve-StaticFile([string]$root, [string]$urlPath) {
  if ([string]::IsNullOrWhiteSpace($urlPath)) { $urlPath = '/' }
  $pathOnly = $urlPath
  $q = $pathOnly.IndexOf('?')
  if ($q -ge 0) { $pathOnly = $pathOnly.Substring(0, $q) }
  try { $rel = [Uri]::UnescapeDataString($pathOnly) } catch { return $null }
  $rel = ($rel -replace '\\', '/').TrimStart('/')
  if ($rel.IndexOf([char]0) -ge 0) { return $null }
  if ([string]::IsNullOrWhiteSpace($rel)) { $rel = 'index.html' }
  $rel = $rel -replace '/', [IO.Path]::DirectorySeparatorChar
  $rootFull = [IO.Path]::GetFullPath($root)
  $sep = [IO.Path]::DirectorySeparatorChar
  if (-not $rootFull.EndsWith($sep)) { $rootFull = $rootFull + $sep }
  try { $full = [IO.Path]::GetFullPath((Join-Path $root $rel)) } catch { return $null }
  if (-not $full.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)) { return $null }
  if (Test-Path -LiteralPath $full -PathType Container) {
    $index = Join-Path $full 'index.html'
    if (Test-Path -LiteralPath $index -PathType Leaf) { return $index }
    return $null
  }
  if (Test-Path -LiteralPath $full -PathType Leaf) { return $full }
  return $null
}

function Open-Browser([string]$url) {
  try {
    Start-Process $url
    return
  } catch {
    Write-Host "Browser konnte nicht automatisch geöffnet werden: $($_.Exception.Message)"
  }
  try {
    Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', 'start', '', $url) | Out-Null
  } catch {
    Write-Host "Bitte diese Adresse im Browser öffnen: $url"
  }
}

function Test-HttpDenied($err) {
  $ex = $err.Exception
  while ($ex) {
    if ($ex -is [System.Net.HttpListenerException]) {
      $code = 0
      if ($ex.PSObject.Properties['ErrorCode']) { $code = [int]$ex.ErrorCode }
      elseif ($ex.PSObject.Properties['NativeErrorCode']) { $code = [int]$ex.NativeErrorCode }
      if ($code -eq 5) { return $true }
    }
    $ex = $ex.InnerException
  }
  $msg = [string]$err.Exception.Message
  return $msg -match 'Access is denied|Zugriff verweigert|access denied'
}

function Start-HttpOnPort([int]$port) {
  $listener = New-Object System.Net.HttpListener
  $listener.Prefixes.Add("http://127.0.0.1:$port/")
  try {
    $listener.Start()
    return $listener
  } catch {
    try { $listener.Abort() } catch {}
    try { $listener.Close() } catch {}
    throw
  }
}

function Serve-HttpListener($listener, [string]$root, [string]$url) {
  Write-Host "ReckonGrid läuft auf $url"
  Write-Host 'Modus: HttpListener. Fenster schließen beendet die App.'
  Open-Browser $url
  try {
    while ($listener.IsListening) {
      $ctx = $null
      try { $ctx = $listener.GetContext() } catch { break }
      try {
        $rel = $ctx.Request.Url.LocalPath
        $file = Resolve-StaticFile $root $rel
        if (-not $file) {
          $ctx.Response.StatusCode = 404
          $ctx.Response.ContentType = 'text/plain; charset=utf-8'
          $bytes = [Text.Encoding]::UTF8.GetBytes('Nicht gefunden')
          Write-Host "404 $rel"
        } else {
          $ctx.Response.StatusCode = 200
          $ctx.Response.ContentType = Get-MimeType $file
          $bytes = [IO.File]::ReadAllBytes($file)
        }
        $ctx.Response.Headers['Cache-Control'] = 'no-cache'
        $ctx.Response.ContentLength64 = $bytes.Length
        if ($ctx.Request.HttpMethod -ne 'HEAD') {
          $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
        }
        $ctx.Response.OutputStream.Close()
      } catch {
        Write-Host "Anfrage fehlgeschlagen: $($_.Exception.Message)"
        try { $ctx.Response.Abort() } catch {}
      }
    }
  } finally {
    try { $listener.Stop() } catch {}
    try { $listener.Close() } catch {}
  }
}

function Read-RequestText($stream) {
  $stream.ReadTimeout = 8000
  $buffer = New-Object byte[] 4096
  $ms = New-Object System.IO.MemoryStream
  while ($ms.Length -lt 65536) {
    $text = [Text.Encoding]::ASCII.GetString($ms.ToArray())
    if ($text.Contains("`r`n`r`n")) { return $text }
    $n = 0
    try { $n = $stream.Read($buffer, 0, $buffer.Length) } catch { break }
    if ($n -le 0) { break }
    $ms.Write($buffer, 0, $n)
  }
  return [Text.Encoding]::ASCII.GetString($ms.ToArray())
}

function Send-SocketResponse($stream, [int]$status, [string]$reason, [string]$contentType, [byte[]]$body, [bool]$headOnly) {
  $header = "HTTP/1.1 $status $reason`r`nContent-Type: $contentType`r`nContent-Length: $($body.Length)`r`nConnection: close`r`nCache-Control: no-cache`r`n`r`n"
  $headerBytes = [Text.Encoding]::ASCII.GetBytes($header)
  $stream.Write($headerBytes, 0, $headerBytes.Length)
  if (-not $headOnly -and $body.Length -gt 0) {
    $stream.Write($body, 0, $body.Length)
  }
  $stream.Flush()
}

function Serve-Socket([System.Net.Sockets.TcpListener]$tcp, [string]$root, [string]$url) {
  Write-Host "ReckonGrid läuft auf $url"
  Write-Host 'Modus: Socket-Server (ohne HttpListener). Fenster schließen beendet die App.'
  Open-Browser $url
  try {
    while ($true) {
      $client = $null
      try { $client = $tcp.AcceptTcpClient() } catch { break }
      try {
        $client.ReceiveTimeout = 8000
        $client.SendTimeout = 8000
        $stream = $client.GetStream()
        $raw = Read-RequestText $stream
        $line = ''
        if ($raw) { $line = ($raw -split "`r`n", 2)[0] }
        if ($line -notmatch '^(GET|HEAD)\s+(\S+)') {
          $msg = [Text.Encoding]::UTF8.GetBytes('Methode nicht erlaubt')
          Send-SocketResponse $stream 405 'Method Not Allowed' 'text/plain; charset=utf-8' $msg $false
        } else {
          $headOnly = $Matches[1] -eq 'HEAD'
          $target = $Matches[2]
          if ($target -match '^https?://[^/]+(/.*)$') { $target = $Matches[1] }
          if ($target -notmatch '^/') { $target = '/' + $target }
          $file = Resolve-StaticFile $root $target
          if (-not $file) {
            $msg = [Text.Encoding]::UTF8.GetBytes('Nicht gefunden')
            Send-SocketResponse $stream 404 'Not Found' 'text/plain; charset=utf-8' $msg $headOnly
            Write-Host "404 $target"
          } else {
            $bytes = [IO.File]::ReadAllBytes($file)
            Send-SocketResponse $stream 200 'OK' (Get-MimeType $file) $bytes $headOnly
          }
        }
      } catch {
        Write-Host "Anfrage fehlgeschlagen: $($_.Exception.Message)"
      } finally {
        try { $client.Close() } catch {}
      }
    }
  } finally {
    try { $tcp.Stop() } catch {}
  }
}

function Start-SocketOnPort([int]$port) {
  $tcp = New-Object System.Net.Sockets.TcpListener ([System.Net.IPAddress]::Loopback, $port)
  $tcp.Start()
  return $tcp
}

try {
  $appRoot = Resolve-AppRoot $Root
  if (-not $appRoot) {
    Write-Host 'Keine gebaute App gefunden (index.html fehlt).'
    Write-Host 'Erwartet wird der Ordner app\ neben diesem Skript oder dist\ im Projekt.'
    Write-Host 'index.html nicht doppelklicken: der Browser blockiert Module über file://.'
    Write-Host 'Entwicklung ohne fertigen Build:'
    Write-Host '  npm install'
    Write-Host '  npm run dev'
    Write-Host 'Die Entwicklungsumgebung liegt auf http://127.0.0.1:5173/'
    exit 1
  }

  $httpListener = $null
  $httpError = $null
  $chosenPort = 0
  if ($Server -ne 'socket') {
    for ($port = 4173; $port -le 4189; $port++) {
      try {
        $httpListener = Start-HttpOnPort $port
        $chosenPort = $port
        break
      } catch {
        $httpError = $_
        if (Test-HttpDenied $_) {
          Write-Host 'HttpListener verweigert 127.0.0.1 ohne URL-Freigabe. Es wird der eingebaute Socket-Server verwendet.'
          break
        }
      }
    }
  }

  if ($httpListener) {
    Serve-HttpListener $httpListener $appRoot "http://127.0.0.1:$chosenPort/"
    exit 0
  }

  if ($Server -eq 'http') {
    $detail = 'HttpListener konnte nicht gestartet werden.'
    if ($httpError) { $detail = $httpError.Exception.Message }
    throw $detail
  }

  if ($Server -eq 'auto' -and $httpError -and -not (Test-HttpDenied $httpError)) {
    Write-Host "HttpListener nicht verfügbar ($($httpError.Exception.Message)). Es wird der eingebaute Socket-Server verwendet."
  }

  $tcp = $null
  $socketError = $null
  for ($port = 4173; $port -le 4189; $port++) {
    try {
      $tcp = Start-SocketOnPort $port
      $chosenPort = $port
      break
    } catch {
      $socketError = $_
    }
  }
  if (-not $tcp) {
    $detail = 'Kein freier Port zwischen 4173 und 4189.'
    if ($socketError) { $detail = "$detail $($socketError.Exception.Message)" }
    throw $detail
  }
  Serve-Socket $tcp $appRoot "http://127.0.0.1:$chosenPort/"
} catch {
  Write-Host ''
  Write-Host "FEHLER: $($_.Exception.Message)" -ForegroundColor Red
  if ($_.ScriptStackTrace) { Write-Host $_.ScriptStackTrace }
  exit 1
}
