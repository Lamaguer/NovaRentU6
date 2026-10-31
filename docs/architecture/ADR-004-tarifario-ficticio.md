# ADR-004 Tarifario ficticio y supuestos de cálculo
**Contexto.** El BRD supone una lista de precios pero no incluye valores.
**Decisión.** Valores de demostración en `src/domain/politicas.py`: tarifa diaria 500/650/900/1400; retraso $150/h (hora límite 12:00); 200 km/día incluidos y $4/km extra; combustible $30/L con tanque de 45 L en octavos; $500 por daño nuevo. Todo en `Decimal`.
**Consecuencias.** Reemplazables sin tocar la lógica. Deben sustituirse por los valores oficiales del cliente.
