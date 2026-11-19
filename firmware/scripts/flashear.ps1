# Nombre: flashear.ps1
# Descripción: Flashea una placa con los binarios del kit (kit\firmware): la XIAO ESP32-C6 de la demo o, si llega, un ESP32-S3 con su binario octal o quad. Dice qué placa flashea y cómo ponerla en modo de descarga.
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-18
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, en PowerShell, desde la raíz del repositorio (o con la copia que queda en kit\firmware):
#   .\kit\firmware\flashear.ps1 -Detectar -Puerto COM5        dice qué chip está conectado y si tiene PSRAM
#   .\kit\firmware\flashear.ps1 -Placa c6 -Puerto COM5         la XIAO ESP32-C6, la placa de la demo
#   .\kit\firmware\flashear.ps1 -Placa s3-octal -Puerto COM6   un ESP32-S3 con PSRAM octal (chip o módulo R8)
#   .\kit\firmware\flashear.ps1 -Placa s3-quad -Puerto COM6    un ESP32-S3 con PSRAM quad (chip o módulo R2)
#   -Borrar borra toda la flash antes, también la configuración de la consola.
#   -WhatIf muestra el comando de esptool sin flashear. Sin -Puerto, esptool busca la placa.
#
# Flashea cada archivo en su dirección, como idf.py flash, así que la configuración de la consola (NVS, de 0x9000 a
# 0xF000) se conserva. Usa el esptool del PATH o el del Python de ESP-IDF 5.4 (C:\Espressif\tools\eim_idf.json).
# Sale con código 1 si algo falla.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('c6', 's3-octal', 's3-quad')]
    [string]$Placa,
    [string]$Puerto,
    [switch]$Detectar,
    [switch]$Borrar,
    # La carpeta con c6, s3-octal y s3-quad. Por defecto, la de este script si las tiene, o kit\firmware.
    [string]$Kit
)
$ErrorActionPreference = 'Stop'
$eimJson = 'C:\Espressif\tools\eim_idf.json'
$baudios = '460800'
$carpetasDePlaca = @('c6', 's3-octal', 's3-quad')

$descargaS3 = @(
    'Conéctala por USB. Si tiene dos puertos USB, usa el que aparece como puerto COM en el Administrador de dispositivos.',
    'Modo de descarga: mantén presionado BOOT (IO0), presiona y suelta RESET (RST o EN) y suelta BOOT.',
    'Si la placa no tiene RESET, como la XIAO ESP32S3 Sense, conecta el cable con BOOT presionado.',
    'Al terminar, presiona RESET.')
$placas = @{
    'c6'       = @{
        Nombre   = 'Seeed Studio XIAO ESP32-C6, la placa del punto de acceso de la demo (D-21)'
        Chip     = 'esp32c6'
        Descarga = @(
            'Conéctala con un cable USB-C de datos. Casi siempre esptool la pone sola en modo de descarga.',
            'Si no conecta: mantén presionado BOOT, conecta el cable (o presiona y suelta RESET) y suelta BOOT.',
            'Al terminar, si no arranca sola, presiona RESET.')
        Consola  = @('wifi AccesIA <clave del hotspot>', 'codigo entrada', 'token <el que da la web al crear la cámara>',
            'mqtt mqtt://<IP de la Pi>:1883 camara <MQTT_CAMARA_CLAVE>', 'sensor dht22', 'antena interna', 'estado')
    }
    's3-octal' = @{
        Nombre   = 'ESP32-S3 con PSRAM octal: ESP32-S3-EYE, Freenove ESP32-S3 WROOM CAM, XIAO ESP32S3 Sense u otra con un chip o módulo R8 (firmware de referencia del PR #7, D-17)'
        Chip     = 'esp32s3'
        Descarga = $descargaS3
        Consola  = @('perfil <esp32s3_eye, freenove_s3_cam, xiao_s3_sense o generico_octal>',
            'wifi AccesIA <clave del hotspot>', 'codigo entrada', 'token <el que da la web al crear la cámara>',
            'mqtt mqtt://<IP de la Pi>:1883 camara <MQTT_CAMARA_CLAVE>', 'estado')
    }
    's3-quad'  = @{
        Nombre   = 'ESP32-S3 con PSRAM quad: un chip o módulo R2, con el perfil generico_quad (firmware de referencia del PR #7, D-17)'
        Chip     = 'esp32s3'
        Descarga = $descargaS3
        Consola  = @('perfil generico_quad', 'pin <…> para los pines de la cámara (ver arquitectura.md, PR #7)',
            'wifi AccesIA <clave del hotspot>', 'codigo entrada', 'token <el que da la web al crear la cámara>',
            'mqtt mqtt://<IP de la Pi>:1883 camara <MQTT_CAMARA_CLAVE>', 'estado')
    }
}

