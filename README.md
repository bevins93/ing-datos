# reset-report

Pipeline que lee los logs diarios del bot de soporte y actualiza de forma
incremental e idempotente `data/output/tabla_reporte_bot.csv` con los eventos
de dos acciones soportadas:

- **Reseteo de contrasena en ADManager** (endpoint interno
  `users_admin/resetuser`).
- **Alta de usuario en SAP** (endpoint interno `sap/register_user`).

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
│   ├── parsers/             # extraccion de datos crudos (resetuser, register_user, SearchUser,
│   │                         #   ADM-Raw response, SAP raw response, mensaje humano final)
│   ├── rules/               # motor de reglas de negocio -> mensaje humano de resultado_final
│   │   ├── common.py               # helpers compartidos entre rule sets (is_found, office_of)
│   │   ├── reset_password_rules.py # reglas de reseteo de password (ADManager)
│   │   └── alta_usuario_sap_rules.py  # reglas de alta de usuario (SAP)
│   └── output/              # upsert idempotente al CSV final
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

### Extraer una sola accion a un CSV aparte

`reset-report-filter` proyecta las filas de `tabla_reporte_bot.csv` que
correspondan a una `accion` especifica hacia otro CSV, sin volver a procesar
ningun log ni aplicar reglas de negocio (es un filtro puro sobre datos ya
generados):

```bash
uv run reset-report-filter --accion alta_usuario_sap \
    --input-csv data/output/tabla_reporte_bot.csv \
    --output-csv data/output/tabla_reporte_bot_alta_usuario_sap.csv

uv run reset-report-filter --accion reseteo_password \
    --output-csv data/output/tabla_reporte_bot_reseteo_password.csv
```

(`--input-csv` es opcional, por default usa `data/output/tabla_reporte_bot.csv`.)

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

### Alta de usuario en SAP (`alta_usuario_sap_rules.py`)

A diferencia de reseteo, el propio bot casi siempre escribe una linea de
texto plano con el resultado final del bloque (confirmado en los 39 bloques
reales disponibles: aparece en 38 de 39, la unica excepcion es el 400 sin
downstream). Cuando existe, `resultado_final` la usa **tal cual, verbatim**
— es la fuente mas fiel de lo que realmente paso. Solo se deriva un mensaje
a partir de los campos crudos (SearchUser, `job`/`treatment` del propio
endpoint) cuando esa linea no esta disponible, o para 500/503 que siempre
usan un texto fijo.

| Code | Causa | Mensaje | Verificado |
|---|---|---|---|
| 200 | Exito | linea final del bot, verbatim | ✅ log real |
| 202 | No se pudo cerrar el ticket de seguimiento | linea final del bot, verbatim | 🧪 sintetico |
| 202 | No se pudo crear el ticket de control | linea final del bot, verbatim | 🧪 sintetico |
| 208 | El empleado ya existe en ECC ECP (SAP responde con "ya existe" en `Mensaje`) | linea final del bot, verbatim (fallback: `Mensaje` de SAP) | ✅ log real |
| 400 | `target_employee_id` no es numerico | `El numero de empleado no es numerico` | ✅ log real |
| 400 | `treatment` no es "señor"/"señora" | `El tratamiento no es "señor" ni "señora"` | 🧪 sintetico |
| 400 | `job` no esta en la lista heuristica de puestos conocidos | `El puesto solicitado no existe` | 🧪 sintetico + heuristica (ver abajo) |
| 400 | Ninguna de las anteriores aplico (fallback por descarte) | `Todas las validaciones fueron exitosas, el servicio de SAP esta disponible, pero no se pudo ejecutar el alta por una razon desconocida (Por descarte de los casos anteriores)` | 🧪 sintetico |
| 401 | DESCRIPTION del solicitante no empieza con "gerente" ni "admin" (normalizado) | `El usuario solicitante no es gerente ni administrador de sistemas` | 🧪 sintetico |
| 403 | OFFICE del solicitante y del target distintos | mensaje propio del bot verbatim, o derivado con el mismo formato | ✅ log real |
| 403 | `job` pide un puesto de Gerente y el target no tiene DESCRIPTION de Gerente | mensaje propio del bot verbatim (`No se puede asignar el puesto ... AD Manager.`) | ✅ log real |
| 403 | OFFICE del solicitante es "corporativo" (OAT) | `El usuario solicitante es de OAT, por lo que no tiene permitido ejecutar este proceso (OFFICE: corporativo)` | 🧪 sintetico |
| 403 | Solicitante no pertenece a la cadena exclusiva del puesto pedido (City Club) | `El solicitante no pertenece a City Club y solicito el alta de un puesto exclusivo de City Club` | 🧪 sintetico + supuesto (ver abajo) |
| 403 | Idem para Soriana | `El solicitante no pertenece a Soriana y solicito el alta de un puesto exclusivo de Soriana` | 🧪 sintetico + supuesto |
| 403 | Ninguna de las anteriores se determino | `Acceso prohibido por SAP/ADManager (403): causa no determinada` | 🧪 sintetico |
| 404 | Target no existe en ADManager (SearchUser por `employeeID`, count 0) | `El usuario target no existe en ADManager (buscado por employeeID)` | 🧪 sintetico |
| 404 | Solicitante no existe en ADManager (SearchUser por `sAMAccountName`, count 0) | `El usuario solicitante no existe en ADManager (buscado por sAMAccountName)` | 🧪 sintetico |
| 404 | Ninguno existe (agregado por consistencia con reseteo, no esta en la especificacion original) | `Ningun usuario existe en ADManager` | 🧪 sintetico |
| 500 | Error desconocido, sin patron identificable | `Error interno critico e inesperado del proceso de alta de usuario en SAP: requiere revision manual` (+ `logger.critical`) | 🧪 sintetico |
| 503 | Validaciones exitosas, el servicio de SAP fallo | `Todas las validaciones fueron exitosas, pero el servicio del lado de SAP fallo` | 🧪 sintetico |
| otro codigo no contemplado | — | `Codigo de respuesta no reconocido (<code>) al ejecutar el alta de usuario` | — |

