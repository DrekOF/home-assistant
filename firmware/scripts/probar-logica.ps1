# Nombre: probar-logica.ps1
# Descripción: Corre las pruebas de la lógica pura del firmware en un contenedor ubuntu:24.04 de Docker Desktop.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio y con Docker Desktop abierto:
#   .\firmware\scripts\probar-logica.ps1
#
# El contenedor se borra al terminar. Instala g++, CMake y Ninja, monta el repositorio de solo lectura
# y corre firmware/scripts/probar-logica.sh, que compila dentro del contenedor. Sale con el código de las pruebas.

$ErrorActionPreference = 'Stop'

$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$imagen = 'ubuntu:24.04'
$preparar = 'export DEBIAN_FRONTEND=noninteractive && apt-get update -qq && apt-get install -y -qq --no-install-recommends g++ cmake ninja-build ca-certificates > /dev/null'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host 'No encuentro docker: abre Docker Desktop y vuelve a intentar.' -ForegroundColor Red
    exit 1
}

Write-Host "== Pruebas de la lógica pura en $imagen (Docker Desktop)" -ForegroundColor Cyan

# Windows PowerShell 5.1 convierte en errores las líneas que un programa escribe por stderr cuando la salida
# se redirige (por ejemplo, a un archivo). Por eso, dentro del contenedor stderr va a stdout, y aquí decide
# el código de salida de docker, no stderr.
$ErrorActionPreference = 'Continue'
docker run --rm -v "${raiz}:/repo:ro" -w /repo $imagen bash -c "exec 2>&1; $preparar && bash firmware/scripts/probar-logica.sh"
exit $LASTEXITCODE
