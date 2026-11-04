# Escenarios Gherkin alternos y de error

Complementan los criterios de aceptación de `user stories - novarent.pdf`, que solo cubren el camino feliz. Cada escenario indica el mensaje **exacto** que ve el usuario y la prueba automatizada que lo verifica.

## US-01 · Consulta de disponibilidad
```gherkin
Scenario: Una categoría llena no se muestra
  Given la categoría PREMIUM de la sucursal tiene todos sus lugares apartados del 10 al 12 de noviembre
  When el cliente consulta disponibilidad para esas fechas
  Then el sistema no muestra la categoría PREMIUM
  And sí muestra las categorías con al menos un lugar libre todos los días
```
Prueba: `test_us01_disponibilidad_oculta_categorias_llenas`

```gherkin
Scenario: Fecha de devolución anterior o igual a la de recogida
  Given el cliente eligió recoger el 15 de noviembre
  When elige devolver el 15 de noviembre o antes
  Then el sistema responde "La fecha de devolución debe ser posterior a la de inicio."
```
Prueba: `test_no_encontrado_validacion_y_estado_sin_tecnicismos`

## US-02 · Confirmación de reservación
```gherkin
Scenario: Reservación con fecha de inicio pasada
  Given hoy es 2 de noviembre
  When el cliente intenta reservar con inicio el 1 de noviembre
  Then el sistema responde "La fecha de inicio no puede ser anterior a hoy."
  And no se genera folio
```
Prueba: `test_errores_llegan_en_lenguaje_de_cliente`

```gherkin
Scenario: Reservación sin nombre de cliente
  When el cliente confirma sin escribir su nombre
  Then el sistema responde "Escribe el nombre del cliente."
```
Prueba: `test_errores_llegan_en_lenguaje_de_cliente`

## US-03 · Bloqueo de inventario (BR-02, cero sobreventas)
```gherkin
Scenario: La última unidad ya fue apartada
  Given la categoría tiene capacidad 1 y ya existe una reservación confirmada del 10 al 15
  When otro cliente reserva la misma categoría del 12 al 14
  Then el sistema responde "No hay unidades disponibles en esas fechas. Prueba otra categoría o cambia las fechas."
  And no se guarda ninguna reservación nueva
```
Pruebas: `test_br02_sobreventa_rechazada`, `test_br02_sobreventa_rechazada_y_nada_se_guarda`

```gherkin
Scenario: Límite — la otra reservación empieza el día que esta termina
  Given la categoría tiene capacidad 1 y una reservación termina el 15
  When otro cliente reserva a partir del 15
  Then la reservación se confirma, porque el día de devolución queda libre
```
Prueba: `test_br02_limite_reserva_que_empieza_el_dia_de_devolucion`

## US-05 · Depósito y método de pago
```gherkin
Scenario: La pasarela rechaza la tarjeta
  Given los documentos del cliente fueron validados
  When el agente captura una tarjeta que la pasarela rechaza
  Then el sistema responde "No se puede entregar el vehículo todavía. Falta el pago / deposito autorizado."
  And la renta sigue en estado PENDIENTE
  And no se asigna ningún vehículo
```
Prueba: `test_us05_pago_rechazado_por_pasarela_simulada`

## US-07 · Bloqueo por requisitos faltantes (RN-02)
```gherkin
Scenario: Faltan licencia, pago y checklist
  Given el agente intenta cambiar la renta a "Entregado"
  When solo se confirmó la identificación
  Then el sistema bloquea la entrega
  And muestra la lista: licencia vigente, pago o depósito autorizado y checklist inicial
  And la renta y el vehículo conservan su estado
```
Pruebas: `test_entrega_incompleta_devuelve_faltantes_legibles`, `test_rn02_entrega_bloqueada_no_cambia_nada`