Prioridad de evaluacion de 403 cuando no hay linea final del bot: OAT/corporativo
→ oficinas distintas → target no es gerente → puesto exclusivo de cadena →
causa no determinada. Para 404: target faltante → solicitante faltante →
ambos faltantes → causa no determinada (mismo criterio que reseteo).

**Dos decisiones sin confirmar con datos reales, documentadas para revisar:**

- *Puestos validos para 400 "el puesto solicitado no existe"*: no se nos
  proporciono un catalogo oficial de SAP, asi que `config.KNOWN_JOB_TITLES`
  es una heuristica armada con los 7 puestos que si aparecen en los 4 dias
  de muestra (Gerente Tienda, Subgerente Tienda, Jefe de Mantenimiento
  Tienda, Supervisor Mermas, Cons.Internos Tienda, Recibo Tienda,
  Adm.Sistemas Tienda). Cualquier puesto real fuera de esa lista se
  reportaria incorrectamente como inexistente — actualizar la lista si
  aparecen puestos validos nuevos.
- *Deteccion de "puesto exclusivo de City Club/Soriana"*: no hay ejemplo
  real de este caso. Se asume que el nombre de la cadena aparece
  literalmente dentro del `job` solicitado (ej. "Gerente City Club") y que
  la pertenencia del solicitante a esa cadena se puede leer de su `OU_NAME`
  o `DESCRIPTION` en ADManager (`config.CHAIN_EXCLUSIVE_JOB_KEYWORDS`).
  Ajustar `alta_usuario_sap_rules._handle_403` si el campo real es distinto.

## Como agregar una accion/sistema nueva en el futuro

El pipeline (`src/reset_report/pipeline.py`) no conoce ningun detalle de
ADManager, SAP, ni de ninguna accion en particular: solo agrupa el log en
bloques por `operation_Id` y, para cada bloque, recorre
`reset_report.rules.REGISTRY` buscando el primer rule set cuyo `matches()`
devuelva `True`. `alta_usuario_sap_rules.py` es la prueba de que esto
funciona: se agrego como segunda accion sin tocar `pipeline.py`,
`log_ingest/` ni `output/` (solo se generalizo `searchuser_parser.py` para
aceptar filtros por `employeeID` ademas de `sAMAccountName`, ya que SAP
consulta al target por employeeID).

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
- Para alta de usuario en SAP se confirmaron con datos reales los codigos
  200, 208, 400 (employee_id no numerico) y dos de las causas de 403
  (oficinas distintas, target no es gerente); el resto de la tabla (202,
  las otras 3 causas de 400, 401, las otras 3 causas de 403, 404, 500, 503)
  son sinteticas por no aparecer en la muestra de 4 dias, y dos de ellas
  (puestos validos, deteccion de City Club/Soriana) son ademas supuestos de
  diseno sin confirmar — ver la seccion de arriba.
