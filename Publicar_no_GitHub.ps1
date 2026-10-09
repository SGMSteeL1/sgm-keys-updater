$ErrorActionPreference = 'Stop'
$remote = 'https://github.com/SGMSteeL1/sgm-keys-updater.git'
$destination = Join-Path (Get-Location) 'sgm-keys-updater-clone'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw 'Instale o Git para Windows (https://git-scm.com/downloads/win) antes de continuar.'
}
if (Test-Path $destination) {
  throw "A pasta $destination ja existe. Remova/renomeie antes de continuar."
}
& git clone $remote $destination
if ($LASTEXITCODE -ne 0) { throw 'Falha no git clone; confira login e acesso.' }
$paths = @('apply_sgm.py', '.github', 'tests', '.gitignore', 'README.md')
foreach ($relative in $paths) {
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) `
    -Destination (Join-Path $destination $relative) -Force -Recurse
}
& git -C $destination add --all
if ($LASTEXITCODE -ne 0) { throw 'Falha no git add.' }
& git -C $destination commit -m 'feat: initial SGM Keys Updater v2 build and CI'
if ($LASTEXITCODE -ne 0) { throw 'Falha no git commit. Configure user.name/user.email no Git.' }
& git -C $destination push origin HEAD:main
if ($LASTEXITCODE -ne 0) { throw 'Falha no git push. Entre na conta SGMSteeL1 ou conceda acesso ao repositorio.' }
Write-Host 'Publicado. Veja: https://github.com/SGMSteeL1/sgm-keys-updater/actions'
