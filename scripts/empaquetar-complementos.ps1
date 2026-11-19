# Nombre: empaquetar-complementos.ps1
# Descripción: Arma kit\complementos (fuera de Git) con los dos complementos de Home Assistant OS listos para copiar a \\<IP de la Pi>\addons: accesia_base tal cual y accesia_servidor con el código del servidor, el SQL del contrato, consentimiento.md, la web compilada y los modelos de cara (D-22).
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-18
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio, en PowerShell (también con pwsh en Linux, como en la CI):
#   .\scripts\empaquetar-complementos.ps1
#
# La web compilada y los modelos salen de las etapas web y modelos de servidor\Dockerfile, las mismas de la imagen
# del servidor: solo hace falta Docker, ni Node ni uv. Sale con código 1 si algo falla.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$complementos = Join-Path $raiz 'complementos'
$kit = Join-Path (Join-Path $raiz 'kit') 'complementos'
$dockerfile = Join-Path (Join-Path $raiz 'servidor') 'Dockerfile'
# Del servidor solo va lo que necesita la imagen: sin pruebas, scripts, .venv ni cachés.
$delServidor = @('pyproject.toml', 'uv.lock', 'README.md', 'alembic.ini', 'accesia', 'migraciones')

function Sacar-DeEtapa([string]$Etapa, [string]$Ruta, [string]$Destino) {
    $imagen = "accesia-empaquetar-$Etapa"
    Write-Host "== Etapa $Etapa de servidor/Dockerfile" -ForegroundColor Cyan
    & docker build --target $Etapa -f $dockerfile -t $imagen $raiz
    if ($LASTEXITCODE -ne 0) {
        throw "Falló la etapa $Etapa de servidor/Dockerfile."
    }
    $contenedor = ((& docker create $imagen) -join '').Trim()
    try {
        New-Item -ItemType Directory -Force (Split-Path $Destino) | Out-Null
        & docker cp "${contenedor}:$Ruta" $Destino
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo copiar $Ruta de la etapa $Etapa."
        }
    } finally {
        & docker rm $contenedor | Out-Null
    }
}

try {
    # Windows PowerShell 5.1 convierte en errores lo que un programa escribe por stderr si la salida se redirige.
    # Desde aquí deciden los códigos de salida y los throw, no stderr.
    $ErrorActionPreference = 'Continue'
    if (Test-Path $kit) {
        Remove-Item $kit -Recurse -Force
    }
    New-Item -ItemType Directory -Force $kit | Out-Null

    Copy-Item (Join-Path $complementos 'accesia_base') $kit -Recurse

    $servidor = Join-Path $kit 'accesia_servidor'
    Copy-Item (Join-Path $complementos 'accesia_servidor') $kit -Recurse
    $codigo = Join-Path $servidor 'servidor'
    New-Item -ItemType Directory -Force $codigo | Out-Null
    foreach ($nombre in $delServidor) {
        Copy-Item (Join-Path (Join-Path $raiz 'servidor') $nombre) $codigo -Recurse
    }
    Get-ChildItem $codigo -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
    $specs = Join-Path $servidor 'specs'
    New-Item -ItemType Directory -Force (Join-Path $specs 'contratos') | Out-Null
    Copy-Item (Join-Path (Join-Path (Join-Path $raiz 'specs') 'contratos') 'base-de-datos.sql') (Join-Path $specs 'contratos')
    Copy-Item (Join-Path (Join-Path $raiz 'specs') 'consentimiento.md') $specs

    Sacar-DeEtapa 'web' '/app/web/dist' (Join-Path (Join-Path $servidor 'web') 'dist')
    Sacar-DeEtapa 'modelos' '/app/datos/modelos' (Join-Path (Join-Path $servidor 'datos') 'modelos')

    Write-Host ''
    Write-Host "Listo: $kit" -ForegroundColor Green
    foreach ($carpeta in Get-ChildItem $kit -Directory) {
        $bytes = (Get-ChildItem $carpeta.FullName -Recurse -File | Measure-Object Length -Sum).Sum
        Write-Host ('  {0,-18} {1,8:N1} MB' -f $carpeta.Name, ($bytes / 1MB))
    }
    Write-Host 'Siguiente paso: copiar las dos carpetas a \\<IP de la Pi>\addons\ (complementos\README.md).'
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
