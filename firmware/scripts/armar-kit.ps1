# Nombre: armar-kit.ps1
# Descripción: Arma kit\firmware (fuera de Git) con los binarios para flashear sin compilar: la XIAO ESP32-C6 de este firmware y, con una copia del PR #7, los binarios octal y quad del ESP32-S3, todos con la IP de la Pi (D-22). Copia también flashear.ps1.
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-18
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio, en PowerShell (no en Git Bash: idf.py no funciona en MSYS):
#   .\firmware\scripts\armar-kit.ps1                            compila la XIAO ESP32-C6 y arma kit\firmware\c6
#   .\firmware\scripts\armar-kit.ps1 -FuenteS3 ..\AccesIA-s3    también kit\firmware\s3-octal y s3-quad
#   .\firmware\scripts\armar-kit.ps1 -FuenteS3 ..\AccesIA-s3 -SoloS3
#
# -FuenteS3 es una copia del PR #7 (rama a/esp-idf-deteccion), por ejemplo un worktree:
#   git fetch origin a/esp-idf-deteccion
#   git worktree add ..\AccesIA-s3 origin/a/esp-idf-deteccion
# Se compila en una carpeta temporal, con la IP de la Pi en lugar de 10.42.0.1 en los valores de fábrica y en los
# ejemplos de la consola, así que esa copia no cambia.
# La IP sale de ACCESIA_IP_DE_LA_PI (components\accesia_config\include\accesia\valores_de_fabrica.hpp), el único
# lugar donde está. Sale con código 1 si algo falla.
[CmdletBinding()]
param(
    [string]$FuenteS3,
    [switch]$SoloS3
)
$ErrorActionPreference = 'Stop'
$firmware = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$raiz = (Resolve-Path (Join-Path $firmware '..')).Path
$kit = Join-Path $raiz 'kit\firmware'
$valores = Join-Path $firmware 'components\accesia_config\include\accesia\valores_de_fabrica.hpp'

function Leer-IpDeLaPi {
    $linea = Select-String -Path $valores -Pattern '#define ACCESIA_IP_DE_LA_PI "([0-9.]+)"' | Select-Object -First 1
    if (-not $linea) {
        throw "No encuentro ACCESIA_IP_DE_LA_PI en $valores."
    }
    return $linea.Matches[0].Groups[1].Value
}

function Copiar-Binarios([string]$Compilacion, [string]$Destino, [string[]]$Origen) {
    if (Test-Path $Destino) {
        Remove-Item $Destino -Recurse -Force
    }
    New-Item -ItemType Directory -Force $Destino | Out-Null
    $flasherArgs = Join-Path $Compilacion 'flasher_args.json'
    $flasher = Get-Content $flasherArgs -Raw | ConvertFrom-Json
    Copy-Item $flasherArgs $Destino
    foreach ($direccion in $flasher.flash_files.PSObject.Properties) {
        $relativo = $direccion.Value -replace '/', '\'
        $destinoArchivo = Join-Path $Destino $relativo
        New-Item -ItemType Directory -Force (Split-Path $destinoArchivo) | Out-Null
        Copy-Item (Join-Path $Compilacion $relativo) $destinoArchivo
    }
    $Origen | Set-Content -Path (Join-Path $Destino 'origen.txt') -Encoding UTF8
}

function Commit-De([string]$Carpeta) {
    $commit = (& git -C $Carpeta rev-parse --short HEAD) -join ''
    $cambios = (& git -C $Carpeta status --porcelain -- firmware) -join ''
    if ($cambios) {
        return "$commit, con cambios sin commit"
    }
    return $commit
}

