from src.domain.specifications import (
    ChecklistSpec,
    LicenciaSpec,
    PagoSpec,
    SolicitudUpgrade,
    Specification,
    faltantes_entrega,
    requisitos_completos,
    upgrade_permitido,
)
from src.domain.valores import EstadoFisico, RequisitosEntrega


class Siempre(Specification):
    def __init__(self, valor):
        self.valor = valor

    def is_satisfied_by(self, c):
        return self.valor


def test_composicion_and_or_not():
    T, F = Siempre(True), Siempre(False)
    assert (T & T).is_satisfied_by(None)
    assert not (T & F).is_satisfied_by(None)
    assert (T | F).is_satisfied_by(None)
    assert not (F | F).is_satisfied_by(None)
    assert (~F).is_satisfied_by(None)


def test_rn02_todos_los_requisitos():
    ok = RequisitosEntrega(True, True, True, EstadoFisico(8, 100))
    assert requisitos_completos.is_satisfied_by(ok)
    assert faltantes_entrega(ok) == []


def test_rn02_us07_lista_todo_lo_que_falta():
    vacio = RequisitosEntrega()
    assert len(faltantes_entrega(vacio)) == 4
    assert not LicenciaSpec().is_satisfied_by(vacio)
    assert not PagoSpec().is_satisfied_by(vacio)
    assert not ChecklistSpec().is_satisfied_by(vacio)


def test_rn01_upgrade_solo_sin_unidades_y_categoria_superior():
    assert upgrade_permitido.is_satisfied_by(SolicitudUpgrade("ECONOMICO", "SUV", 0))
    assert not upgrade_permitido.is_satisfied_by(SolicitudUpgrade("ECONOMICO", "SUV", 1))
    assert not upgrade_permitido.is_satisfied_by(SolicitudUpgrade("SUV", "ECONOMICO", 0))
    assert not upgrade_permitido.is_satisfied_by(SolicitudUpgrade("SUV", "SUV", 0))
