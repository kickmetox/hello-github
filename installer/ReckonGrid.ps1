# ReckonGrid starten. Andreas Meyer, ame@sellerbach.de
$ErrorActionPreference = 'Stop'
$root = Join-Path $PSScriptRoot 'app'
if (-not (Test-Path (Join-Path $root 'index.html'))) {
  Write-Error "App-Dateien fehlen: $root"
}

function Get-Mime([string]$name) {
  switch ([IO.Path]::GetExtension($name).ToLowerInvariant()) {
    '.html' { 'text/html; charset=utf-8' }
    '.js' { 'text/javascript; charset=utf-8' }
    '.css' { 'text/css; charset=utf-8' }
    '.json' { 'application/json; charset=utf-8' }
    '.png' { 'image/png' }
    '.svg' { 'image/svg+xml' }
    '.ico' { 'image/x-icon' }
    '.woff2' { 'font/woff2' }
    default { 'application/octet-stream' }
  }
}

$listener = New-Object System.Net.HttpListener
$port = 4173
while ($port -lt 4190) {
  $prefix = "http://127.0.0.1:$port/"
  $listener.Prefixes.Clear()
  $listener.Prefixes.Add($prefix)
  try {
    $listener.Start()
    break
  } catch {
    $port++
  }
}
if (-not $listener.IsListening) { Write-Error 'Kein freier Port zwischen 4173 und 4189.' }

Start-Process $prefix
Write-Host "ReckonGrid läuft auf $prefix  (Fenster schließen beendet die App)"

try {
  while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $rel = [Uri]::UnescapeDataString($ctx.Request.Url.LocalPath.TrimStart('/'))
    if ([string]::IsNullOrWhiteSpace($rel)) { $rel = 'index.html' }
    $rel = $rel -replace '/', '\'
    $file = [IO.Path]::GetFullPath((Join-Path $root $rel))
    $rootFull = [IO.Path]::GetFullPath($root)
    if (-not $file.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path $file -PathType Leaf)) {
      $ctx.Response.StatusCode = 404
      $bytes = [Text.Encoding]::UTF8.GetBytes('Nicht gefunden')
    } else {
      $ctx.Response.StatusCode = 200
      $ctx.Response.ContentType = Get-Mime $file
      $bytes = [IO.File]::ReadAllBytes($file)
    }
    $ctx.Response.ContentLength64 = $bytes.Length
    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    $ctx.Response.Close()
  }
} finally {
  $listener.Stop()
}