try {
    # Windows PowerShell 5.1 convierte en errores lo que un programa escribe por stderr si la salida se redirige.
    # Desde aquí deciden los códigos de salida y los throw, no stderr.
    $ErrorActionPreference = 'Continue'
    $ip = Leer-IpDeLaPi
    $fecha = Get-Date -Format 'yyyy-MM-dd HH:mm'
    New-Item -ItemType Directory -Force $kit | Out-Null

    if (-not $SoloS3) {
        & (Join-Path $PSScriptRoot 'compilar.ps1')
        if ($LASTEXITCODE -ne 0) {
            throw 'Falló la compilación de la XIAO ESP32-C6.'
        }
        $version = (& idf.py --version 2>$null) -join ' '
        Copiar-Binarios (Join-Path $firmware 'build-c6') (Join-Path $kit 'c6') @(
            'Placa: Seeed Studio XIAO ESP32-C6 (chip esp32c6)',
            "Firmware: este repositorio, commit $(Commit-De $raiz)",
            "Servidor de fábrica: http://${ip}:8000",
            "MQTT de fábrica: mqtt://${ip}:1883, usuario camara",
            "Compilado: $fecha, con $version")
    }

    if ($FuenteS3) {
        $fuente = (Resolve-Path $FuenteS3).Path
        if (-not (Test-Path (Join-Path $fuente 'firmware\scripts\compilar-binarios.ps1'))) {
            throw "$fuente no es una copia del PR #7: no tiene firmware\scripts\compilar-binarios.ps1."
        }
        $commitS3 = Commit-De $fuente
        $temporal = Join-Path ([IO.Path]::GetTempPath()) 'accesia-s3'
        if (Test-Path $temporal) {
            Remove-Item $temporal -Recurse -Force
        }
        Write-Host ''
        Write-Host "== ESP32-S3 desde $fuente ($commitS3), en $temporal, con la IP $ip" -ForegroundColor Cyan
        & robocopy (Join-Path $fuente 'firmware') (Join-Path $temporal 'firmware') /E /XD 'build-*' /NFL /NDL /NJH /NJS /NP |
            Out-Null
        if ($LASTEXITCODE -ge 8) {
            throw "No se pudo copiar el firmware del S3 (robocopy terminó con $LASTEXITCODE)."
        }
        $cambiados = @()
        $codigo = Get-ChildItem (Join-Path $temporal 'firmware\components') -Recurse -File -Include '*.cpp', '*.hpp'
        foreach ($archivo in $codigo) {
            $texto = [IO.File]::ReadAllText($archivo.FullName)
            if ($texto -match '10\.42\.0\.1') {
                [IO.File]::WriteAllText($archivo.FullName, ($texto -replace '10\.42\.0\.1', $ip),
                    (New-Object Text.UTF8Encoding($false)))
                $cambiados += $archivo.Name
            }
        }
        if ($cambiados -notcontains 'config.hpp') {
            throw 'El config.hpp del PR #7 ya no tiene 10.42.0.1: revisa sus valores de fábrica antes de cambiarlos.'
        }
        Write-Host "IP de la Pi en: $($cambiados -join ', ')"
        & (Join-Path $temporal 'firmware\scripts\compilar-binarios.ps1')
        if ($LASTEXITCODE -ne 0) {
            throw 'Falló la compilación de los binarios del ESP32-S3.'
        }
        $version = (& idf.py --version 2>$null) -join ' '
        foreach ($binario in @('octal', 'quad')) {
            Copiar-Binarios (Join-Path $temporal "firmware\build-$binario") (Join-Path $kit "s3-$binario") @(
                "Placa: ESP32-S3 con PSRAM $binario (chip esp32s3), binario $binario de D-17",
                "Firmware: el de referencia del PR #7, commit $commitS3, con la IP de la Pi en lugar de 10.42.0.1",
                "Servidor de fábrica: http://${ip}:8000",
                "MQTT de fábrica: mqtt://${ip}:1883, usuario camara",
                "Compilado: $fecha, con $version")
        }
        Remove-Item $temporal -Recurse -Force -ErrorAction SilentlyContinue
    }

    Copy-Item (Join-Path $PSScriptRoot 'flashear.ps1') $kit -Force
    $placasEnElKit = @(Get-ChildItem $kit -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'origen.txt') })
    $leeme = @(
        '# Kit de flasheo de AccesIA',
        '',
        "Armado el $fecha con firmware\scripts\armar-kit.ps1. No va a Git: lleva binarios.",
        '',
        '| Carpeta | Para qué |',
        '| --- | --- |')
    foreach ($carpeta in $placasEnElKit) {
        $leeme += "| ``$($carpeta.Name)`` | $((Get-Content (Join-Path $carpeta.FullName 'origen.txt') -Encoding UTF8 | Select-Object -First 1)) |"
    }
    $leeme += @(
        '',
        'Flashear, en PowerShell y con la placa conectada por USB:',
        '',
        '```powershell',
        '.\flashear.ps1 -Detectar -Puerto COM5          # qué chip está conectado y si tiene PSRAM',
        '.\flashear.ps1 -Placa c6 -Puerto COM5           # la XIAO ESP32-C6',
        '.\flashear.ps1 -Placa s3-octal -Puerto COM6     # un ESP32-S3 con PSRAM octal',
        '```',
        '',
        'El script dice cómo poner la placa en modo de descarga, flashea cada archivo en su dirección (la configuración',
        'de la consola se conserva) y muestra los comandos de la consola que faltan. Más detalle en firmware\README.md.')
    $leeme | Set-Content -Path (Join-Path $kit 'LEEME.md') -Encoding UTF8

    Write-Host ''
    Write-Host "Listo: $kit" -ForegroundColor Green
    Get-ChildItem $kit -Recurse -File | ForEach-Object {
        [pscustomobject]@{
            Archivo = $_.FullName.Substring($kit.Length + 1)
            KB      = [math]::Round($_.Length / 1KB)
        }
    } | Format-Table -AutoSize | Out-String | Write-Host
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
