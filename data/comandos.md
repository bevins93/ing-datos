# Comandos de referencia — reset-report

Chuleta con todos los comandos de shell para instalar, ejecutar y probar el
proyecto, tanto en Windows (VSCode / PowerShell / Git Bash) como en WSL.
Este archivo es solo documentacion de referencia; no es parte del pipeline
ejecutable.

Todos los comandos asumen que ya estas parado en la raiz del repo
(`ing-datos/`).

---

## 1. Windows — PowerShell (terminal por defecto en VSCode)

```powershell
# Instalar dependencias (crea .venv/ y usa uv.lock)
uv sync

# Procesar un dia especifico (localiza el .log por fecha en data/input)
uv run reset-report --date 2026-08-29

# Procesar un dia indicando el archivo explicitamente
uv run reset-report --date 2026-08-29 --log-path "D:\Kevin\Posgrados\MCD\2026-2\ing-datos\datos\2026-08-29.log"

# Procesar todos los .log de data/input, en orden de fecha
uv run reset-report --all

# Procesar todos los .log reales sin copiarlos a data/input (usando la carpeta original)
uv run reset-report --all --input-dir "D:\Kevin\Posgrados\MCD\2026-2\ing-datos\datos" --output-dir data\output

# Pruebas y calidad de codigo
uv run pytest -q
uv run ruff check .
uv run ruff format .
```

## 2. Windows — Git Bash (el que usa la herramienta Bash de este asistente)

```bash
cd "D:/Kevin/Posgrados/MCD/2026-2/ing-datos"

uv sync

uv run reset-report --date 2026-08-29
uv run reset-report --date 2026-08-29 --log-path "D:/Kevin/Posgrados/MCD/2026-2/ing-datos/datos/2026-08-29.log"
uv run reset-report --all
uv run reset-report --all --input-dir "D:/Kevin/Posgrados/MCD/2026-2/ing-datos/datos" --output-dir data/output

uv run pytest -q
uv run ruff check .
uv run ruff format .
```

## 3. WSL (Linux)

### 3a. Primera vez: instalar uv (si no esta instalado)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # o abre una terminal nueva
```

### 3b. Opcion recomendada: clonar el repo dentro del filesystem nativo de WSL

`/mnt/d/...` es lento en WSL2 (filesystem 9p); clonar en `~` es mucho mas
rapido para correr tests/ruff repetidamente.

```bash
cd ~
git clone https://github.com/bevins93/ing-datos.git
cd ing-datos

uv sync

# Los logs reales viven fuera del repo (datos/ en Windows), se referencian por --input-dir
uv run reset-report --date 2026-08-29 --input-dir "/mnt/d/Kevin/Posgrados/MCD/2026-2/ing-datos/datos" --output-dir data/output
uv run reset-report --all --input-dir "/mnt/d/Kevin/Posgrados/MCD/2026-2/ing-datos/datos" --output-dir data/output

uv run pytest -q
uv run ruff check .
uv run ruff format .
```

### 3c. Alternativa: trabajar directo sobre la carpeta de Windows desde WSL

```bash
cd "/mnt/d/Kevin/Posgrados/MCD/2026-2/ing-datos"

uv sync

uv run reset-report --date 2026-08-29
uv run reset-report --all --input-dir ./datos --output-dir data/output

uv run pytest -q
uv run ruff check .
uv run ruff format .
```

---

## 4. Git — commits semanticos (recordatorio de convencion usada en este repo)

```bash
git add <archivos>
git commit -m "feat: descripcion breve en presente"
git commit -m "fix: descripcion breve en presente"
git commit -m "refactor: descripcion breve en presente"
git commit -m "test: descripcion breve en presente"
git commit -m "docs: descripcion breve en presente"
git commit -m "chore: descripcion breve en presente"

git push origin main
```

## 5. Notas

- `data/input/` y `data/output/` estan vacios en el repo (`.gitkeep`) y su
  contenido esta en `.gitignore`: nunca subas ahi los `.log` reales ni el
  CSV generado si vas a hacer commit.
- Si prefieres no pasar `--input-dir`/`--output-dir` en cada corrida, copia
  (o crea un symlink a) los `.log` dentro de `data/input/` y usa los
  comandos sin esas banderas (usan `data/input`/`data/output` por default).
- `uv run <comando>` siempre usa el entorno virtual del proyecto (`.venv/`)
  sin necesidad de activarlo manualmente.
