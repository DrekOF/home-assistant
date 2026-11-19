<!--
Nombre: DOCS.md
Descripción: Documentación del complemento accesia_base, en la pestaña Documentación de Home Assistant OS.
Fecha de creación: 2026-11-18
Actualización: 2026-11-18
Autor: Equipo AccesIA
Versión: 1.0
-->

# AccesIA · base de datos

PostgreSQL 18 con pgvector para AccesIA (D-22). El complemento AccesIA · servidor se conecta a él en `local-accesia-base:5432`, por la red interna. No publica ningún puerto (D-16).

## Opciones

| Opción | Qué es |
| --- | --- |
| `clave_base` | La clave del dueño de la base, `accesia`. Es `POSTGRES_PASSWORD` de `infra/.env`, y va igual en AccesIA · servidor |

La clave solo cuenta la primera vez, cuando se crea la base. Para cambiarla después, hay que cambiarla también dentro de PostgreSQL.

## Datos y copias de seguridad

- Los datos quedan en `/data/postgres`. Ahí están las huellas.
- Las copias de seguridad de Home Assistant incluyen este complemento. Se hacen en frío, con la base detenida, y van siempre cifradas y nunca al repositorio. La del kit se toma sin inscripciones (`specs/modelo-datos.md`, Retención).
- Al terminar el semestre se desinstala el complemento con sus datos y se borran las copias.
