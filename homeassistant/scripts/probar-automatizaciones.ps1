# Nombre: probar-automatizaciones.ps1
# Descripción: Prueba las automatizaciones de AccesIA en Home Assistant sin el servidor (C2 del Día 3): publica con el usuario servidor el Evento «permitido» y la Alerta de contratos/mqtt.md, y espera el ABRIR que manda Home Assistant. La clave sale de infra/.env y no se muestra.
# Fecha de creación: 2026-11-18
# Actualización: 2026-11-18
# Autor: Equipo AccesIA
# Versión: 1.0
# Uso, desde la raíz del repositorio, con Docker Desktop abierto (usa la imagen eclipse-mosquitto:2):
#   .\homeassistant\scripts\probar-automatizaciones.ps1                         broker de la Pi (192.168.137.250)
#   .\homeassistant\scripts\probar-automatizaciones.ps1 -Broker 192.168.137.1   broker del portátil (plan B)
# Los mensajes son los ejemplos del contrato: después, «Última persona» muestra «Ana Gómez» hasta el siguiente acceso real.

param(
    [string]$Broker = '192.168.137.250'
)

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$archivoEnv = Join-Path $raiz 'infra\.env'
if (-not (Test-Path -LiteralPath $archivoEnv)) {
    throw 'Falta infra/.env: créalo con .\infra\scripts\generar-env.ps1'
}
$linea = Select-String -LiteralPath $archivoEnv -Pattern '^MQTT_SERVIDOR_CLAVE=(.+)$' | Select-Object -First 1
if (-not $linea) {
    throw 'infra/.env no tiene MQTT_SERVIDOR_CLAVE'
}
# La clave pasa al contenedor por una variable de entorno: no queda en la línea de comandos ni se muestra.
$env:MQTT_CLAVE = $linea.Matches[0].Groups[1].Value.Trim().Trim('"')
$env:BROKER = $Broker
$pruebas = Join-Path $raiz 'homeassistant\pruebas'

try {
    Write-Host "1. Evento «permitido» en accesia/entrada/evento. Home Assistant debe publicar ABRIR en accesia/entrada/puerta/set (espera hasta 10 s)."
    $orden = 'mosquitto_sub -h $BROKER -u servidor -P $MQTT_CLAVE -t accesia/entrada/puerta/set -C 1 -W 10 & sleep 2; ' +
             'mosquitto_pub -h $BROKER -u servidor -P $MQTT_CLAVE -q 1 -t accesia/entrada/evento -f /pruebas/evento-permitido.json; wait'
    $salida = docker run --rm -e MQTT_CLAVE -e BROKER -v "${pruebas}:/pruebas:ro" eclipse-mosquitto:2 sh -c $orden 2>&1
    if ($salida -match 'ABRIR') {
        Write-Host '   Bien: Home Assistant publicó ABRIR. Si la placa está conectada, su LED se enciende 3 s.' -ForegroundColor Green
    } else {
        Write-Host "   No llegó ABRIR. Revisa que Home Assistant cargó automatizaciones_accesia.yaml, que su integración MQTT esté conectada a $Broker y la clave de servidor." -ForegroundColor Red
        Write-Host "   Lo que respondió el broker: $salida"
    }

    Write-Host '2. Alerta en accesia/entrada/alerta. Home Assistant debe crear la notificación «Desconocidos en entrada».'
    $orden = 'mosquitto_pub -h $BROKER -u servidor -P $MQTT_CLAVE -q 1 -t accesia/entrada/alerta -f /pruebas/alerta.json'
    docker run --rm -e MQTT_CLAVE -e BROKER -v "${pruebas}:/pruebas:ro" eclipse-mosquitto:2 sh -c $orden
    Write-Host '   Mírala en la campana de Home Assistant: «3 caras desconocidas en 60 s, a las 08:15.» Si dice 13:15, la zona horaria no es America/Bogota.'
} finally {
    Remove-Item Env:MQTT_CLAVE, Env:BROKER -ErrorAction SilentlyContinue
}
