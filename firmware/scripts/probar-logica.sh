#!/usr/bin/env bash
# Nombre: probar-logica.sh
# Descripción: Compila y corre las pruebas de la lógica pura del firmware con CMake y doctest: recorte, espera, mensajes MQTT, puerta, ambiente, LED y pines.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.1
#
# Necesita Linux con g++, CMake 3.20 o más reciente y, si está, Ninja. En el equipo se corre desde
# probar-logica.ps1, en un contenedor ubuntu:24.04; desde el Día 4 también lo corre GitHub Actions.
#
# Uso, desde la raíz del repositorio:
#   bash firmware/scripts/probar-logica.sh              compila en /tmp/accesia-pruebas y corre las pruebas
#   bash firmware/scripts/probar-logica.sh <carpeta>    compila en otra carpeta

set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
compilacion="${1:-/tmp/accesia-pruebas}"

generador=()
if command -v ninja >/dev/null 2>&1; then
  generador=(-G Ninja)
fi

echo "== Configurando las pruebas en $compilacion"
cmake -S "$raiz/firmware/pruebas" -B "$compilacion" "${generador[@]}" -DCMAKE_BUILD_TYPE=Debug
echo "== Compilando"
cmake --build "$compilacion" --parallel
echo "== Corriendo las pruebas, con el tiempo de cada una"
"$compilacion/pruebas" --duration=true
