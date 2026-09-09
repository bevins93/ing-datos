from reset_report.rules.alta_usuario_sap_rules import AltaUsuarioSapRules
from reset_report.rules.base import ActionRuleSet
from reset_report.rules.reset_password_rules import AdManagerResetPasswordRules

REGISTRY: list[ActionRuleSet] = [
    AdManagerResetPasswordRules(),
    AltaUsuarioSapRules(),
]

__all__ = ["REGISTRY", "ActionRuleSet"]
