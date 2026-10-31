# Matriz de trazabilidad: BRD/US → regla → componente → prueba
| Origen | Regla | Componente | Prueba |
|---|---|---|---|
| US-01, US-02 | Reservar y confirmar con folio por categoría | `Reservacion.confirmar` | `test_us02_us03_confirmar_genera_evento_y_bloquea_lugar` |
| US-03, BR-02 | Bloquear inventario / cero sobreventas | `InventarioCategoria.apartar` | `test_br02_sobreventa_rechazada`, `test_br02_limite_reserva_que_empieza_el_dia_de_devolucion`, `test_br02_ocupacion_se_mide_dia_por_dia` |
| US-04..US-06, RN-02 | Documentos, pago y checklist | `requisitos_completos` (Specification AND) | `test_rn02_todos_los_requisitos`, `test_us04_us07_entrega_completa` |
| US-07, RN-02 | Bloquear entrega e informar faltantes | `faltantes_entrega`, `Renta.entregar` | `test_rn02_us07_lista_todo_lo_que_falta`, `test_rn02_entrega_bloqueada_informa_faltantes` |
| US-08, RN-03 | Extensión solo con disponibilidad | `extension_permitida`, `Renta.extender` | `test_us08_extension_con_disponibilidad`, `test_rn03_extension_rechazada_sin_capacidad`, `test_rn03_limite_otra_reserva_inicia_en_la_nueva_fecha_fin` |
| US-09 | Comparar estado inicial vs final | `comparar_estados` | `test_us09_comparar_y_danos_nuevos` |
| US-10, BR-03 | Cargos por retraso y kilometraje | `CalculadoraCargos` | `test_us10_retraso_exacto_no_cobra_y_un_minuto_cobra_una_hora`, `test_us10_kilometraje_limite_1000_incluidos` |
| US-11, BR-03 | Cargo por combustible | `CalculadoraCargos.por_combustible` | `test_us11_combustible_octavo_es_168_75` |
| US-12, BR-04 | Aviso a limpieza | `Vehiculo.devolver` (evento) | `test_us12_us13_ciclo_del_vehiculo`, `test_us10_us11_devolucion_con_cargos_y_limpieza` |
| US-13 | Vehículo vuelve a Disponible | `Vehiculo.terminar_limpieza` | `test_us12_us13_ciclo_del_vehiculo` |
| US-14, RN-01 | Upgrade sin costo extra | `upgrade_permitido`, `Renta.aplicar_upgrade` | `test_us14_upgrade_conserva_tarifa_y_entrega_categoria_superior`, `test_rn01_upgrade_rechazado_si_hay_unidades` |
| US-15 | KPIs | _pendiente (capa application)_ | — |
