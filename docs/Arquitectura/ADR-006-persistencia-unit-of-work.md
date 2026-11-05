# ADR-006 Persistencia con Unit of Work, repositorios por agregado y bloqueo de fila
**Contexto.** Cada caso de uso toca varios agregados (por ejemplo, entregar actualiza la renta, el vehículo y los eventos). Si una regla de negocio falla a la mitad, no puede quedar nada guardado. Además, BR-02 exige cero sobreventas aunque dos reservaciones lleguen al mismo tiempo.
**Decisión.**
- `UnitOfWork` abre una sesión por caso de uso: hace commit solo si todo sale bien y rollback si el dominio lanza un error.
- Hay un repositorio por agregado (reservaciones, rentas, vehículos, inventarios, eventos). Reconstruyen los objetos de dominio desde la base, así el dominio no conoce SQLAlchemy.
- El inventario de cada categoría se carga con `SELECT ... FOR UPDATE` (`bloquear=True`) al reservar, para que dos reservaciones simultáneas sobre la misma categoría se atiendan una tras otra.
- El dinero se guarda como `Numeric(12,2)` y se maneja como `Decimal`, nunca como `float`.
- Los eventos de dominio se persisten en una tabla y alimentan los indicadores (US-15).
- Las pruebas de integración corren contra SQLite en memoria en local y contra PostgreSQL en el pipeline de CI.
**Alternativas.**
- Un único servicio que haga commit en cada método: no garantiza atomicidad entre agregados.
- Guardar el dinero como texto o `float`: pierde precisión o impide sumar en la base.
- Bloqueo optimista con versión de fila: más código para un riesgo que el bloqueo de fila ya cubre.
**Consecuencias.**
- (+) Un rechazo del dominio no deja datos a medias (prueba: `test_br02_sobreventa_rechazada_y_nada_se_guarda`).
- (+) La sobreventa concurrente se evita en PostgreSQL.
- (−) En SQLite el bloqueo de fila no tiene efecto; la garantía de concurrencia solo se valida en PostgreSQL.
- (−) Cada caso de uso abre su propia transacción, así que no hay transacciones largas entre varias pantallas.