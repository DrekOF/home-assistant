# Nombre: flashear.ps1
# Descripción: Flashea una placa con los binarios del kit (kit\firmware): la ESP32-CAM de la demo o, de respaldo, un ESP32-S3 con su binario octal o quad. Dice qué placa flashea y cómo ponerla en modo de descarga, y abre el monitor serial.
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-19
# Autor: Equipo AccesIA
# Versión: 1.1
#
# Uso, en PowerShell, desde la raíz del repositorio (o con la copia que queda en kit\firmware):
#   .\kit\firmware\flashear.ps1 -Placa esp32cam -Puerto COM5 -Monitor   la ESP32-CAM de la demo (D-24), y su consola
#   .\kit\firmware\flashear.ps1 -Monitor -Puerto COM5                   solo abre la consola de la placa
#   .\kit\firmware\flashear.ps1 -Detectar -Puerto COM5                  dice qué chip está conectado y si tiene PSRAM
#   .\kit\firmware\flashear.ps1 -Placa s3-octal -Puerto COM6            un ESP32-S3 con PSRAM octal (chip o módulo R8)
#   .\kit\firmware\flashear.ps1 -Placa s3-quad -Puerto COM6             un ESP32-S3 con PSRAM quad (chip o módulo R2)
#   .\kit\firmware\flashear.ps1 -Placa c6 -Puerto COM5                  la XIAO ESP32-C6, si el kit la trae (sin uso desde D-24)
#   -Borrar borra toda la flash antes, también la configuración de la consola.
#   -WhatIf muestra el comando de esptool sin flashear. Sin -Puerto, esptool busca la placa.
#
# Flashea cada archivo en su dirección, como idf.py flash, así que la configuración de la consola (NVS, de 0x9000 a
# 0xF000) se conserva. Usa el esptool del PATH o el del Python de ESP-IDF 5.4 (C:\Espressif\tools\eim_idf.json).
# El monitor es miniterm de pyserial con DTR y RTS en 0, para que la base de la ESP32-CAM no deje la placa en reset:
# Ctrl+T y Ctrl+R dos veces la reinician, y Ctrl+] sale. Sale con código 1 si algo falla.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('esp32cam', 's3-octal', 's3-quad', 'c6')]
    [string]$Placa,
    [string]$Puerto,
    [switch]$Detectar,
    [switch]$Borrar,
    [switch]$Monitor,
    # La carpeta con las carpetas de cada placa. Por defecto, la de este script si las tiene, o kit\firmware.
    [string]$Kit
)
$ErrorActionPreference = 'Stop'
$eimJson = 'C:\Espressif\tools\eim_idf.json'
$baudios = '460800'
$carpetasDePlaca = @('esp32cam', 's3-octal', 's3-quad', 'c6')

$descargaS3 = @(
    'Conéctala por USB. Si tiene dos puertos USB, usa el que aparece como puerto COM en el Administrador de dispositivos.',
    'Modo de descarga: mantén presionado BOOT (IO0), presiona y suelta RESET (RST o EN) y suelta BOOT.',
    'Si la placa no tiene RESET, como la XIAO ESP32S3 Sense, conecta el cable con BOOT presionado.',
    'Al terminar, presiona RESET.')
$consolaComun = @('wifi AccesIA <clave del hotspot>', 'codigo entrada', 'token <el que da la web al crear la cámara>',
    'mqtt mqtt://<IP de la Pi>:1883 camara <MQTT_CAMARA_CLAVE>')
