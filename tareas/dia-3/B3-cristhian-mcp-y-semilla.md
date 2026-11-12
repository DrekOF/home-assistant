<!--
Nombre: B3-cristhian-mcp-y-semilla.md
Descripción: Tarea B3 del Día 3 del frente B: el servidor MCP del agente con sus cinco herramientas de solo lectura, el servicio mcp en Docker Compose y el comando semilla agente.
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 3 · Frente B · B3 · Servidor MCP y semilla del agente

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/mcp-agente`
- Depende de:
  - B1 del Día 3 en `main`, porque la semilla califica las llegadas con R5;
  - nada de B2: B2 y B3 van en paralelo, y la puede correr otra sesión libre.
- Lee primero: `CLAUDE.md`; `tareas/dia-3/00-todos-orden-e-hito-2.md`; `specs/contratos/mcp-agente.md` completo; `specs/modelo-datos.md` (Usuarios de la base y Vistas del agente); `specs/requisitos.md` (RF-08); `specs/decisiones.md` (D-06, D-15, D-16 y D-21); `specs/arquitectura.md` (Piezas, Servicios de Docker Compose y Configuración); `servidor/README.md`.

## Objetivo

Home Assistant puede preguntarle al servidor MCP de AccesIA, con sus cinco herramientas de solo lectura, y el comando `semilla agente` crea los datos de la evaluación de las 10 preguntas. Con esto C2 conecta Assist y hace la primera medición.

## Antes de empezar

- El SDK oficial `mcp` de Python (FastMCP), con su versión fijada en `uv.lock`, como parte del mismo paquete del servidor (`arquitectura.md`, Piezas).
- Propón en el plan:
  - cómo arranca: un comando del paquete para el servicio `mcp` de Compose, con la misma imagen y otro comando;
  - el encabezado `Host`:
    - el SDK lo valida;
    - hay que aceptar `mcp:8001` y la dirección del portátil en el escenario 2 (D-21), por ejemplo `192.168.137.1:8001`;
    - si hace falta una variable, va en `arquitectura.md` (Configuración) y en `infra/.env.example`;
  - cómo convive la semilla con las personas reales del Hito 1. Por ejemplo:
    - solo en una base sin personas, o con una opción que lo confirme;
    - nunca borra datos que no creó ella.

## Hacer

1. Servidor MCP (`mcp-agente.md`, Servidor MCP):
   - Nombre `AccesIA`, Streamable HTTP en `/mcp`, puerto 8001.
   - Usa el usuario `agente` de la base, con su clave de `AGENTE_DB_PASSWORD`, que solo lee las tres vistas del agente.
   - Cada herramienta corre en una transacción `READ ONLY` con `statement_timeout` de 3 s.
   - Sin autenticación (D-16).
2. Las cinco herramientas, tal como las describe el contrato: `buscar_persona`, `asistencia_del_dia`, `llegadas_tarde`, `accesos_de_persona` y `desconocidos_recientes`.
   - Nombres, descripciones y parámetros en español.
   - Fechas como `AAAA-MM-DD`, `hoy`, `ayer` o `antier`, calculadas en hora de Colombia. Horas como `HH:MM`, o como `AAAA-MM-DD HH:MM` cuando una lista mezcla días.
   - Los límites del contrato: 10 personas, 31 días, 50 accesos, de 1 a 168 horas y 10 horas en `ultimos`.
   - Un error se devuelve como `{"error": "texto"}`, nunca como excepción.
   - Nunca devuelven documentos, huellas ni similitudes (RNF-01 · C4).
3. Servicio `mcp` en `infra/compose.yaml`:
   - la misma imagen `accesia-servidor`, con su comando;
   - depende de `postgres` y no se publica fuera de la red de Docker (D-16);
   - `compose.escenario2.yaml`, de C2, lo publica en la red del hotspot.
4. Comando `semilla agente`: crea las seis personas, el horario «Clase todos los días» (siete bloques a las 07:00 con 10 min de tolerancia), los consentimientos, la cámara `entrada` y los eventos de la tabla de la evaluación, con fechas relativas a hoy. Las llegadas se califican con la función de R5 de B1.
5. Pruebas, cada una con su marca:

   | Marca | Casos |
   | --- | --- |
   | `contrato agente · <herramienta>` | Cada herramienta con los datos de la semilla, sin modelo: lo que devuelve, sus límites y sus errores |
   | `contrato agente · preguntas` | Para las preguntas 1 a 9 de la evaluación, la herramienta esperada devuelve la respuesta correcta |
   | `RF-08 · C1` | Un cliente MCP real, por Streamable HTTP, lista las cinco herramientas y las llama |
   | `RF-08 · C4` | Las herramientas no pueden escribir: la conexión es de solo lectura y el usuario `agente` no puede tocar las tablas |
   | `RNF-01 · C4` | Ninguna respuesta lleva documentos, huellas ni similitudes |

6. `servidor/README.md` (comandos y marcas), `infra/README.md` (servicio `mcp` y semilla) y la sección Comandos de `CLAUDE.md`.

## No hacer

- No configures Home Assistant ni Ollama: son de C2.
- No des herramientas que escriban ni que abran la puerta (D-03 y D-15).
- No publiques el puerto 8001 en `compose.yaml`: solo `compose.escenario2.yaml` lo hace (D-16 y D-21).
- No cambies `mcp-agente.md` sin proponerlo en el PR.

## Criterios de aceptación

- C1 (RF-08 · C1) Las cinco herramientas funcionan por MCP, con lo que devuelve el contrato.
- C2 (RF-08 · C4; D-15) Todo es de solo lectura, con el usuario `agente`, y nada devuelve documentos, huellas ni similitudes.
- C3 (`mcp-agente.md` · Evaluación) `semilla agente` crea los datos de la tabla, y las herramientas responden bien las preguntas 1 a 9.
- C4 El servicio `mcp` arranca con Docker Compose y acepta el encabezado `Host` de `mcp:8001` y del portátil.
- C5 (RNF-06 · C3) `uv run pytest` y `servidor.yml` en verde.
- C6 `servidor/README.md`, `infra/README.md`, `CLAUDE.md`, las specs que cambien y la bitácora al día.

## Al terminar

- Resume:
  - qué hiciste y qué pruebas corriste, con su resultado por marca;
  - qué decidiste sobre el encabezado `Host` y la semilla con datos reales.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-b`. Se fusiona con todos los workflows del PR en verde. Cuando esté en `main`, avisa a C para conectar Assist en C2.
- El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