function Buscar-Kit {
    if ($Kit) {
        return (Resolve-Path $Kit).Path
    }
    foreach ($candidato in @($PSScriptRoot, (Join-Path $PSScriptRoot '..\..\kit\firmware'))) {
        foreach ($carpeta in $carpetasDePlaca) {
            if (Test-Path (Join-Path $candidato $carpeta)) {
                return (Resolve-Path $candidato).Path
            }
        }
    }
    throw 'No encuentro el kit: arma kit\firmware con firmware\scripts\armar-kit.ps1, o indica la carpeta con -Kit.'
}

function Buscar-Esptool {
    foreach ($nombre in @('esptool', 'esptool.exe')) {
        $comando = Get-Command $nombre -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($comando) {
            return @($comando.Source)
        }
    }
    if (-not (Get-Command idf.py -ErrorAction SilentlyContinue)) {
        if (-not (Test-Path $eimJson)) {
            throw 'No encuentro esptool ni ESP-IDF 5.4. Instala ESP-IDF como dice firmware\README.md, o esptool con: python -m pip install esptool'
        }
        $instalaciones = @((Get-Content $eimJson -Raw | ConvertFrom-Json).idfInstalled |
            Where-Object { $_.name -like 'v5.4*' })
        if ($instalaciones.Count -eq 0) {
            throw "No encuentro ESP-IDF 5.4 en $eimJson."
        }
        $idf = $instalaciones |
            Sort-Object { try { [version]($_.name.TrimStart('v')) } catch { [version]'0.0' } } -Descending |
            Select-Object -First 1
        Write-Host "Activando ESP-IDF $($idf.name) para usar su esptool..."
        Remove-Item Env:MSYSTEM -ErrorAction SilentlyContinue
        # Con -WhatIf, el script de activación tampoco haría nada: se activa de verdad y se vuelve a -WhatIf.
        $whatIfAntes = $WhatIfPreference
        $WhatIfPreference = $false
        try {
            . $idf.activationScript *> $null
        } finally {
            $WhatIfPreference = $whatIfAntes
        }
    }
    $python = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($python) {
        & $python.Source -m esptool version *> $null
        if ($LASTEXITCODE -eq 0) {
            return @($python.Source, '-m', 'esptool')
        }
    }
    throw 'El Python de ESP-IDF no tiene esptool. Prueba con: python -m pip install esptool'
}

function Correr-Esptool([string[]]$Argumentos) {
    $previos = @($script:esptool | Select-Object -Skip 1)
    & $script:esptool[0] @previos @Argumentos
    if ($LASTEXITCODE -ne 0) {
        throw "esptool terminó con código $LASTEXITCODE. Revisa el puerto y el modo de descarga."
    }
}

