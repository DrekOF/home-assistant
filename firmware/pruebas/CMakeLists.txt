# Nombre: CMakeLists.txt
# Descripción: Pruebas de la lógica pura del firmware (recorte, cara_min y espera entre recortes) con doctest, sin placa.
# Fecha de creación: 2026-11-12
# Actualización: 2026-11-12
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Se corren con firmware/scripts/probar-logica.ps1 (contenedor ubuntu:24.04) o con probar-logica.sh en Linux.
# No usan ESP-IDF: compilan los mismos archivos del componente accesia_recorte con el g++ del equipo.
# doctest y nlohmann/json se bajan al configurar, en versiones fijas y comprobados con su huella SHA-256.

cmake_minimum_required(VERSION 3.20)
project(pruebas_logica_accesia LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(TERCEROS ${CMAKE_BINARY_DIR}/terceros)

# doctest 2.5.3 y nlohmann/json 3.12.0, de una sola cabecera cada uno.
file(DOWNLOAD
    https://raw.githubusercontent.com/doctest/doctest/v2.5.3/doctest/doctest.h
    ${TERCEROS}/doctest/doctest.h
    EXPECTED_HASH SHA256=cfd518a3ef90f67e1f3ba514df23fb3627437de1a2feeba78cf5062a40021421
    TLS_VERIFY ON)
file(DOWNLOAD
    https://github.com/nlohmann/json/releases/download/v3.12.0/json.hpp
    ${TERCEROS}/nlohmann/json.hpp
    EXPECTED_HASH SHA256=aaf127c04cb31c406e5b04a63f1ae89369fccde6d8fa7cdda1ed4f32dfc5de63
    TLS_VERIFY ON)

set(RECORTE ${CMAKE_CURRENT_SOURCE_DIR}/../components/accesia_recorte)
set(CASOS_RECORTE ${CMAKE_CURRENT_SOURCE_DIR}/../../specs/contratos/casos-recorte.json)

# Detiene la prueba ante comportamiento indefinido (desbordes, divisiones o desplazamientos inválidos).
set(SANITIZAR -fsanitize=undefined -fno-sanitize-recover=all)

add_library(accesia_recorte STATIC ${RECORTE}/recorte.cpp ${RECORTE}/espera.cpp)
target_include_directories(accesia_recorte PUBLIC ${RECORTE}/include)
target_compile_options(accesia_recorte PRIVATE -Wall -Wextra -Wpedantic -Werror ${SANITIZAR})
target_link_options(accesia_recorte PUBLIC ${SANITIZAR})

add_executable(pruebas principal.cpp prueba_recorte.cpp prueba_espera.cpp)
target_include_directories(pruebas SYSTEM PRIVATE ${TERCEROS})
target_compile_options(pruebas PRIVATE -Wall -Wextra -Werror ${SANITIZAR})
target_compile_definitions(pruebas PRIVATE CASOS_RECORTE="${CASOS_RECORTE}")
target_link_libraries(pruebas PRIVATE accesia_recorte)

enable_testing()
add_test(NAME logica_pura COMMAND pruebas)
