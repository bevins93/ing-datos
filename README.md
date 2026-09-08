# reset-report

Pipeline que lee los logs diarios del bot de soporte y actualiza de forma
incremental e idempotente `data/output/tabla_reporte_bot.csv` con los eventos
de **reseteo de contrasena en ADManager** (endpoint interno
`users_admin/resetuser`).

`resultado_final` nunca contiene el status code crudo de la API interna: es
siempre un mensaje humano, construido combinando ese status code con la
informacion real de las respuestas de ADManager (SearchUser y ResetPwd) que
ya viene en el log.

## Estructura del repo

```
.
├── data/
│   ├── input/     # coloca aqui los .log de entrada (vacio en el repo)
│   └── output/    # aqui se escribe tabla_reporte_bot.csv (vacio en el repo)
├── notebooks/     # solo exploracion, nunca parte del proceso ejecutable
├── src/reset_report/
│   ├── cli.py               # punto de entrada (argparse)
│   ├── pipeline.py          # orquestacion: ingest -> parsers -> rules -> CSV
│   ├── config.py            # rutas por defecto, columnas, umbrales documentados
│   ├── text_normalize.py    # normalizacion de texto centralizada
│   ├── report_row.py        # forma de una fila del CSV
│   ├── log_ingest/          # descubrimiento de archivos + agrupacion por operation_Id
│   ├── parsers/             # extraccion de datos crudos (resetuser, SearchUser, ADM-Raw response)
│   ├── rules/                # motor de reglas de negocio -> mensaje humano de resultado_final
│   └── output/                # upsert idempotente al CSV final
└── tests/
    ├── fixtures/*.log        # logs sinteticos, uno por caso de negocio
    └── test_*.py
```

Los datos reales **nunca se suben al repo**: `data/input/` y `data/output/`
viven vacios (con `.gitkeep`) y su contenido esta en `.gitignore`.

## Instalacion (con [uv](https://docs.astral.sh/uv/))

```bash
uv sync
```

Esto crea el entorno virtual (`.venv/`) e instala las dependencias fijadas en
`uv.lock`, incluyendo `pytest` y `ruff` para desarrollo.

## Ejecucion

Coloca los `.log` a procesar dentro de `data/input/` (o apunta a otro
directorio con `--input-dir`). Los nombres de archivo aceptados son tanto
`<epoch>_<YYYY-MM-DD>.log` como `<YYYY-MM-DD>.log`.

```bash
# procesar un dia especifico (localiza el archivo automaticamente por fecha)
uv run reset-report --date 2026-08-29

# procesar un dia especifico indicando el archivo explicitamente
uv run reset-report --date 2026-08-29 --log-path /ruta/absoluta/2026-08-29.log

# procesar todos los .log presentes en data/input/, en orden de fecha
uv run reset-report --all

# usar directorios distintos a los defaults (data/input, data/output)
uv run reset-report --all --input-dir /otra/ruta/logs --output-dir /otra/ruta/salida
```

Cada corrida agrega (append) al final de `tabla_reporte_bot.csv` las filas
nuevas, creandolo con encabezado si no existe. **Nunca** reescribe ni borra
filas ya escritas: la llave de idempotencia es `operation_id` (columna extra
al final del CSV, necesaria para detectar de forma inequivoca que registros
ya se procesaron). Por eso:

- Correr el mismo dia dos veces produce exactamente el mismo CSV.
- Reprocesar un log "corregido" (con lineas nuevas agregadas a mano) solo
  agrega lo nuevo.

## Pruebas y calidad de codigo

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Como se determina `resultado_final`

El motor de reglas vive en `src/reset_report/rules/reset_password_rules.py`.
Combina el status code de la linea gatillo `resetuser` con los datos de
ADManager ya extraidos (`SearchUser` de solicitante y target, y la respuesta
de `ResetPwd`):

| Code | Causa | Mensaje |
|---|---|---|
| 200 | `ADM-Raw response` con `status:'1'` | `Reseteo ejecutado exitosamente` |
| 200 | `ADM-Raw response` con `status` distinto de `'1'` (defensivo; no visto en datos reales) | `El reseteo fallo en ADManager: <statusMessage>` |
| 202 | El target es de Corporativo (asumido por nuestra propia API al devolver 202) | `El usuario target pertenece a Corporativo (oficina: <OFFICE>)` |
| 403 | OFFICE del solicitante distinto al del target | `El usuario solicitante y el usuario target no pertenecen a la misma oficina` |
| 403 | DESCRIPTION del solicitante no empieza con "gerente" ni "admin" (normalizado) | `El usuario solicitante no tiene privilegios para ejecutar el reseteo` |
| 403 | OU_NAME del target es "OAT/Cedis/BY" (normalizado) | `El usuario target pertenece a una oficina restringida (OAT/Cedis/BY)` |
| 403 | Ninguna de las anteriores se pudo determinar | `Acceso prohibido por ADManager (403): causa no determinada` |
| 404 | Solo el target no aparece en SearchUser (`count:0`) | `El usuario objetivo no se encontro en ADManager` |
| 404 | Solo el solicitante no aparece en SearchUser | `El usuario solicitante no se encontro en ADManager` |
| 404 | Ninguno aparece en SearchUser | `Ningun usuario se encontro en ADManager` |
| 429 | Tokens de ADManager agotados | `No se pudo ejecutar el reseteo: se agotaron los tokens de ADManager` |
| 500 | Sin ningun patron identificable en las respuestas de ADManager (bug interno) | `Error interno critico e inesperado del proceso de reseteo: requiere revision manual` (ademas se loggea con `logger.critical`) |
| 503 | `ADM-Raw response` con `body` de `status:'0'` | `El reseteo fallo en ADManager: <statusMessage tal cual la reporta ADManager>` |
| 504 | `ADM-Raw response` con `reason: ADM timed out` | `El reseteo no se pudo confirmar: ADManager no respondio a tiempo (timeout)` |
| otro codigo no contemplado | — | `Codigo de respuesta no reconocido (<code>) al ejecutar el reseteo` |

