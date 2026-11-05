# ADR-001 Arquitectura en capas con DDD
**Contexto.** El PIA exige DDD, Specification, State Machine y API REST, con `src/` dividido en domain, application, infrastructure y api.
**Decisión.** Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL. El dominio no depende de frameworks; la API traduce errores de dominio a mensajes en español.
**Alternativas.** Portar el esqueleto Java del Equipo 7 (descartado: no hay tiempo y las pruebas/CI del curso están en Python).
**Consecuencias.** Dominio probado de forma aislada; el esqueleto Java queda como referencia de modelado.