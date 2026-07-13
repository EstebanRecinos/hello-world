# ORBITA-LINK — Identidad de marca

## Concepto: la trayectoria

La sala de control no grita; anota. El elemento más distintivo del producto es su
**línea de trayectoria** — el timeline de hitos del tracking, la confirmación y el
progreso del wizard. La identidad entera se construye alrededor de ese trazo:
**un punto que avanza por una ruta trazada con precisión**. Logística, no ciencia
ficción: nada de estrellitas ni gradientes morados.

## Isotipo: "el waypoint"

Un arco circular de trazo uniforme, abierto en el cuadrante superior derecho, con
un **punto sólido ámbar** posado en el extremo — la carga saliendo por su
trayectoria. (`web/img/logo.svg`)

- Geometría pura (un arco + un círculo): a 16px se lee como favicon (el trazo y el
  punto crecen para conservar la lectura), a 512px como ícono de app.
- Monocromo primero: arco en tinta; el punto es lo único con color.
- Doble vida en el UI: el mismo motivo es el momento celebratorio de la reserva
  (el punto recorre el arco) y la familia de ilustraciones de estados vacíos.

**Wordmark**: `ORBITA—LINK` en monoespaciada con tracking amplio y el guion largo
en ámbar — el guion es el puente (link) entre tierra y órbita.

## Paleta: "bitácora de rampa"

Fuente de verdad: `design/tokens.json` (con los ratios de contraste documentados
por token). Resumen de roles:

| Token | Nombre | Rol |
|---|---|---|
| `color.ink` | Tinta de bitácora | Texto y trazos |
| `color.paper` | Papel técnico | Fondo |
| `color.surface` | Superficie | Tarjetas |
| `color.accent` | **Ámbar de rampa** | Acción, progreso, el punto del logo |
| `color.ok` | Verde de confirmación | Hechos consumados (semántico, no acento) |
| `color.warn` | Rojo de aviso | Errores y bloqueos |
| `color.focus` | Azul de foco | Solo el anillo de foco — nunca decorativo |

**Por qué el ámbar**: es el color de las luces de precaución de una rampa de
lanzamiento y de los paneles de telemetría — precisión operativa. Contraste
validado: 4.7:1 (claro) / 7.3:1 (oscuro). Todo color nuevo pasa por el mismo
validador (≥ 4.5:1 en ambos temas).

## Tipografía: sin webfonts, por diseño

- **Datos y marca** (`type.family.data`): pila monoespaciada del sistema.
  Precios, coordenadas, wordmark, etiquetas en mayúsculas espaciadas. La
  monoespaciada es la voz de telemetría y sus números tabulares alinean solos.
- **Texto** (`type.family.text`): pila del sistema. Cuerpo y formularios.
- Escala en `type.scale.*`: display 1.45rem/650 · sección 1.1rem/650 ·
  cuerpo 1rem/400 (nunca < 16px) · pista 0.9rem · dato 0.8rem/650.

Cero descarga de fuentes = carga instantánea con datos móviles limitados, cero
fallback silencioso, y la app nativa usa la mono/system de cada plataforma con la
misma jerarquía. La identidad vive en la geometría, el color y el trazo.

## Tono de voz

Ya establecido y no negociable: **llano, nivel de lectura de 12 años, en
español**. El estado siempre en palabras humanas primero ("Tu carga ya está
dentro del cohete"), lo técnico plegado bajo "Ver detalles técnicos". Los textos
no se "elevan" a marketing.

## Principios de diseño

1. **Una decisión por pantalla.** Si una vista pide dos cosas, son dos vistas.
2. **Lo técnico existe, pero plegado.** Nunca borramos el dato experto; lo
   guardamos bajo "Ver detalles técnicos".
3. **El estado, primero en palabras humanas.** `integrated` es un detalle; "Tu
   carga ya está dentro del cohete" es el mensaje.
4. **El precio nunca sorprende.** Siempre desglosado, siempre con el porqué,
   siempre con su fecha de vencimiento.
5. **Nada decora.** Cada trazo codifica información: la trayectoria marca
   progreso real, el ámbar acción real, el verde hechos consumados. Si un
   elemento no dice nada, se va.

## Movimiento

Tres duraciones como tokens (`motion.*`): 120ms hover/foco · 200ms transición
direccional entre pasos (avanzar desliza a la izquierda, volver a la derecha) ·
280ms el único momento celebratorio (el punto recorre el arco al confirmar la
reserva). Todo bajo 300ms; todo muere con `prefers-reduced-motion`.

## Estados vacíos y de error

Cuatro ilustraciones SVG inline, todas variaciones del arco del waypoint:
trayectoria punteada (sin cargas), punto esperando fuera del arco (sin vuelos),
arco cortado (sin conexión), punto con interrogación (enlace inválido). Cada una
acompaña un siguiente paso claro.
