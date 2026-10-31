# ADR-003 Inventario por categoría, medido día por día; extensión validada contra la categoría
**Contexto.** Se reserva una categoría, no una unidad (D002, D006); RN-03 habla de "ese auto".
**Decisión.** `InventarioCategoria` cuenta lugares apartados por cada día del periodo [inicio, fin). Una reserva que empieza el día en que otra termina no choca. La extensión excluye la propia reserva al contar.
**Alternativas.** Contar traslapes entre reservas (sobrerrechaza); validar contra una unidad física (no existe al reservar).
**Consecuencias.** Se evitan sobreventas sin bloquear casos válidos.