$placas = @{
    'esp32cam' = @{
        Nombre   = 'ESP32-CAM AI-Thinker, la cámara y el punto de acceso de la demo (D-24)'
        Chip     = 'esp32'
        Descarga = @(
            'En su base con USB-C (ESP32-CAM-MB): conéctala y esptool la pone sola en modo de descarga. Windows la muestra como «USB Serial Port» (COMn).',
            'Con un adaptador USB-TTL: 5V y GND, U0R al TX y U0T al RX del adaptador, y GPIO0 a GND. Presiona RST antes de flashear; al terminar, quita el puente de GPIO0 y presiona RST.',
            'La base tapa el botón RST: para reiniciar, abre el monitor (-Monitor) y presiona Ctrl+T y Ctrl+R dos veces.')
        Consola  = $consolaComun + @('reiniciar', 'estado')
    }
    's3-octal' = @{
        Nombre   = 'ESP32-S3 con PSRAM octal: ESP32-S3-EYE, Freenove ESP32-S3 WROOM CAM, XIAO ESP32S3 Sense u otra con un chip o módulo R8 (firmware de referencia del PR #7, D-17)'
        Chip     = 'esp32s3'
        Descarga = $descargaS3
        Consola  = @('perfil <esp32s3_eye, freenove_s3_cam, xiao_s3_sense o generico_octal>') + $consolaComun + @('estado')
    }
    's3-quad'  = @{
        Nombre   = 'ESP32-S3 con PSRAM quad: un chip o módulo R2, con el perfil generico_quad (firmware de referencia del PR #7, D-17)'
        Chip     = 'esp32s3'
        Descarga = $descargaS3
        Consola  = @('perfil generico_quad', 'pin <…> para los pines de la cámara (ver arquitectura.md, PR #7)') +
            $consolaComun + @('estado')
    }
    'c6'       = @{
        Nombre   = 'Seeed Studio XIAO ESP32-C6 (D-21, sin uso desde D-24)'
        Chip     = 'esp32c6'
        Descarga = @(
            'Conéctala con un cable USB-C de datos. Casi siempre esptool la pone sola en modo de descarga.',
            'Si no conecta: mantén presionado BOOT, conecta el cable (o presiona y suelta RESET) y suelta BOOT.',
            'Al terminar, si no arranca sola, presiona RESET.')
        Consola  = $consolaComun + @('sensor dht22', 'antena interna', 'estado')
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

function Activar-Python {
    if (Get-Command idf.py -ErrorAction SilentlyContinue) {
        return
    }
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
    Write-Host "Activando ESP-IDF $($idf.name) para usar su esptool y su Python..."
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

function Buscar-Esptool {
    foreach ($nombre in @('esptool', 'esptool.exe')) {
        $comando = Get-Command $nombre -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($comando) {
            return @($comando.Source)
        }
    }
    Activar-Python
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

function Abrir-Monitor {
    $argumentos = @('-m', 'serial.tools.miniterm', '--dtr', '0', '--rts', '0')
    if ($Puerto) {
        $argumentos += $Puerto
    }
    $argumentos += '115200'
    Write-Host ''
    Write-Host 'Monitor serial (115200 baudios). Ctrl+T y Ctrl+R dos veces reinician la placa; Ctrl+] sale.' -ForegroundColor Cyan
    Write-Host "python $($argumentos -join ' ')"
    if ($WhatIfPreference) {
        return
    }
    Activar-Python
    $python = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $python) {
        throw 'No encuentro Python para el monitor. Abre una terminal de ESP-IDF y corre el comando de arriba.'
    }
    & $python.Source @argumentos
}

try {
    # Windows PowerShell 5.1 convierte en errores lo que un programa escribe por stderr si la salida se redirige.
    # Desde aquí deciden los códigos de salida y los throw, no stderr.
    $ErrorActionPreference = 'Continue'
    if (-not $Detectar -and -not $Placa -and -not $Monitor) {
        throw 'Indica la placa con -Placa esp32cam, s3-octal, s3-quad o c6; usa -Detectar para ver qué chip está conectado, o -Monitor para abrir la consola.'
    }
    $conPuerto = @()
    if ($Puerto) {
        $conPuerto = @('--port', $Puerto)
    }

    if ($Detectar) {
        $script:esptool = Buscar-Esptool
        Write-Host 'Leyendo el chip conectado...' -ForegroundColor Cyan
        Correr-Esptool ($conPuerto + @('chip_id'))
        Write-Host ''
        Write-Host 'Qué binario usar:'
        Write-Host '  -Placa esp32cam  si dice ESP32-D0WD (ESP32 clásico): la ESP32-CAM AI-Thinker.'
        Write-Host '  -Placa s3-octal  si dice ESP32-S3 y «Embedded PSRAM 8MB» (chip o módulo R8).'
        Write-Host '  -Placa s3-quad   si dice ESP32-S3 y «Embedded PSRAM 2MB» (chip o módulo R2).'
        Write-Host '  -Placa c6        si dice ESP32-C6 (la XIAO ESP32-C6, sin uso desde D-24).'
        Write-Host '  Si es un ESP32-S3 sin PSRAM, este firmware no sirve: la cámara necesita PSRAM (D-17).'
        exit 0
    }

    if (-not $Placa) {
        Abrir-Monitor
        exit 0
    }

    $script:esptool = Buscar-Esptool
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
        if (-not $Monitor) {
            Write-Host "Para abrir la consola: .\flashear.ps1 -Monitor$(if ($Puerto) { " -Puerto $Puerto" }) (Ctrl+T y Ctrl+R dos veces reinician la placa)."
        }
    }
    if ($Monitor) {
        Abrir-Monitor
    }
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
