# BRD — Sistema de Gestión Operativa NovaRent (v1.1)

Base: BRD v1.0 (2 sept 2026). Esta versión refina el alcance para el PIA; los cambios están marcados con **[v1.1]**.

## 1. Contexto
NovaRent renta automóviles por día. El cliente reserva una **categoría**; la unidad física se asigna hasta la entrega en sucursal. Genera ingresos extra con seguros, conductores adicionales y otros servicios.

## 2. Problemas
Daños mal documentados · cobros confusos · inventario desactualizado (sobreventas) · retraso en avisar a limpieza.

## 3. Actores
Cliente · Agente de Renta · Personal de Patio · Personal de Limpieza · Administración.

## 4. Alcance
Reservaciones y disponibilidad real por categoría · registro digital de entrega (documentos y checklist) · cálculo automático de cargos extra · seguimiento del estado del vehículo (Rentado, En Limpieza, Disponible) · KPIs.
**Fuera de alcance [v1.1]:** cancelación de reservaciones, seguros y conductores adicionales, pagos reales (se usa un adaptador simulado).

## 5. Requerimientos de negocio
| ID | Prioridad | Descripción |
|---|---|---|
| BR-01 | Alto | Checklist digital con fotos al entregar y recibir. |
| BR-02 | Alto | Disponibilidad real: no rentar si la categoría está llena. |
| BR-03 | Alto | Motor de cargos con lista de precios oficial. |
| BR-04 | Bajo | Aviso a limpieza al devolver un auto. |

## 6. Reglas de negocio
| ID | Regla |
|---|---|
| RN-01 | Si no hay autos de la categoría reservada, se entrega una categoría superior sin costo extra (se conserva la tarifa original). |
| RN-02 | No se registra la entrega sin identificación, licencia vigente y pago/tarjeta. **[v1.1]** El checklist inicial también es requisito previo (glosario D023, US-07). |
| RN-03 | Una extensión solo se permite si la categoría tiene lugar en las fechas nuevas. **[v1.1]** Se valida contra el inventario de la categoría. |

## 7. Supuestos
Buena conexión en sucursales. **[v1.1]** Tarifario ficticio de demostración (ver ADR-004).

## 8. KPIs
−40 % en tiempo devolución → disponible · −60 % quejas por cobros de daños · 0 % sobreventas.