```gherkin
Scenario: Entrega duplicada
  Given una renta ya está ENTREGADA
  When el agente intenta entregarla otra vez
  Then el sistema responde "Esa acción no está disponible en el estado actual de la renta."
```
Prueba: `test_no_se_entrega_dos_veces`

## US-08 · Extensión de renta (RN-03)
```gherkin
Scenario: Otra reservación ocupa el último lugar de la categoría
  Given la renta termina el 15 y otro cliente tiene reservada la categoría a partir del 15
  When el cliente pide extender hasta el 17
  Then el sistema responde "No es posible extender la renta: la categoría ya está reservada por otro cliente en esas fechas."
  And la fecha de devolución sigue siendo el 15
```
Prueba: `test_extension_bloqueada_se_explica_al_cliente`

```gherkin
Scenario: Límite — la otra reservación empieza justo cuando termina la extensión
  When el cliente extiende hasta el día en que empieza la otra reservación
  Then la extensión se aprueba
```
Prueba: `test_rn03_limite_otra_reserva_inicia_en_la_nueva_fecha_fin`

```gherkin
Scenario: Nueva fecha que no amplía la renta
  When el cliente elige una fecha igual o anterior a la devolución actual
  Then el sistema responde "La nueva fecha debe ser posterior a la fecha de devolución actual."
```
Prueba: `test_upgrade_y_extension_por_api`

## US-10 y US-11 · Cargos por devolución (BR-03)
```gherkin
Scenario Outline: Límites del cargo por retraso
  Given el límite de devolución es las 12:00 del último día
  When el vehículo se devuelve a las <hora>
  Then el cargo por retraso es <cargo>

  Examples:
    | hora  | cargo   |
    | 12:00 | $0.00   |
    | 12:01 | $150.00 |
    | 14:30 | $450.00 |
```
Prueba: `test_us10_retraso_exacto_no_cobra_y_un_minuto_cobra_una_hora`

```gherkin
Scenario: Kilometraje exactamente en el límite incluido
  Given la renta incluye 200 km por día durante 5 días
  When el cliente recorre 1000 km
  Then no se cobra kilometraje excedido
  When recorre 1001 km
  Then se cobran $4.00
```
Prueba: `test_us10_kilometraje_limite_1000_incluidos`

```gherkin
Scenario: Kilometraje final menor al de entrega
  When el agente captura un kilometraje menor al registrado al entregar
  Then el sistema responde "El kilometraje final no puede ser menor al de entrega."
```
Prueba: `test_devolucion_validaciones`

## US-14 · Upgrade sin costo (RN-01)
```gherkin
Scenario: No hay unidad física de la categoría reservada
  Given el inventario lógico tiene lugar pero la única unidad está en limpieza
  When el agente intenta entregar sin upgrade
  Then el sistema responde "No hay unidades físicas de la categoría reservada. Autoriza un upgrade a una categoría superior sin costo extra."
  When el agente autoriza un upgrade a SUV
  Then la entrega se realiza con un SUV y la tarifa original no cambia
```
Pruebas: `test_upgrade_y_extension_por_api`, `test_us14_upgrade_conserva_tarifa_y_entrega_categoria_superior`

```gherkin
Scenario: Upgrade no permitido
  Given aún hay unidades físicas disponibles en la categoría reservada
  When el agente intenta autorizar un upgrade
  Then el sistema responde "El upgrade solo aplica cuando no quedan unidades de la categoría reservada y hacia una categoría superior."
```
Pruebas: `test_rn01_upgrade_rechazado_si_hay_unidades`, `test_rn01_upgrade_a_categoria_inferior_o_igual`

## US-13 · Fin de limpieza
```gherkin
Scenario: Marcar disponible un vehículo que no está en limpieza
  When el personal marca como terminada la limpieza de un vehículo DISPONIBLE
  Then el sistema rechaza la acción y el estado no cambia
```
Prueba: `test_terminar_limpieza_de_vehiculo_disponible_y_ids_inexistentes`
