<!--
Nombre: DESIGN.md
Descripción: Sistema visual de la web de AccesIA: dirección, tokens, componentes, movimiento, accesibilidad y qué skill apoya cada decisión.
Fecha de creación: 2026-11-11
Actualización: 2026-11-11
Autor: Equipo AccesIA
Versión: 1.0
-->

# Sistema visual de la web

La fuente de verdad de los valores es `src/estilos/tokens.css`; este documento explica para qué sirve cada uno. Si un valor cambia, se cambia allá y aquí.

## Dirección

Sobria y clara, tipo panel de trabajo. La web es una herramienta: quien la usa está haciendo una tarea (crear a una persona, registrar su consentimiento, inscribirla), y en la demo se ve en un portátil y en un proyector de salón.

- **Modo:** Operate de impeccable. Primero se ve y se usa bien; la identidad está en los detalles.
- **Tema claro:** el salón tiene luz y los proyectores lavan los fondos oscuros. Por eso `color-scheme: light`.
- **Un solo color de acento** (azul petróleo) para la acción principal, la selección y el foco. Los colores de estado (verde, ámbar, rojo y gris) van siempre con ícono y texto.
- **Un momento con carácter:** el panel de color del inicio de sesión. Lo demás es neutro.

## Tipografía

- **Atkinson Hyperlegible Next** (variable, de Fontsource, servida por la propia web) para todo. La diseñó el Braille Institute para leerse bien con poca visión y de lejos, que es la situación del proyector. Su cero lleva barra para no confundirse con la O.
- **Atkinson Hyperlegible Mono** solo para documentos y códigos, que son datos que se comparan carácter por carácter.
- Escala fija de 14, 16, 19, 23 y 28 px (`--texto-s` a `--texto-xxl`), con razón cercana a 1,2. El texto corrido es de 16 px y nunca baja de 14 px.
- Pesos: 400 para el texto, 600 para etiquetas y botones, y 700 para títulos.
- Los números de tablas y conteos usan `tabular-nums`.

## Color

| Token | Valor | Uso |
| --- | --- | --- |
| `--color-fondo` | `#f3f6f8` | Fondo de la página |
| `--color-superficie` | `#ffffff` | Paneles, tablas, campos y diálogos |
| `--color-lateral` | `#e6ecf1` | Barra lateral |
| `--color-texto` | `#111a22` | Texto principal |
| `--color-texto-2` | `#44525f` | Etiquetas, ayudas y texto secundario |
| `--color-acento` | `#0b5e78` | Acción principal, enlaces, selección y anillo de foco |
| `--color-acento-oscuro` | `#084a5f` | Botón principal al pasar el mouse |
| `--color-acento-suave` | `#dcecf2` | Opción elegida, aviso informativo y selección de texto |
| `--color-sobre-acento` y `-2` | `#ffffff`, `#d9ebf1` | Texto sobre el acento (el segundo, para el secundario) |
| `--color-borde` | `#7a8795` | Bordes de campos y botones secundarios |
| `--color-marcador` | `#5f6c78` | Texto de ejemplo dentro de los campos |
| `--color-divisor` | `#d5dde4` | Líneas de tablas y bordes de paneles |
| `--color-ok` y `-fondo` | `#17663a`, `#e2f2e8` | Vigente, activa, confirmaciones |
| `--color-aviso` y `-fondo` | `#7a4a00`, `#fcefd4` | Simulacro y advertencias |
| `--color-error`, `-oscuro` y `-fondo` | `#a61b12`, `#8a160f`, `#fce5e3` | Errores y acciones que borran datos |
| `--color-neutro` y `-fondo` | `#44525f`, `#e6ecf1` | Sin consentimiento, inactiva, revocado y botones deshabilitados |

Contraste AA probado en `src/logica/contraste.test.ts`: cada par de texto que aparece en pantalla llega a 4,5:1 y cada borde de control o anillo de foco llega a 3:1. El par más justo es el borde de los campos sobre el fondo, con 3,38:1.

## Espacio y tamaños

- Rejilla de 8 px, con 4 px para ajustes finos: `--e-1` a `--e-7` son 4, 8, 16, 24, 32, 48 y 64 px.
- Barra lateral de 224 px y contenido de hasta 1200 px. A 1280 px de ancho, el contenido mide 960 px.
- Botones, campos y filas de tabla miden 44 px: se ven desde el fondo del salón y se tocan bien en una pantalla táctil.
- Radios de 6 px (controles), 8 px (paneles) y 12 px (diálogos).
- Sombra solo en lo que flota (el diálogo). Los paneles se separan con borde, no con sombra.

## Movimiento

Corto, con salida rápida, y solo cuando dice algo. Nada se mueve solo.

