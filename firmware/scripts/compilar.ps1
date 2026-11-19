# Nombre: compilar.ps1
# Descripción: Compila el firmware de la placa: la ESP32-CAM en firmware/build-esp32cam/ (D-24) y, si se pide, la XIAO ESP32-C6 en firmware/build-c6/ (D-21).
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.2
#
# Uso, desde la raíz del repositorio, en PowerShell (no en Git Bash: idf.py no funciona en MSYS):
#   .\firmware\scripts\compilar.ps1                      la ESP32-CAM de la demo
#   .\firmware\scripts\compilar.ps1 -Placa esp32cam, c6  las dos placas
#
# Si idf.py no está a mano, activa ESP-IDF 5.4 con el script que dejó EIM (C:\Espressif\tools\eim_idf.json).
# Cada placa compila en su carpeta, con su sdkconfig adentro. Si vuelve el ESP32-S3 (PR #7), suma aquí sus
# binarios octal y quad. Sale con código 1 si algo falla.

[CmdletBinding()]
param(
    [ValidateSet('esp32cam', 'c6')]
    [string[]]$Placa = @('esp32cam')
)

$ErrorActionPreference = 'Stop'
$firmware = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$eimJson = 'C:\Espressif\tools\eim_idf.json'
$tamanoFactory = 3MB  # partición factory de particiones.csv

# Cada placa con su target y su carpeta. ESP-IDF suma solo sdkconfig.defaults.<target> al común.
$placas = @{
    esp32cam = @{ Target = 'esp32'; Carpeta = 'build-esp32cam' }
    c6       = @{ Target = 'esp32c6'; Carpeta = 'build-c6' }
}

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
    foreach ($p in $Placa) {
        $datos = $placas[$p]
        $carpeta = Join-Path $firmware $datos.Carpeta
        Write-Host ''
        Write-Host "== Placa $p ($($datos.Target)) en firmware\$($datos.Carpeta) ($version)" -ForegroundColor Cyan
        & idf.py -C $firmware -B $carpeta -D "SDKCONFIG=$carpeta\sdkconfig" -D "IDF_TARGET=$($datos.Target)" build
        if ($LASTEXITCODE -ne 0) {
            throw "Falló la compilación de la placa $p (código $LASTEXITCODE)."
        }
        $bytes = (Get-Item (Join-Path $carpeta 'accesia.bin') -ErrorAction Stop).Length
        $resultados.Add([pscustomobject]@{
            Placa   = $p
            Archivo = "firmware\$($datos.Carpeta)\accesia.bin"
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