Las tres causas de 403 y las tres de 404 se evaluan en el orden de la tabla
(office mismatch antes que privilegios, antes que OU restringida; target
faltante antes que solicitante faltante, antes que ambos faltantes). Ese
orden importa: se valido contra un caso real (`operation_Id`
`895db57ed39c8499d426c89d9f924394`, log del 2026-08-29) donde el solicitante
tenia `DESCRIPTION: "Administrador De Sistemas"` (que en teoria tambien
satisface el prefijo "admin" de la regla de privilegios) pero la causa real
era el mismatch de oficina — de ahi que esa regla se evalue primero.

Toda comparacion de texto (OFFICE, DESCRIPTION, OU_NAME) pasa antes por
`text_normalize.normalize()`, que quita acentos y pasa a minusculas, porque
ADManager es inconsistente en como capitaliza esos campos
(`"Corporativo"` vs `"CORPORATIVO"`). El texto que se escribe en el CSV
(por ejemplo el `statusMessage` del 503) nunca se normaliza: se usa el valor
original del log.

## Como agregar una accion/sistema nueva en el futuro

El pipeline (`src/reset_report/pipeline.py`) no conoce ningun detalle de
ADManager ni de reseteo de contrasenas: solo agrupa el log en bloques por
`operation_Id` y, para cada bloque, recorre `reset_report.rules.REGISTRY`
buscando el primer rule set cuyo `matches()` devuelva `True`.

Para agregar, por ejemplo, un hipotetico "bloqueo de cuenta" en otro sistema:

1. Si el formato de las respuestas crudas de ese sistema es distinto,
   agregar los parsers necesarios en `src/reset_report/parsers/`.
2. Crear `src/reset_report/rules/otro_sistema_lock_rules.py`:

   ```python
   from reset_report.rules.base import ActionRuleSet
   from reset_report.report_row import ReportRow
   from reset_report.log_ingest import LogBlock

   class OtroSistemaLockRules(ActionRuleSet):
       action_name = "bloqueo_cuenta"
       system_name = "OtroSistema"

       def matches(self, block: LogBlock) -> bool:
           return any("users_admin/lockuser" in e.message for e in block.entries)

       def build_row(self, block: LogBlock) -> ReportRow | None:
           # extraer datos del bloque (via parsers/) y construir el ReportRow,
           # aplicando aqui las reglas de negocio propias de esta accion
           ...
   ```

3. Registrarla en `src/reset_report/rules/__init__.py`:

   ```python
   from reset_report.rules.otro_sistema_lock_rules import OtroSistemaLockRules

   REGISTRY: list[ActionRuleSet] = [
       AdManagerResetPasswordRules(),
       OtroSistemaLockRules(),
   ]
   ```

No se requiere ningun cambio en `pipeline.py`, `log_ingest/` ni `output/`.
Los bloques que ningun rule set reclame (Proactivanet, `segMttoUsuario`,
etc.) se siguen ignorando automaticamente.

## Notas sobre los datos reales usados para validar este diseno

- Los archivos de muestra usados durante el desarrollo se llaman
  `<YYYY-MM-DD>.log` (sin el prefijo `<epoch>_`); el localizador de archivos
  acepta ambos patrones.
- Se confirmaron con datos reales los casos 200, 403 (mismatch de oficina),
  404 (los tres sub-casos), 500 y 504. Los casos 202, 429, y las reglas de
  "sin privilegios" y "OU restringida" del 403 no aparecieron en la muestra
  de 4 dias disponible; estan implementados siguiendo la regla de negocio
  descrita y cubiertos por fixtures sinteticas en `tests/fixtures/`.
- ADManager corta la llamada a `ResetPwd` con un timeout (HTTP 504, `reason:
  "ADM timed out"`) alrededor de los `ADMANAGER_TIMEOUT_SECONDS` (35s,
  documentado en `config.py`); no se calcula ningun delta de tiempo para
  detectarlo, el log ya lo indica explicitamente.
