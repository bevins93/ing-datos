from reset_report.rules.base import ActionRuleSet
from reset_report.rules.reset_password_rules import AdManagerResetPasswordRules

REGISTRY: list[ActionRuleSet] = [
    AdManagerResetPasswordRules(),
]

__all__ = ["REGISTRY", "ActionRuleSet"]
