"""Normalizacion de texto centralizada, usada por el motor de reglas para
comparar valores provenientes de ADManager (OFFICE, DESCRIPTION, OU_NAME)
de forma insensible a acentos y mayusculas/minusculas.

Nunca se usa para transformar el texto que se escribe en el CSV final: ahi
siempre va el valor original tal como aparece en el log.
"""

import unicodedata


def normalize(value: str | None) -> str:
    """Quita acentos, pasa a minusculas y recorta espacios.

    normalize("Corporativo ")      -> "corporativo"
    normalize("CORPORATIVO")       -> "corporativo"
    normalize("OAT/Cedis/BY")      -> "oat/cedis/by"
    normalize(None)                -> ""
    """
    if not value:
        return ""

    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.strip().lower()


def starts_with_any(value: str | None, prefixes: tuple[str, ...]) -> bool:
    """True si `value` normalizado empieza con alguno de `prefixes`
    (los prefijos ya deben venir normalizados)."""
    normalized_value = normalize(value)
    return any(normalized_value.startswith(prefix) for prefix in prefixes)
