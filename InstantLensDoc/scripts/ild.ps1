# InstantLens Doc — PowerShell-Scripting 2.6.10
# Als CLI:
#   powershell -ExecutionPolicy Bypass -File .\scripts\ild.ps1 pages D:\dok.pdf
# Als Modul:
#   . .\scripts\ild.ps1
#   Get-IldPageCount D:\dok.pdf
#   New-IldLicenseKey -Email kunde@example.com

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$IldArgs
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $scriptDir
if (-not (Test-Path (Join-Path $Root "ild\__main__.py"))) {
    if (Test-Path (Join-Path $scriptDir "ild\__main__.py")) { $Root = $scriptDir }
    elseif (Test-Path "D:\AI_Temp\InstantLensDoc\ild\__main__.py") { $Root = "D:\AI_Temp\InstantLensDoc" }
}

function Get-IldPython {
    if ($env:ILD_PYTHON -and (Test-Path $env:ILD_PYTHON)) { return $env:ILD_PYTHON }
    $venvPy = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { return $venvPy }
    foreach ($c in @("py", "python", "python3")) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if ($cmd) { return $c }
    }
    throw "Python nicht gefunden. ILD_PYTHON setzen oder Python 3.10+ 64-Bit installieren."
}

function Invoke-Ild {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )
    $py = Get-IldPython
    $old = Get-Location
    try {
        Set-Location $Root
        & $py -m ild @Arguments
        return $LASTEXITCODE
    } finally {
        Set-Location $old
    }
}

function Get-IldPageCount {
    param([Parameter(Mandatory = $true)][string]$Path)
    Invoke-Ild @("pages", $Path) | Out-Host
}

function Get-IldInfo {
    param([Parameter(Mandatory = $true)][string]$Path, [string]$Password)
    $a = @("info", $Path, "--json")
    if ($Password) { $a += @("--password", $Password) }
    Invoke-Ild @a | Out-Host
}

function Export-IldPage {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$Page = 1,
        [Parameter(Mandatory = $true)][string]$Out,
        [int]$Dpi = 150
    )
    Invoke-Ild @("export", $Path, "--page", "$Page", "--out", $Out, "--dpi", "$Dpi") | Out-Host
}

function Invoke-IldOcr {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$Page,
        [string]$Lang = "deu+eng"
    )
    $a = @("ocr", $Path, "--lang", $Lang, "--json")
    if ($PSBoundParameters.ContainsKey("Page")) { $a += @("--page", "$Page") }
    Invoke-Ild @a | Out-Host
}

function Invoke-IldRedact {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$Out
    )
    $a = @("redact-apply", $Path)
    if ($Out) { $a += @("--out", $Out) }
    Invoke-Ild @a | Out-Host
}

function Add-IldShape {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$Page = 1,
        [Parameter(Mandatory = $true)][string]$Type,
        [double]$X,
        [double]$Y,
        [double]$Width,
        [double]$Height,
        [string]$Color = "#2980B9",
        [string]$Fill = "",
        [double]$Stroke = 2,
        [switch]$Filled
    )
    $a = @("ann-shape", $Path, "--page", "$Page", "--type", $Type, "--x", "$X", "--y", "$Y", "--width", "$Width", "--height", "$Height", "--color", $Color, "--stroke", "$Stroke")
    if ($Fill) { $a += @("--fill", $Fill) }
    if ($Filled) { $a += "--filled" }
    Invoke-Ild @a | Out-Host
}

function Add-IldStamp {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Text,
        [int]$Page = 1,
        [double]$X = 72,
        [double]$Y = 72,
        [switch]$Date
    )
    $a = @("ann-stamp", $Path, "--page", "$Page", "--text", $Text, "--x", "$X", "--y", "$Y")
    if ($Date) { $a += "--date" }
    Invoke-Ild @a | Out-Host
}

function Add-IldParagraphHighlight {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$Page = 1,
        [double]$X,
        [double]$Y,
        [double]$Width,
        [double]$Height
    )
    Invoke-Ild @("ann-highlight-para", $Path, "--page", "$Page", "--x", "$X", "--y", "$Y", "--width", "$Width", "--height", "$Height") | Out-Host
}