- Curva `cubic-bezier(0.23, 1, 0.32, 1)` y duraciones de 120, 150 y 200 ms.
- Los botones se encogen a `scale(0.97)` al presionarlos.
- El diálogo entra con opacidad y escala desde 0,97 (`@starting-style`) y sale igual. Su fondo se oscurece.
- Los segmentos de la barra de avance se llenan con `scaleX` desde la izquierda.
- Los esqueletos laten mientras carga.
- Con `prefers-reduced-motion`, todo queda quieto.
- No hay `transition: all`. Se anima `transform` y `opacity`, más el color en los cambios de estado al pasar el mouse.

## Componentes

| Componente | Archivo | Reglas |
| --- | --- | --- |
| Botón | `Boton.tsx` | Variantes primario, secundario, peligro, peligro suave y texto. Un solo primario por vista. Mientras la petición corre, gira y dice qué hace («Guardando…»). `BotonEnlace` es un enlace con forma de botón, para navegar. |
| Campo | `Campo.tsx` | Etiqueta visible arriba; ayuda y error debajo, unidos al control con `aria-describedby`. Los errores salen al enviar, y el foco va al primero. |
| Insignia de estado | `InsigniaEstado.tsx` | Color, ícono y texto. |
| Aviso | `Aviso.tsx` | Información, éxito, advertencia o error, con acción opcional («Reintentar», «Deshacer»). Los errores que interrumpen usan `role="alert"`; las confirmaciones van en una región `role="status"`. |
| Diálogo de confirmación | `DialogoConfirmacion.tsx` | `<dialog>` nativo, solo para lo que no se puede deshacer (revocar) o lo que se pierde (salir sin guardar). El foco empieza en «Cancelar» y Escape cierra. |
| Esqueleto | `Esqueleto.tsx` | Filas grises del mismo alto que las reales, para que la tabla no salte. |
| Vacío | `Vacio.tsx` | Dice qué pasó y qué hacer, con la acción a la mano. |
| Barra de avance | `BarraAvance.tsx` | Un segmento por muestra, «Muestra 3 de 5» con `aria-live` y `role="progressbar"`. La usará la inscripción (RF-03 · C6). |
| Marco | `Marco.tsx` | Salto al contenido, barra lateral con la sección actual marcada (`aria-current`), cinta del simulacro y cierre de sesión. Al cambiar de pantalla, el foco va al contenido. |

## Estados

Cada pantalla tiene sus estados de carga (esqueleto), vacío (`Vacio`), error (`Aviso` con «Reintentar») y éxito (aviso en la región de estado). Desactivar a una persona no pide confirmación porque se puede deshacer en el mismo aviso. Revocar el consentimiento sí la pide, porque borra las huellas.

## Accesibilidad

Revisada con las reglas de web-design-guidelines fijadas en el commit `434b7f9` (`.claude/skills/web-design-guidelines/command.md`).

- Todo se usa con teclado: salto al contenido, foco visible con `:focus-visible` (2 px en el acento) y orden de tabulación igual al de lectura. Lo prueba Playwright.
- Formularios: `label` en cada control, `name` y `autocomplete`, sin corrector en correos y documentos, y ejemplos que terminan en «…».
- La dirección guarda el estado de la lista (`q`, `estado` y `pagina`). La paginación usa enlaces.
- Fechas y horas con `Intl.DateTimeFormat`, en `es-CO` y `America/Bogota`. La hora y «a. m.» van con espacio duro, para que no se partan de línea.
- Las superficies del navegador también llevan los colores del sistema: selección de texto, cursor, casillas (`accent-color`), barra de desplazamiento y subrayados.

Dos diferencias justificadas con esas reglas:

- **Mayúsculas en títulos y botones:** las reglas piden *Title Case*, que es del inglés. En español solo va en mayúscula la primera palabra.
- **«Inscribir» es un botón y no un enlace:** debe poder deshabilitarse sin consentimiento vigente (RF-02 · C4), y un enlace no se deshabilita.

## Con qué skill se apoya cada decisión

| Skill | Qué aportó |
| --- | --- |
| impeccable | El modo Operate (familiaridad, densidad y consistencia), el piso de calidad de `craft-floor.md` (estados, superficies del navegador, contraste y foco) y elegir el tema por el lugar de uso. Se usaron solo sus guías; su ejecutable no se corrió. |
| refactoring-ui | Jerarquía con tamaño, peso y color sin multiplicarlos; etiquetas en segundo plano frente a los valores; escala de espacio de 4 a 64 px; grises con un toque de azul y sombras solo para lo que flota. |
| Emil Kowalski (`emil-design-eng` y los de animación) | Qué se anima y qué no, la curva de salida, duraciones por debajo de 300 ms, `scale(0.97)` al presionar, entradas desde 0,97 y nunca desde 0, y `prefers-reduced-motion`. |
| frontend-design | Partir del tema (control de acceso para una demo en clase) y no de una plantilla; el panel de color de la entrada como único momento propio. |
| taste-skill | Un solo estilo de botón relleno por vista, etiquetas visibles, errores debajo de cada campo y el foco en el primero. Su parte de páginas de presentación queda para la página de scroll storytelling del plan. |
| web-design-guidelines | La revisión final de accesibilidad, formularios, teclado, tipografía e i18n con su copia fija. |