try {
    # Windows PowerShell 5.1 convierte en errores lo que un programa escribe por stderr si la salida se redirige.
    # Desde aquí deciden los códigos de salida y los throw, no stderr.
    $ErrorActionPreference = 'Continue'
    if (-not $Detectar -and -not $Placa) {
        throw 'Indica la placa con -Placa c6, s3-octal o s3-quad, o usa -Detectar para ver qué chip está conectado.'
    }
    $script:esptool = Buscar-Esptool
    $conPuerto = @()
    if ($Puerto) {
        $conPuerto = @('--port', $Puerto)
    }

    if ($Detectar) {
        Write-Host 'Leyendo el chip conectado...' -ForegroundColor Cyan
        Correr-Esptool ($conPuerto + @('chip_id'))
        Write-Host ''
        Write-Host 'Qué binario usar:'
        Write-Host '  -Placa c6        si dice ESP32-C6 (la XIAO ESP32-C6).'
        Write-Host '  -Placa s3-octal  si dice ESP32-S3 y «Embedded PSRAM 8MB» (chip o módulo R8).'
        Write-Host '  -Placa s3-quad   si dice ESP32-S3 y «Embedded PSRAM 2MB» (chip o módulo R2).'
        Write-Host '  Si es un ESP32-S3 sin PSRAM, este firmware no sirve: la cámara necesita PSRAM (D-17).'
        exit 0
    }

    $datos = $placas[$Placa]
    $kitRuta = Buscar-Kit
    $carpeta = Join-Path $kitRuta $Placa
    $flasherArgs = Join-Path $carpeta 'flasher_args.json'
    if (-not (Test-Path $flasherArgs)) {
        throw "No está $flasherArgs. Arma el kit con firmware\scripts\armar-kit.ps1."
    }
    $flasher = Get-Content $flasherArgs -Raw | ConvertFrom-Json
    $chip = $flasher.extra_esptool_args.chip
    if ($chip -ne $datos.Chip) {
        throw "La carpeta $Placa es para el chip $chip y la placa $Placa usa $($datos.Chip): el kit está mal armado."
    }
    $archivos = @()
    $direcciones = $flasher.flash_files.PSObject.Properties | Sort-Object { [Convert]::ToInt64($_.Name, 16) }
    foreach ($direccion in $direcciones) {
        $archivo = Join-Path $carpeta ($direccion.Value -replace '/', '\')
        if (-not (Test-Path $archivo)) {
            throw "Falta $archivo en el kit."
        }
        $archivos += @($direccion.Name, $archivo)
    }

    Write-Host ''
    Write-Host "== Placa: $($datos.Nombre)" -ForegroundColor Cyan
    $origen = Join-Path $carpeta 'origen.txt'
    if (Test-Path $origen) {
        Get-Content $origen -Encoding UTF8 | ForEach-Object { Write-Host "   $_" }
    }
    Write-Host "   Puerto: $(if ($Puerto) { $Puerto } else { 'el que encuentre esptool' })"
    Write-Host ''
    Write-Host 'Cómo ponerla en modo de descarga:' -ForegroundColor Yellow
    $datos.Descarga | ForEach-Object { Write-Host "  - $_" }
    Write-Host ''

    $comunes = @('--chip', $chip, '--baud', $baudios) + $conPuerto
    $escribir = $comunes + @('--before', $flasher.extra_esptool_args.before, '--after',
        $flasher.extra_esptool_args.after, 'write_flash') + @($flasher.write_flash_args) + $archivos
    Write-Host "esptool $($escribir -join ' ')"
    if ($PSCmdlet.ShouldProcess("$($datos.Nombre), $(if ($Puerto) { $Puerto } else { 'puerto automático' })",
            'Flashear')) {
        if ($Borrar) {
            Write-Host 'Borrando toda la flash, también la configuración de la consola...' -ForegroundColor Yellow
            Correr-Esptool ($comunes + @('erase_flash'))
        }
        Correr-Esptool $escribir
        Write-Host ''
        Write-Host 'Listo. Ahora, por la consola serial (115200 baudios):' -ForegroundColor Green
        $datos.Consola | ForEach-Object { Write-Host "  $_" }
        Write-Host 'Los valores de fábrica ya apuntan a la Pi (origen.txt). Si quedó en otra IP, también servidor y mqtt con esa IP.'
        Write-Host 'Para abrir la consola: idf.py -C firmware -B firmware\build-c6 -p COM5 monitor, desde el repositorio, o'
        Write-Host 'cualquier terminal serie, como python -m serial.tools.miniterm COM5 115200 con el Python de ESP-IDF.'
    }
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
