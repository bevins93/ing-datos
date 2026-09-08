"""Interfaz comun que debe implementar cualquier set de reglas de negocio
para una accion (ver rules/reset_password_rules.py para la implementacion
de referencia).

Agregar una accion nueva en el futuro es cuestion de:
  1. Crear un modulo nuevo en rules/ con una clase que herede de
     ActionRuleSet e implemente matches() y build_row().
  2. Registrarla en rules/__init__.py (REGISTRY).

El pipeline central (reset_report.pipeline) no necesita cambios.
"""

from abc import ABC, abstractmethod

from reset_report.log_ingest import LogBlock
from reset_report.report_row import ReportRow


class ActionRuleSet(ABC):
    #: Valor que se escribe en la columna "accion" del CSV.
    action_name: str
    #: Valor que se escribe en la columna "sistema" del CSV.
    system_name: str

    @abstractmethod
    def matches(self, block: LogBlock) -> bool:
        """True si este bloque (mismo operation_Id) corresponde a esta accion."""
        raise NotImplementedError

    @abstractmethod
    def build_row(self, block: LogBlock) -> ReportRow | None:
        """Construye la fila de reporte para este bloque, o None si el
        bloque no trae suficiente informacion para producir una fila util.

        Debe ser defensivo: nunca debe lanzar una excepcion por datos
        incompletos o corruptos; en su lugar registra una advertencia
        (logging.warning) y hace su mejor esfuerzo.
        """
        raise NotImplementedError
