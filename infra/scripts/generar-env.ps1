# Nombre: generar-env.ps1
# Descripción: Crea infra/.env desde infra/.env.example con claves aleatorias, solo si todavía no existe (Windows).
# Fecha de creación: 2026-11-11
# Actualización: 2026-11-11
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio: .\infra\scripts\generar-env.ps1

$ErrorActionPreference = 'Stop'

$infra = Split-Path -Parent $PSScriptRoot
$ejemplo = Join-Path $infra '.env.example'
$destino = Join-Path $infra '.env'

if (Test-Path $destino) {
    Write-Host 'infra/.env ya existe; no lo cambio.'
    exit 0
}

# Claves que se llenan solas. SESION_SECRETO lleva 64 caracteres; las demás, 32.
$claves = @('POSTGRES_PASSWORD', 'AGENTE_DB_PASSWORD', 'SESION_SECRETO', 'ADMIN_CLAVE_INICIAL',
            'MQTT_SERVIDOR_CLAVE', 'MQTT_HA_CLAVE', 'MQTT_CAMARA_CLAVE')

function Nueva-Clave([int]$bytes) {
    $datos = New-Object byte[] $bytes
    $generador = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generador.GetBytes($datos) } finally { $generador.Dispose() }
    return -join ($datos | ForEach-Object { $_.ToString('x2') })
}

$lineas = foreach ($linea in Get-Content -Path $ejemplo -Encoding UTF8) {
    if ($linea -match '^([A-Z_]+)=$' -and $claves -contains $Matches[1]) {
        $nombre = $Matches[1]
        $bytes = 16
        if ($nombre -eq 'SESION_SECRETO') { $bytes = 32 }
        "$nombre=$(Nueva-Clave $bytes)"
    } else {
        $linea
    }
}

# Fin de línea LF y UTF-8 sin BOM, para que Docker Compose lo lea igual en Windows y en la Raspberry.
$texto = ($lineas -join "`n") + "`n"
[System.IO.File]::WriteAllText($destino, $texto, (New-Object System.Text.UTF8Encoding $false))
Write-Host 'Listo: se creó infra/.env con claves nuevas. No lo subas a Git.'
