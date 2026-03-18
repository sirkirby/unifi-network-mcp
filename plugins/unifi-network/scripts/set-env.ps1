# Merge environment variables into .claude/settings.json
# Usage: set-env.ps1 KEY1=VALUE1 KEY2=VALUE2 ...
#
# Creates .claude/settings.json if it doesn't exist.
# Merges into existing "env" object without overwriting other keys.

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$KeyValuePairs
)

if (-not $KeyValuePairs -or $KeyValuePairs.Count -eq 0) {
    Write-Error "Usage: set-env.ps1 KEY1=VALUE1 KEY2=VALUE2 ..."
    exit 1
}

# Parse key=value pairs
$newVars = @{}
foreach ($pair in $KeyValuePairs) {
    $eqIndex = $pair.IndexOf('=')
    if ($eqIndex -lt 1) {
        Write-Error "Invalid argument '$pair'. Expected KEY=VALUE format."
        exit 1
    }
    $key = $pair.Substring(0, $eqIndex)
    $value = $pair.Substring($eqIndex + 1)
    $newVars[$key] = $value
}

$settingsFile = ".claude/settings.local.json"

# Ensure .claude directory exists
$dir = Split-Path $settingsFile -Parent
if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

# Read existing settings or start fresh
if (Test-Path $settingsFile) {
    try {
        $settings = Get-Content $settingsFile -Raw | ConvertFrom-Json -AsHashtable
    } catch {
        $settings = @{}
    }
} else {
    $settings = @{}
}

# Ensure env object exists
if (-not $settings.ContainsKey('env')) {
    $settings['env'] = @{}
}

# Merge new vars
foreach ($key in $newVars.Keys) {
    $settings['env'][$key] = $newVars[$key]
}

# Write back with formatting
$json = $settings | ConvertTo-Json -Depth 10
Set-Content -Path $settingsFile -Value $json -Encoding UTF8

# Report what was set (mask sensitive values)
foreach ($key in $newVars.Keys) {
    $value = $newVars[$key]
    if ($value.Length -gt 4 -and -not ($key -match '_(HOST|PORT|SITE)$') -and $value -ne 'true' -and $value -ne 'false') {
        $display = $value.Substring(0, 2) + '***' + $value.Substring($value.Length - 2)
    } else {
        $display = $value
    }
    Write-Host "  $key = $display"
}

Write-Host ""
Write-Host "Saved to $settingsFile"
