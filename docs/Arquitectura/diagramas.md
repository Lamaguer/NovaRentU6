# Diagramas de arquitectura y dominio — NovaRent

Los diagramas están en **Mermaid**: GitHub los dibuja directamente al abrir este archivo. Para el reporte PDF, exporta cada uno como imagen desde <https://mermaid.live> (pega el bloque, descarga PNG/SVG).

Cada diagrama refleja el código de `src/`; el nombre de la clase o archivo está en el texto para poder rastrearlo.

---

## 1. Arquitectura por capas

La interfaz no conoce la base de datos y el dominio no conoce a FastAPI ni a SQLAlchemy (regla de dependencia hacia adentro).

```mermaid
flowchart TB
    UI["Interfaz web<br/>src/web"] -->|HTTP JSON| API["API REST con FastAPI<br/>src/api (main.py, mensajes.py)"]
    API --> APP["Casos de uso<br/>src/application/servicios.py<br/>ServicioNovaRent"]
    APP --> DOM["Dominio<br/>src/domain<br/>agregados, Specifications, eventos"]
    APP --> INF["Infraestructura<br/>src/infrastructure<br/>UnitOfWork, Repositorios, Pasarela"]
    INF --> DB[("PostgreSQL<br/>SQLite en pruebas")]
    INF --> PAS["Pasarela de pago simulada<br/>PasarelaPagoSimulada"]
    INF -.->|reconstruye| DOM
```

| Capa | Responsabilidad | Ejemplo |
|---|---|---|
| Web | Mostrar solo el campo `mensaje` de los errores | `src/web/app.js` |
| API | Validar la forma de los datos, traducir errores de dominio a lenguaje de cliente | `clasificar()` en `mensajes.py` |
| Aplicación | Una transacción por caso de uso (commit o rollback) | `ServicioNovaRent.reservar` |
| Dominio | Reglas del BRD, sin dependencias externas | `Renta.entregar`, `upgrade_permitido` |
| Infraestructura | Persistir y cobrar (simulado) | `UnitOfWork`, `Repositorio*` |

---

## 2. Modelo de dominio (DDD)

Tres agregados raíz (`Reservacion`, `Renta`, `Vehiculo`), un agregado de capacidad (`InventarioCategoria`) y Value Objects inmutables. Los agregados se referencian **por identificador** (folio, id de vehículo), nunca por objeto, para mantener transacciones pequeñas.

```mermaid
classDiagram
    class Reservacion {
        <<Aggregate Root>>
        +str folio
        +str cliente_id
        +str sucursal_id
        +str categoria
        +PeriodoRenta periodo
        +Dinero tarifa_diaria
        +str estado
        +confirmar(inventario)
        +marcar_cumplida()
    }
    class Renta {
        <<Aggregate Root>>
        +str id_renta
        +str folio
        +str categoria_reservada
        +str categoria_asignada
        +str vehiculo_id
        +Dinero tarifa_diaria_original
        +PeriodoRenta periodo
        +str estado
        +aplicar_upgrade(categoria, unidades)
        +entregar(requisitos, vehiculo)
        +extender(nueva_fin, inventario)
        +registrar_devolucion(estado_final, retorno, vehiculo)
    }
    class Vehiculo {
        <<Aggregate Root>>
        +str id
        +str categoria
        +str sucursal_id
        +str estado
        +rentar()
        +devolver()
        +terminar_limpieza()
    }
    class InventarioCategoria {
        <<Aggregate>>
        +str sucursal_id
        +str categoria
        +int capacidad
        +dict apartados
        +hay_capacidad(periodo)
        +apartar(folio, periodo)
        +extender(folio, periodo)
        +liberar(folio)
    }
    class PeriodoRenta {
        <<Value Object>>
        +date inicio
        +date fin
        +dias()
        +traslapa(otro)
    }
    class Dinero {
        <<Value Object>>
        +Decimal monto
        +str moneda
        +por(factor)
    }
    class EstadoFisico {
        <<Value Object>>
        +int combustible_octavos
        +int kilometraje
        +tuple danos
    }
    class RequisitosEntrega {
        <<Value Object>>
        +bool identificacion_valida
        +bool licencia_vigente
        +bool pago_autorizado
        +EstadoFisico checklist
    }
    class Cargo {
        <<Value Object>>
        +str concepto
        +Dinero monto
        +str detalle
    }
    class CalculadoraCargos {
        <<Domain Service>>
        +calcular(periodo, inicial, final, retorno)
    }
    class Evento {
        <<Domain Event>>
        +str nombre
        +str agregado_id
        +dict datos
    }

    Reservacion "1" --> "1" PeriodoRenta
    Reservacion "1" --> "1" Dinero
    Renta ..> Reservacion : nace de, por folio
    Renta ..> Vehiculo : referencia por id
    Renta "1" *-- "0..*" Cargo
    Renta --> EstadoFisico : checklist inicial y final
    Renta ..> RequisitosEntrega : valida
    Renta ..> CalculadoraCargos : usa
    Cargo --> Dinero
    InventarioCategoria "1" o-- "0..*" Reservacion : aparta lugares por folio
    Reservacion ..> Evento : emite
    Renta ..> Evento : emite
    Vehiculo ..> Evento : emite
```

