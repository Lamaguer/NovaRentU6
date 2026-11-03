class PasarelaPagoSimulada:
    """Adaptador simulado (no mueve dinero). Rechaza tarjetas que terminan en 0000."""

    def retener_deposito(self, tarjeta, monto):
        return bool(tarjeta) and not tarjeta.strip().endswith("0000")
