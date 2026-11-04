# Principios SOLID y patrones de diseño aplicados

Cada afirmación apunta a código verificable. Donde un principio se cumple solo en parte, se dice.

## SOLID
| Principio | Evidencia en el código | Matiz |
|---|---|---|
| **S** Responsabilidad única | `CalculadoraCargos` solo calcula cargos; `InventarioCategoria` solo controla capacidad; `mensajes.py` solo traduce errores; el dominio no sabe de HTTP ni de SQL. | `ServicioNovaRent` concentra todos los casos de uso en una clase: podría dividirse por módulo (reservas, rentas, limpieza). |
| **O** Abierto/cerrado | Una regla nueva se agrega como otra `Specification` y se combina con `&`, `\|` o `~` sin tocar las existentes. El tarifario (`politicas.py`) cambia sin modificar la lógica de cargos. | — |
| **L** Sustitución de Liskov | Todas las Specifications (`LicenciaSpec`, `Compuesta`, `Not`...) se usan donde se espera una `Specification`. | — |
| **I** Segregación de interfaces | La pasarela expone un solo método (`retener_deposito`); `Specification` expone solo `is_satisfied_by`. | — |
| **D** Inversión de dependencias | El dominio no importa infraestructura; `ServicioNovaRent` recibe la `session_factory` y la pasarela por constructor, y en pruebas se sustituyen. | La pasarela tiene un valor por defecto concreto (`PasarelaPagoSimulada`) y no hay una interfaz explícita; un `Protocol` lo formalizaría. |

## Patrones
| Patrón | Dónde | Por qué |
|---|---|---|
| **Aggregate / Entity (DDD)** | `Reservacion`, `Renta`, `Vehiculo`, `InventarioCategoria` | Cada agregado protege sus invariantes y se guarda en una transacción. |
| **Value Object** | `Dinero`, `PeriodoRenta`, `EstadoFisico`, `RequisitosEntrega`, `Cargo` | Inmutables y validados al crearse: no puede existir un monto negativo ni un periodo invertido. |
| **Specification** | `src/domain/specifications.py` | RN-01, RN-02 y RN-03 son condiciones que se combinan; así se prueban por separado y la entrega puede listar exactamente qué falta. |
| **State Machine** | `Vehiculo` (tabla de transiciones), `Renta`, `Reservacion` | El BRD define estados del vehículo; las transiciones inválidas lanzan error. |
| **Domain Events** | `Evento` y 8 eventos persistidos | Alimentan la limpieza (BR-04) y los KPIs (US-15) sin acoplar módulos. |
| **Unit of Work** | `UnitOfWork` | Una transacción por caso de uso: commit si todo sale bien, rollback si el dominio rechaza. |
| **Repository** | `Repositorio*` | Reconstruye agregados desde la base y los guarda; el dominio no conoce SQLAlchemy. |
| **Adapter** | `PasarelaPagoSimulada` | El BRD no incluye un proveedor de pagos real; el adaptador permite simular cobros sin mover dinero. |
| **Domain Service** | `CalculadoraCargos` | El cálculo involucra varias entidades y no pertenece a ninguna. |
