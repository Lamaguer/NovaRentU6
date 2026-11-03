"""Unit of Work: una transaccion por caso de uso (commit si todo sale bien, rollback si no)."""
from src.infrastructure.repositorios import (
    RepositorioEventos,
    RepositorioInventarios,
    RepositorioRentas,
    RepositorioReservaciones,
    RepositorioVehiculos,
)


class UnitOfWork:
    def __init__(self, session_factory):
        self._factory = session_factory

    def __enter__(self):
        self.session = self._factory()
        self.inventarios = RepositorioInventarios(self.session)
        self.reservaciones = RepositorioReservaciones(self.session)
        self.rentas = RepositorioRentas(self.session)
        self.vehiculos = RepositorioVehiculos(self.session)
        self.eventos = RepositorioEventos(self.session)
        return self

    def __exit__(self, tipo, valor, tb):
        if tipo is not None:
            self.session.rollback()
        self.session.close()
        return False

    def commit(self):
        self.session.commit()
