"""Traduce errores de dominio a mensajes que entiende un cliente sin conocimientos tecnicos."""
from src.domain.errores import (
    DatosInvalidos,
    NoEncontrado,
    RequisitosIncompletos,
    SinDisponibilidad,
    TransicionInvalida,
)

_DATOS = {
    "anterior a hoy": "La fecha de inicio no puede ser anterior a hoy.",
    "fecha fin": "La fecha de devolución debe ser posterior a la de inicio.",
    "ampliar": "La nueva fecha debe ser posterior a la fecha de devolución actual.",
    "kilometraje final": "El kilometraje final no puede ser menor al de entrega.",
    "nombre del cliente": "Escribe el nombre del cliente.",
    "Categoria desconocida": "Selecciona una categoría válida.",
    "estado final": "Captura el estado final del vehículo.",
}


def clasificar(exc):
    """Devuelve (codigo_http, mensaje_para_el_usuario)."""
    texto = str(exc)
    if isinstance(exc, RequisitosIncompletos):
        return 409, "No se puede entregar el vehículo todavía. " + "; ".join(exc.faltantes) + "."
    if isinstance(exc, SinDisponibilidad):
        if "BR-02" in texto:
            return 409, ("No hay unidades disponibles en esas fechas. "
                         "Prueba otra categoría o cambia las fechas.")
        if "RN-03" in texto:
            return 409, ("No es posible extender la renta: la categoría ya está reservada "
                         "por otro cliente en esas fechas.")
        if "RN-01" in texto:
            return 409, ("El upgrade solo aplica cuando no quedan unidades de la categoría "
                         "reservada y hacia una categoría superior.")
        return 409, ("No hay unidades físicas de la categoría reservada. "
                     "Autoriza un upgrade a una categoría superior sin costo extra.")
    if isinstance(exc, NoEncontrado):
        return 404, "No encontramos lo que buscas. Revisa el folio o el identificador."
    if isinstance(exc, TransicionInvalida):
        return 409, "Esa acción no está disponible en el estado actual de la renta."
    if isinstance(exc, DatosInvalidos):
        for clave, msg in _DATOS.items():
            if clave in texto:
                return 422, msg
        return 422, "Revisa los datos capturados."
    return 400, "No se pudo completar la operación."
