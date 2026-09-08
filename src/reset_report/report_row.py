"""Forma de una fila de tabla_reporte_bot.csv, comun a cualquier accion."""

from dataclasses import dataclass


@dataclass
class ReportRow:
    timestamp: str
    solicitante: str
    target: str
    accion: str
    sistema: str
    nombre_completo_solicitante: str
    nombre_completo_target: str
    oficina_solicitante: str
    oficina_target: str
    resultado_final: str
    operation_id: str
