# Nota de traspaso — equipo de la app nativa

## Qué consumir

- **`design/tokens.json`** (W3C Design Tokens) es la única fuente de verdad de
  color (temas claro/oscuro), espaciado, radios, tamaños táctiles, tipografía y
  duraciones de movimiento. El CSS web se genera con
  `python -m scripts.gen_tokens`; para React Native / SwiftUI / Compose,
  generen su propio artefacto desde el mismo JSON (Style Dictionary lo lee
  directamente).
- **`design/BRAND.md`**: concepto, isotipo, principios y tono de voz.
- **`web/img/logo.svg`** + iconos PNG 192/512/maskable ya exportados.
- **Catálogo vivo en `/design`**: cada componente con sus estados, tal como
  corre en producción.

## Componentes a replicar (en orden de valor)

1. **Línea de trayectoria (timeline)** — el componente identitario: verde =
   pasado, ámbar = estás aquí, gris = futuro; siempre con hitos en palabras.
2. **Tarjeta de opción** (destino, permisos) y **tri-estado** Sí/No/No estoy
   segura/o — "no sé" nunca bloquea.
3. **Pills de estado** con el mapeo palabra-humana → estado del sistema
   (ver `STATE_WORDS` en `web/app.js`).
4. **Desglose de precio en palabras** (ver `MULT_WORDS` en `web/app.js`) con la
   fecha de congelación (`expires_at` de la quote).
5. Stepper de progreso, campo con error accionable, toast.

## Backend listo (no cambia)

Todo el círculo comercial está servido por `/api/v1` (OpenAPI en `/docs`):

- `POST /auth/dev-token` → se reemplazará por IdP; la app solo necesita un JWT
  con `sub` + `role`.
- `POST/PATCH /manifests` — borradores parciales (solo `name` obligatorio);
  `is_complete`/`missing_fields` en cada respuesta para pintar el progreso.
- `GET /manifests/{id}/matches` — opciones rankeadas; 409 con
  `missing_fields` si falta algo (llevar al usuario al paso correcto).
- `POST /manifests/{id}/quotes` y `/book` — la quote trae `expires_at`
  ("precio congelado hasta…"); reservar una expirada/invalidada da 409 con
  mensaje accionable (mapeo en `traducir()` de `web/app.js`).
- `GET /tracking/{token}` — público, sin auth; la app debe cachear el último
  estado y mostrarlo offline con aviso honesto (patrón ya implementado en
  `vTracking`).

## Reglas que la app nativa hereda sin excepción

- Accesibilidad: objetivos ≥ 44pt, contraste ≥ 4.5:1 (ratios en tokens.json),
  foco/VoiceOver/TalkBack en todo el flujo, `reduce motion` respetado.
- Dinero siempre en centavos enteros (formatear en cliente), UTC siempre.
- Textos en lenguaje llano — no inventar copy nuevo sin pasar por el tono de
  voz de BRAND.md.