### Eventos de dominio

| Evento | Lo emite | Historia |
|---|---|---|
| `ReservacionConfirmada` | `Reservacion.confirmar` | US-02, US-03 |
| `UpgradeAplicado` | `Renta.aplicar_upgrade` | US-14 |
| `VehiculoEntregado` | `Renta.entregar` | US-04..US-07 |
| `RentaExtendida` | `Renta.extender` | US-08 |
| `VehiculoDevuelto` | `Renta.registrar_devolucion` | US-09 |
| `CargoGenerado` | `Renta.registrar_devolucion` (solo si hay cargos) | US-10, US-11 |
| `VehiculoEnLimpieza` | `Vehiculo.devolver` | US-12, BR-04 |
| `VehiculoDisponible` | `Vehiculo.terminar_limpieza` | US-13 |

---

## 3. Máquinas de estado

**Reservación**

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE
    PENDIENTE --> CONFIRMADA : confirmar, si hay capacidad
    CONFIRMADA --> CUMPLIDA : abrir contrato de renta
    CUMPLIDA --> [*]
```

**Renta**

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE : abrir contrato
    PENDIENTE --> PENDIENTE : aplicar upgrade, RN-01
    PENDIENTE --> ENTREGADO : entregar, RN-02
    ENTREGADO --> ENTREGADO : extender, RN-03
    ENTREGADO --> DEVUELTO : registrar devolucion
    DEVUELTO --> [*]
```

**Vehículo** (ciclo físico de la unidad, BRD §4)

```mermaid
stateDiagram-v2
    [*] --> DISPONIBLE
    DISPONIBLE --> RENTADO : rentar
    RENTADO --> EN_LIMPIEZA : devolver
    EN_LIMPIEZA --> DISPONIBLE : terminar_limpieza
```

Cualquier otra transición lanza `TransicionInvalida` (el dominio no permite, por ejemplo, rentar un vehículo `EN_LIMPIEZA`).

---

## 4. Specifications (RN-01, RN-02, RN-03)

Cada regla es una combinación de condiciones pequeñas con `&`, `|` y `~`.

```mermaid
classDiagram
    class Specification {
        <<abstract>>
        +is_satisfied_by(candidato)
        +__and__(otra)
        +__or__(otra)
        +__invert__()
    }
    Specification <|-- IdentificacionSpec
    Specification <|-- LicenciaSpec
    Specification <|-- PagoSpec
    Specification <|-- ChecklistSpec
    Specification <|-- NuevaFechaPosteriorSpec
    Specification <|-- SinConflictoSpec
    Specification <|-- SinUnidadesSpec
    Specification <|-- CategoriaSuperiorSpec
    Specification <|-- Compuesta_AND_OR
    Specification <|-- Not_NOT
```

| Regla | Composición | Candidato |
|---|---|---|
| RN-02 `requisitos_completos` | `IdentificacionSpec & LicenciaSpec & PagoSpec & ChecklistSpec` | `RequisitosEntrega` |
| RN-03 `extension_permitida` | `NuevaFechaPosteriorSpec & SinConflictoSpec` | `SolicitudExtension` |
| RN-01 `upgrade_permitido` | `SinUnidadesSpec & CategoriaSuperiorSpec` | `SolicitudUpgrade` |

`faltantes_entrega()` recorre las mismas Specifications para devolver la lista legible de lo que falta (US-07).

---

