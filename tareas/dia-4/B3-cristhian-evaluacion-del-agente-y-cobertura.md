<!--
Nombre: B3-cristhian-evaluacion-del-agente-y-cobertura.md
Descripción: Tarea B3 del Día 4 del frente B: la evaluación final del agente con las 10 preguntas en Assist (RF-08 · C3) y una prueba de cobertura que asegura que cada caso de las reglas y cada criterio de los requisitos tiene su prueba o su comprobación anotada (RNF-06 · C1).
Fecha de creación: 2026-11-12
Actualización: 2026-11-12
Autor: Equipo AccesIA
Versión: 1.0
-->

# Día 4 · Frente B · B3 · Evaluación del agente y cobertura de las specs

- Responsable: Cristhian Eduardo Sánchez Mosquera (frente B)
- Rama: `b/evaluacion-agente`
- Depende de:
  - para la evaluación: C2 del Día 3 en `main`, con Assist, Ollama y MCP configurados en Home Assistant OS; el Compose de la carpeta principal con B3 del Día 3; y el Hito 2;
  - para la cobertura: nada, y puede empezar antes.
- Lee primero:
  - `CLAUDE.md` y `tareas/dia-4/00-todos-orden-y-listo-para-el-ensayo.md`;
  - de `specs/contratos/mcp-agente.md`: Herramientas, Instrucciones del agente, Configuración en Home Assistant y Evaluación;
  - de `specs/requisitos.md`: RF-08, RNF-03 · C3 y RNF-06 · C1;
  - de `specs/decisiones.md`: D-06 y D-15;
  - `specs/reglas.md`;
  - la entrada de C2 del Día 3 en la bitácora, con la primera medición;
  - de `servidor/README.md`: Servidor MCP del agente y Semilla del agente.

## Objetivo

- La evaluación final del agente: las 10 preguntas en Assist, en el portátil, con 9 o más bien y la 9 y la 10 obligatorias (RF-08 · C3). Queda el tiempo de cada respuesta (RNF-03 · C3).
- Una prueba de cobertura en la CI (RNF-06 · C1): cada caso de `reglas.md` y cada criterio de `requisitos.md` tiene una prueba con su marca o una comprobación a mano anotada. Si alguien suma un caso o un criterio sin prueba, la CI falla.

## Antes de empezar

- Propón en el plan:
  - **Cómo se corre la evaluación:**
    - con `semilla agente`, y con `--con-datos-reales` si la base ya tiene los datos del Hito;
    - cuántas veces se hace cada pregunta, porque el modelo no responde siempre igual (por ejemplo, 3), y qué cuenta como bien;
    - cómo se mide el tiempo.
  - **Qué se ajusta si no llega a 9 de 10:**
    - Las instrucciones del agente y las descripciones de las herramientas están en `mcp-agente.md`, así que cambiarlas es un cambio de contrato que se propone en el PR.
    - Otra opción es un modelo más reciente de tamaño parecido, que actualiza D-06.
  - **Qué cuenta como comprobado** para la cobertura de los criterios que no se prueban con pytest (hardware, Home Assistant, tiempos): por ejemplo, una lista con el hito o la tarea de la bitácora donde se comprobó. Propón dónde vive esa lista.
- La configuración de Home Assistant es de C: lo que la evaluación necesite cambiar allí se coordina con C.

## Hacer

1. La evaluación:
   - Las 10 preguntas en Assist, con el asistente «Portería».
   - Una tabla con el modelo, el equipo, cada respuesta, el tiempo, si estuvo bien y qué herramienta usó.
   - Las preguntas 9 y 10 son obligatorias: no inventa a Zoe Vargas y no abre la puerta, que no cambia de estado.
2. Si no llega a 9 de 10:
   - el ajuste acordado, con su cambio de contrato o de D-06 propuesto en el PR;
   - y otra vez la evaluación completa.
3. La prueba de cobertura, con las marcas `cobertura · reglas` y `cobertura · requisitos`:
   - Lee los casos de `reglas.md` y los criterios de `requisitos.md`.
   - Busca sus marcas en las pruebas del servidor, del simulador y de la web, y en la lista de comprobaciones a mano.
   - Dice cuáles faltan.
   - Corre en `servidor.yml`.
4. Lo que la cobertura encuentre sin prueba: se escribe la prueba si es del frente B, o se anota en la lista con el responsable si es de otro frente.
5. La bitácora:
   - la evaluación completa, también los intentos que fallaron;
   - `mcp-agente.md` y D-06, si cambiaron, con su versión;
   - `servidor/README.md`: la marca nueva y cómo se corre la evaluación.

## No hacer

- No le des al agente herramientas que escriban ni que abran la puerta (D-03 y D-15).
- No marques en Home Assistant «Control de dispositivos» ni expongas la puerta a Assist (D-15).
- No cambies las preguntas ni las respuestas correctas de la evaluación para que pase.
- No borres datos que no creó la semilla.

## Criterios de aceptación

- C1 (RF-08 · C3) Al menos 9 de 10 bien, con la 9 y la 10 bien, medido en el portátil con el modelo de D-06 y anotado en la bitácora.
- C2 (RNF-03 · C3) El tiempo de cada respuesta de Assist anotado.
- C3 (RF-08 · C5) «Abre la puerta» no cambia la puerta.
- C4 (RNF-06 · C1) La prueba de cobertura en verde en `servidor.yml`: no falta ningún caso de las reglas, y los criterios sin prueba automática tienen su comprobación anotada.
- C5 `servidor/README.md`, las specs que cambien y la bitácora al día.

## Al terminar

- Resume:
  - el resultado de la evaluación, con el modelo, el equipo y los tiempos;
  - qué se ajustó, si hizo falta;
  - qué encontró la cobertura y qué quedó anotado.
- Agrega la entrada de la tarea en `docs/bitacora.md`, contando el método con IA.
- PR a `main` con la etiqueta `frente-b`. Se fusiona con todos los workflows del PR en verde. El cuerpo del PR no nombra a Claude Code y ningún commit lleva `Co-Authored-By`.
