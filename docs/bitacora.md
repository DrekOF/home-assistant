<!--
Nombre: bitacora.md
Descripción: Bitácora de AccesIA: qué se hizo, quién, cómo (incluido el método con IA) y qué quedó pendiente.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Bitácora

Una entrada por tarea terminada, la más reciente arriba. Aquí se cuenta el método con IA; los commits y los PR no lo mencionan.

## Plantilla

```markdown
## AAAA-MM-DD · Día N · Tarea
- Quién:
- Qué: lo que quedó funcionando.
- Cómo: qué se le pidió a Claude Code, qué se revisó o corrigió a mano y qué decisiones se tomaron.
- Pruebas: cuáles corrieron y su resultado.
- Cambios de contrato o de specs: cuáles y por qué (o «ninguno»).
- Pendiente:
```

## 2026-11-11 · Antes del Día 1 · Kit base del repositorio

- Quién: Cristhian Sánchez, para todo el equipo.
- Qué: `CLAUDE.md`, specs (enunciado, decisiones, arquitectura, requisitos, reglas, modelo de datos, consentimiento y plan), contratos (API, MQTT, agente y base de datos), tareas del Día 1, esta bitácora, la guía del día de clase y los diagramas.
- Cómo: las specs y los contratos se redactaron con Claude (claude.ai) a partir del levantamiento y del plan del proyecto. El equipo los revisa y los acepta en la tarea 00 del Día 1.
- Pruebas: `openapi.yaml` pasó `openapi-spec-validator`; `base-de-datos.sql` se cargó en un PostgreSQL 16 de prueba (con `vector` y `uuidv7` simulados) y se comprobaron restricciones, vistas, permisos del agente y borrado en cascada.
- Cambios de contrato o de specs: decisiones D-12 a D-19 propuestas.
- Pendiente: P-01 fecha de la clase; P-02 hardware que entregan; cargar el esquema en PostgreSQL 18 con pgvector (tarea B del Día 1).