## 5. Secuencia: entrega del vehículo (flujo principal y excepcional)

```mermaid
sequenceDiagram
    actor Agente
    participant UI as Interfaz web
    participant API as API REST
    participant S as ServicioNovaRent
    participant P as Pasarela simulada
    participant R as Renta (dominio)
    participant V as Vehiculo (dominio)
    participant BD as Base de datos

    Agente->>UI: Marca documentos, tarjeta y checklist
    UI->>API: POST /api/rentas/id/entrega
    API->>S: entregar_con_tarjeta(...)
    S->>S: faltantes_entrega(requisitos)
    alt Faltan requisitos
        S-->>API: RequisitosIncompletos con lista
        API-->>UI: 409 con mensaje y faltantes en español
        UI-->>Agente: Muestra lo que falta
    else Requisitos completos
        S->>P: retener_deposito(tarjeta, total)
        alt Pago rechazado
            P-->>S: False
            S-->>API: RequisitosIncompletos pago
            API-->>UI: 409 con mensaje
        else Pago autorizado
            P-->>S: True
            S->>R: entregar(requisitos, vehiculo)
            R->>V: rentar()
            R-->>S: estado ENTREGADO y evento
            S->>BD: commit de renta, vehiculo y eventos
            S-->>API: renta
            API-->>UI: 200
        end
    end
    Note over S,BD: Si el dominio lanza un error, se hace rollback y no se guarda nada
```

## 6. Secuencia: reservar y bloquear inventario (US-02, US-03, BR-02)

```mermaid
sequenceDiagram
    actor Cliente
    participant UI as Interfaz web
    participant API as API REST
    participant S as ServicioNovaRent
    participant I as InventarioCategoria
    participant BD as Base de datos

    Cliente->>UI: Sucursal, fechas y categoria
    UI->>API: POST /api/reservaciones
    API->>S: reservar(...)
    S->>BD: Carga inventario con bloqueo de fila
    S->>I: apartar(folio, periodo)
    alt Sin lugar algun dia del periodo
        I-->>S: SinDisponibilidad BR-02
        S->>BD: rollback
        API-->>UI: 409 No hay unidades disponibles en esas fechas
    else Hay lugar todos los dias
        I-->>S: lugar apartado
        S->>BD: commit
        API-->>UI: 201 con folio
    end
```

---

## 7. Proceso de negocio actualizado (BPMN)

Cambios respecto al BPMN original (ver `ADR-002`): el **checklist inicial se captura antes de entregar** (requisito de la entrega, glosario D023 y US-07) y se agrega la rama de **upgrade** (RN-01).

```mermaid
flowchart TB
    subgraph CL["Cliente"]
        A([Inicio]) --> B[Realizar reservacion]
        B --> C{Categoria disponible?}
        C -- No --> D[Aviso de no disponibilidad] --> Z1([Fin])
        C -- Si --> E[Recibir folio de reserva]
        E --> F[Ir a sucursal]
    end
    subgraph AG["Agente de renta"]
        F --> G[Abrir contrato con el folio]
        G --> H{Hay unidad fisica de la categoria?}
        H -- No --> I[Autorizar upgrade sin costo extra RN-01]
        H -- Si --> J[Validar identificacion, licencia y pago]
        I --> J
        J --> K[Capturar checklist inicial]
        K --> L{Requisitos completos RN-02?}
        L -- No --> M[Bloquear entrega y listar faltantes]
        M --> J
        L -- Si --> N[Entregar vehiculo]
    end
    subgraph CR["Cliente en renta"]
        N --> O[Uso del vehiculo]
        O --> P{Extension solicitada?}
        P -- Si --> Q{Categoria con lugar RN-03?}
        Q -- Si --> R[Aprobar extension] --> O
        Q -- No --> S[Rechazar extension] --> O
        P -- No --> T[Devolver vehiculo]
    end
    subgraph AD["Agente en devolucion"]
        T --> U[Registrar estado final]
        U --> V[Comparar contra checklist inicial]
        V --> W[Calcular cargos: retraso, km, combustible, danos]
    end
    subgraph LI["Limpieza"]
        W --> X[Notificar vehiculo en limpieza]
        X --> Y[Reacondicionar]
        Y --> Z[Marcar vehiculo disponible]
    end
    subgraph AM["Administracion"]
        Z --> AA[Consultar KPIs]
    end
```
