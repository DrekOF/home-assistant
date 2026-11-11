<!--
Nombre: README.md
Descripción: Índice de las specs de AccesIA y orden de lectura.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Specs de AccesIA

Aquí está qué se construye y con qué reglas. Se leen antes de cada tarea. Si el código y una spec no coinciden, manda la spec; si la spec está mal, primero se corrige la spec.

## Orden de lectura

| # | Archivo | Para qué sirve |
| --- | --- | --- |
| 1 | [enunciado.md](enunciado.md) | Lo que pidió el docente y dónde se cumple cada parte |
| 2 | [decisiones.md](decisiones.md) | Por qué el sistema es así (D-01 a D-19) |
| 3 | [arquitectura.md](arquitectura.md) | Piezas, flujos, servicios, puertos, configuración y despliegue |
| 4 | [requisitos.md](requisitos.md) | Qué debe hacer (RF y RNF) y cómo se comprueba (criterios C) |
| 5 | [reglas.md](reglas.md) | Reglas de negocio R1 a R9 con sus casos de prueba |
| 6 | [modelo-datos.md](modelo-datos.md) | Tablas, vistas y quién puede leer qué |
| 7 | [consentimiento.md](consentimiento.md) | Texto de la autorización de datos biométricos (Ley 1581) |
| 8 | [plan.md](plan.md) | Días, hitos y tareas |
| — | [contratos/](contratos/README.md) | API, MQTT, agente y base de datos: el acuerdo entre frentes |

## Códigos

| Código | Qué es | Ejemplo |
| --- | --- | --- |
| D-xx | Decisión | D-02 dónde se saca la huella |
| RF-xx | Requisito funcional | RF-04 reconocimiento |
| RNF-xx | Requisito no funcional | RNF-01 privacidad |
| Cn | Criterio de aceptación dentro de un RF o RNF | RF-04 · C2 |
| R1 a R9 | Regla de negocio | R5 llegada tarde |
| P-xx | Pendiente | P-02 hardware |

Las pruebas citan estos códigos en su nombre o en su marca (ver `CLAUDE.md`).

## Pendientes abiertos

- P-01 Fecha exacta de la clase.
- P-02 Placa ESP32-S3 y Raspberry que entregan: modelo, RAM, sistema, si trae microSD y con qué usuario se entra.

## Cómo cambia una spec

1. El cambio se propone en un PR con la versión nueva en el encabezado del archivo.
2. Si cambia una decisión, se agrega una línea en `decisiones.md`.
3. Si cambia un contrato, se sigue `contratos/README.md`.
