# Nombre: crear-claves-mqtt.ps1
# Descripción: Genera infra/mosquitto/claves/passwd con los usuarios de MQTT, usando mosquitto_passwd dentro del contenedor (Windows).
# Fecha de creación: 2026-11-11
# Actualización: 2026-11-11
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio y después de generar-env: .\infra\scripts\crear-claves-mqtt.ps1

$ErrorActionPreference = 'Stop'

$infra = Split-Path -Parent $PSScriptRoot
$archivoEnv = Join-Path $infra '.env'
if (-not (Test-Path $archivoEnv)) {
    throw 'Falta infra/.env: corre primero .\infra\scripts\generar-env.ps1.'
}

$valores = @{}
foreach ($linea in Get-Content -Path $archivoEnv -Encoding UTF8) {
    if ($linea -match '^([A-Z_]+)=(.*)$') { $valores[$Matches[1]] = $Matches[2] }
}
foreach ($nombre in 'MQTT_SERVIDOR_CLAVE', 'MQTT_HA_CLAVE', 'MQTT_CAMARA_CLAVE') {
    if (-not $valores[$nombre]) { throw "Falta $nombre en infra/.env." }
}

New-Item -ItemType Directory -Force -Path (Join-Path $infra 'mosquitto/claves') | Out-Null

# Las claves que crea generar-env son hexadecimales, así que van sin comillas.
# mosquitto_passwd -c no sobrescribe un archivo existente: se borra antes para poder correr el script otra vez.
$archivo = '/mosquitto/config/claves/passwd'
$guion = "rm -f $archivo && " +
         "mosquitto_passwd -b -c $archivo servidor `$1 && " +
         "mosquitto_passwd -b $archivo homeassistant `$2 && " +
         "mosquitto_passwd -b $archivo camara `$3 && " +
         "{ chown mosquitto:mosquitto $archivo && chmod 0700 $archivo || true; }"

& docker compose -f (Join-Path $infra 'compose.yaml') run --rm --no-deps --entrypoint sh mosquitto -c $guion claves `
    $valores['MQTT_SERVIDOR_CLAVE'] $valores['MQTT_HA_CLAVE'] $valores['MQTT_CAMARA_CLAVE']
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el archivo de claves de MQTT.' }

Write-Host 'Listo: infra/mosquitto/claves/passwd tiene los usuarios servidor, homeassistant y camara.'