function Get-IldStamps {
    Invoke-Ild @("stamp-list", "--json") | Out-Host
}

function Invoke-IldAutoFormat {
    param(
        [string]$Path,
        [string]$Text,
        [string]$Out,
        [int]$MaxLevel = 3,
        [switch]$NoToc
    )
    if ($Text) {
        Invoke-Ild @("--json", "auto-format", "--text", $Text) | Out-Host
        return
    }
    if (-not $Path) { throw "Path oder Text erforderlich" }
    $a = @("--json", "auto-format", $Path, "--max-level", "$MaxLevel")
    if ($Out) { $a += @("--out", $Out) }
    if ($NoToc) { $a += "--no-toc" }
    Invoke-Ild @a | Out-Host
}

function Update-IldToc {
    param(
        [string]$Path,
        [string]$Text,
        [string]$Out,
        [int]$MaxLevel = 3,
        [switch]$DryRun
    )
    $a = @("--json", "toc", "--max-level", "$MaxLevel")
    if ($Text) { $a += @("--text", $Text) }
    elseif ($Path) { $a += @($Path) }
    else { throw "Path oder Text erforderlich" }
    if ($Out) { $a += @("--out", $Out) }
    if ($DryRun) { $a += "--dry-run" }
    Invoke-Ild @a | Out-Host
}

function Get-IldSystemFonts {
    param([switch]$Files)
    $a = @("fonts")
    if ($Files) { $a += "--files" }
    Invoke-Ild @a | Out-Host
}

function Get-IldStylePresets {
    Invoke-Ild @("--json", "styles") | Out-Host
}

function Invoke-IldFindReplace {
    param(
        [string]$Path,
        [string]$Text,
        [Parameter(Mandatory = $true)][string]$Find,
        [Parameter(Mandatory = $true)][string]$Replace,
        [switch]$CaseSensitive,
        [int]$Count = 0,
        [int]$Max = 50
    )
    $a = @("--json", "find-replace", "--find", $Find, "--replace", $Replace)
    if ($Text) { $a += @("--text", $Text) }
    elseif ($Path) { $a += @($Path) }
    else { throw "Path oder Text erforderlich" }
    if ($CaseSensitive) { $a += "--case" }
    if ($Count -gt 0) { $a += @("--count", "$Count") }
    if ($Max -gt 0) { $a += @("--max", "$Max") }
    Invoke-Ild @a | Out-Host
}

function Merge-IldPdf {
    param(
        [Parameter(Mandatory = $true)][string[]]$Path,
        [Parameter(Mandatory = $true)][string]$Out
    )
    $a = @("merge") + $Path + @("--out", $Out)
    Invoke-Ild @a | Out-Host
}

function Split-IldPdf {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$OutDir
    )
    Invoke-Ild @("split", $Path, "--out-dir", $OutDir) | Out-Host
}

function New-IldLicenseKey {
    param(
        [Parameter(Mandatory = $true)][string]$Email,
        [int]$Days
    )
    $a = @("license", "generate", $Email)
    if ($PSBoundParameters.ContainsKey("Days")) { $a += @("--days", "$Days") }
    Invoke-Ild @a | Out-Host
}

function Test-IldLicenseKey {
    param([Parameter(Mandatory = $true)][string]$Key)
    Invoke-Ild @("license", "verify", $Key, "--json") | Out-Host
}

function Get-IldLicenseStatus {
    Invoke-Ild @("license", "status", "--json") | Out-Host
}

# Direkter CLI-Aufruf (nicht dot-sourced)
$isDotSourced = $MyInvocation.InvocationName -eq "." -or $MyInvocation.Line -match "^\s*\.\s+"
if (-not $isDotSourced) {
    $pass = @()
    if ($Command) { $pass += $Command }
    if ($IldArgs) { $pass += $IldArgs }
    if ($pass.Count -eq 0) { $pass = @("--help") }
    $code = Invoke-Ild @pass
    exit $code
}
