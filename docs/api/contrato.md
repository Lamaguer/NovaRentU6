# Contrato de la API (para la interfaz)
Los errores siempre llegan como `{"ok": false, "mensaje": "<texto en español para el usuario>", "faltantes": [...]}`. **La interfaz solo muestra `mensaje`** (y `faltantes` como lista cuando exista). Swagger: `/docs` · OpenAPI: `/openapi.json` (copia en `openapi.json`).

| Método y ruta | Historia / regla | Cuerpo / parámetros | Éxito |
|---|---|---|---|
| GET `/api/sucursales` | — | — | `[{id, nombre}]` |
| GET `/api/disponibilidad` | US-01 | `sucursal_id, inicio, fin` | solo categorías con lugar: `{categoria, lugares, tarifa_diaria, total}` |
| POST `/api/reservaciones` | US-02, US-03, BR-02 | `cliente, sucursal_id, categoria, inicio, fin` | 201 con `folio`, `total`, `mensaje` |
| GET `/api/reservaciones`, `/{folio}` | — | — | reservaciones |
| POST `/api/rentas` | abrir contrato | `folio` | 201 renta `PENDIENTE` |
| POST `/api/rentas/{id}/upgrade` | RN-01, US-14 | `categoria_destino` | misma tarifa, nueva categoría |
| POST `/api/rentas/{id}/entrega` | RN-02, US-04..07 | `identificacion_valida, licencia_vigente, tarjeta, combustible_octavos, kilometraje, danos[]` | renta `ENTREGADO` + `vehiculo_id` |
| POST `/api/rentas/{id}/extension` | RN-03, US-08 | `nueva_fin` | renta con nueva fecha |
| POST `/api/rentas/{id}/devolucion` | US-09..US-11, BR-03 | `combustible_octavos, kilometraje, danos[], fecha_hora?` | `DEVUELTO` + `cargos` + `comparacion` |
| GET `/api/limpieza` | US-12, BR-04 | — | vehículos `EN_LIMPIEZA` |
| POST `/api/vehiculos/{id}/limpieza-terminada` | US-13 | — | vehículo `DISPONIBLE` |
| GET `/api/rentas`, `/api/rentas/{id}`, `/api/vehiculos` | — | — | listados |
| GET `/api/kpis` | US-15 | — | `sobreventas` (meta 0), `minutos_devolucion_a_disponible`, `cobros_por_danos`, `cargos_por_concepto`, estados |

**Demo:** tarjeta que termina en `0000` = pago rechazado. Sucursal **Apodaca**, categoría **ECONOMICO**: la única unidad está en limpieza, la entrega pide upgrade (RN-01).
