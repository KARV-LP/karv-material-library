param(
    [Parameter(Mandatory = $true)]
    [string]$ZipPath
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$zip = (Resolve-Path $ZipPath).Path
$temp = Join-Path $env:TEMP "karv-web-assets-initial"

if (Test-Path $temp) {
    Remove-Item $temp -Recurse -Force
}

Expand-Archive -Path $zip -DestinationPath $temp -Force

$targets = @{
    "toledo-51-escama-preto" = "fabrics/wiler-k/toledo/toledo-51-escama-preto"
    "croma-05-pet-friendly-musgo" = "fabrics/wiler-k/all-colours/croma-05-pet-friendly-musgo"
    "milano-02-bege" = "fabrics/wiler-k/milano/milano-02-bege"
}

foreach ($material in $targets.Keys) {
    $source = Join-Path $temp $material
    $target = Join-Path $repoRoot $targets[$material]

    if (-not (Test-Path $source)) {
        throw "Pasta ausente no pacote: $material"
    }

    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Copy-Item (Join-Path $source "base-color.webp") $target -Force
    Copy-Item (Join-Path $source "preview.webp") $target -Force
}

$catalogPath = Join-Path $repoRoot "catalog/fabrics.json"
$catalog = Get-Content $catalogPath -Raw | ConvertFrom-Json

foreach ($item in $catalog.items) {
    $item.asset_status = "published_in_repository"
    $item.ready_for_configurator = $true
}

$catalog | ConvertTo-Json -Depth 20 | Set-Content $catalogPath -Encoding utf8

Push-Location $repoRoot
try {
    git add fabrics catalog/fabrics.json scripts/publish-initial-assets.ps1

    if (-not (git diff --cached --quiet)) {
        git commit -m "feat: publish initial web fabric assets"
        git push origin feat/publish-initial-web-assets
    }
    else {
        Write-Host "Nenhuma alteração pendente."
    }
}
finally {
    Pop-Location
    Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Assets publicados na branch feat/publish-initial-web-assets."
