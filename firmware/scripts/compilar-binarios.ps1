# Nombre: compilar-binarios.ps1
# Descripción: Compila los dos binarios del firmware (octal y quad, D-17) en firmware/build-octal/ y firmware/build-quad/.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio, en PowerShell (no en Git Bash: idf.py no funciona en MSYS):
#   .\firmware\scripts\compilar-binarios.ps1                 compila los dos binarios
#   .\firmware\scripts\compilar-binarios.ps1 -Binario quad   compila solo uno
#
# Si idf.py no está a mano, activa ESP-IDF 5.4 con el script que dejó EIM (C:\Espressif\tools\eim_idf.json).
# Cada binario usa sdkconfig.defaults más sdkconfig.defaults.<binario> y guarda su sdkconfig en su carpeta.
# Sale con código 1 si algo falla.

[CmdletBinding()]
param(
    [ValidateSet('octal', 'quad')]
    [string[]]$Binario = @('octal', 'quad')
)

$ErrorActionPreference = 'Stop'
$firmware = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$eimJson = 'C:\Espressif\tools\eim_idf.json'
$tamanoFactory = 3MB  # partición factory de particiones.csv

function Activar-EspIdf {
    if (Get-Command idf.py -ErrorAction SilentlyContinue) {
        return
    }
    if (-not (Test-Path $eimJson)) {
        throw "No encuentro idf.py ni $eimJson. Instala ESP-IDF 5.4 como dice firmware/README.md."
    }
    $instalaciones = @((Get-Content $eimJson -Raw | ConvertFrom-Json).idfInstalled |
        Where-Object { $_.name -like 'v5.4*' })
    if ($instalaciones.Count -eq 0) {
        throw "No encuentro ESP-IDF 5.4 en $eimJson."
    }
    $idf = $instalaciones |
        Sort-Object { try { [version]($_.name.TrimStart('v')) } catch { [version]'0.0' } } -Descending |
        Select-Object -First 1
    Write-Host "Activando ESP-IDF $($idf.name)..."
    . $idf.activationScript *> $null
}

try {
    # Windows PowerShell 5.1 convierte en errores las líneas que idf.py escribe por stderr cuando la salida se
    # redirige (por ejemplo, a un archivo). Desde aquí deciden los códigos de salida y los throw, no stderr.
    $ErrorActionPreference = 'Continue'

    # idf.py rechaza el entorno de MSYS: si este PowerShell se abrió desde Git Bash, se quita esa marca.
    Remove-Item Env:MSYSTEM -ErrorAction SilentlyContinue
    Activar-EspIdf

    $version = (& idf.py --version 2>$null) -join ' '
    if ($version -notmatch 'v5\.4') {
        throw "Hace falta ESP-IDF 5.4 y está activo: $version"
    }

    $resultados = New-Object System.Collections.Generic.List[object]
    foreach ($b in $Binario) {
        $carpeta = Join-Path $firmware "build-$b"
        Write-Host ''
        Write-Host "== Binario $b en firmware\build-$b ($version)" -ForegroundColor Cyan
        & idf.py -C $firmware -B $carpeta -D "SDKCONFIG=$carpeta\sdkconfig" `
            -D "SDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.defaults.$b" -D IDF_TARGET=esp32s3 build
        if ($LASTEXITCODE -ne 0) {
            throw "Falló la compilación del binario $b (código $LASTEXITCODE)."
        }
        $bytes = (Get-Item (Join-Path $carpeta 'accesia.bin') -ErrorAction Stop).Length
        $resultados.Add([pscustomobject]@{
            Binario = $b
            Archivo = "firmware\build-$b\accesia.bin"
            Bytes   = $bytes
            Factory = '{0:P0} de 3 MB' -f ($bytes / $tamanoFactory)
        })
    }

    Write-Host ''
    Write-Host 'Listo:' -ForegroundColor Green
    $resultados | Format-Table -AutoSize | Out-String | Write-Host
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
