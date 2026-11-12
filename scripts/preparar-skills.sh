#!/usr/bin/env bash
# Nombre: preparar-skills.sh
# Descripción: Trae los skills de frontend a .claude/skills/ en los commits fijos de su tabla (Linux, Raspberry y Git Bash).
# Fecha de creación: 2026-11-11
# Actualización: 2026-11-11
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio:
#   ./scripts/preparar-skills.sh                trae los skills en los commits fijos de la tabla
#   ./scripts/preparar-skills.sh --actualizar   trae la última versión de cada repositorio, muestra qué
#                                               commits cambiaron y anota los nuevos en la tabla de los dos scripts
#
# Necesita git y bash 4 o más reciente. Al terminar, reinicia Claude Code para que cargue los skills.
# Hace lo mismo que preparar-skills.ps1 y lleva la misma tabla.

set -euo pipefail

# Tabla de skills, igual en preparar-skills.ps1. Columnas: repositorio en GitHub, commit fijo,
# ruta en el repositorio y carpeta (o archivo) en .claude/skills. Las filas se procesan en orden.
#   skills/*    copia cada carpeta de skills/ que tenga SKILL.md, con su mismo nombre.
#   command.md  es la copia local de las reglas de web-design-guidelines (CLAUDE.md, sección Web):
#               va dentro de la carpeta que trae la fila anterior.
TABLA='
Leonxlnx/taste-skill                  f6b76575f949707b4e3c37cd86cb44b0b98643e8  skills/taste-skill            taste-skill
pbakaus/impeccable                    b4bff1626c344067788c2679f048a20057c7cc5a  .claude/skills/impeccable     impeccable
emilkowalski/skills                   4061b67b8d976a186aca118594f54b638c5f718a  skills/*                      *
anthropics/skills                     2c5958ecac7cee2b583967a2c4981d0f4a75c579  skills/frontend-design        frontend-design
wondelai/skills                       d8d5d75f83da9f16d8aad5bab5f5b341a4770a30  refactoring-ui                refactoring-ui
vercel-labs/agent-skills              1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62  skills/web-design-guidelines  web-design-guidelines
vercel-labs/web-interface-guidelines  434b7f91364665f2f733b310ec54809bf8f37937  command.md                    web-design-guidelines/command.md
'

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skills="$raiz/.claude/skills"
manifiesto="$skills/VERSIONES.txt"
scripts_con_tabla=("$raiz/scripts/preparar-skills.sh" "$raiz/scripts/preparar-skills.ps1")

uso() {
  cat <<'FIN'
Uso, desde la raíz del repositorio:
  ./scripts/preparar-skills.sh                trae los skills en los commits fijos de la tabla
  ./scripts/preparar-skills.sh --actualizar   trae la última versión, muestra qué commits cambiaron
                                              y los anota en la tabla de los dos scripts
FIN
}

# git sin conversión de fin de línea, con rutas largas en Windows y sin avisos de HEAD suelto.
g() {
  git -c core.longpaths=true -c core.autocrlf=false -c core.quotepath=false -c advice.detachedHead=false "$@"
}

# Nombres de carpeta que el script puede crear y borrar dentro de .claude/skills.
nombre_valido() {
  [[ "$1" =~ ^[A-Za-z0-9_][A-Za-z0-9._-]*$ ]]
}

# Cuando una ruta no aparece, muestra dónde quedaron las carpetas con SKILL.md (no copia nada).
sugerir() {
  local archivos="$1" ruta="$2" buscado mismas carpetas
  buscado="${ruta##*/}"
  # Sin tuberías que se corten antes de tiempo: con pipefail, un head o un grep -q darían SIGPIPE.
  mismas="$(awk -v b="$buscado" '{ n = split($0, p, "/"); for (i = 1; i <= n; i++) if (p[i] == b) { s = p[1]; for (j = 2; j <= i; j++) s = s "/" p[j]; print s; break } }' <<< "$archivos" | sort -u | awk 'NR <= 10')"
  carpetas="$(awk '/(^|\/)SKILL\.md$/ { sub(/\/?SKILL\.md$/, ""); if ($0 == "") $0 = "(raíz)"; if (++n <= 15) print }' <<< "$archivos")"
  if [ -n "$mismas" ]; then
    echo "    Rutas con el nombre «$buscado» en ese commit:" >&2
    printf '      %s\n' $mismas >&2
  fi
  if [ -n "$carpetas" ]; then
    echo "    Carpetas con SKILL.md en ese commit:" >&2
    printf '      %s\n' $carpetas >&2
  fi
  echo "    Si la ruta cambió, revisa esa carpeta y corrige la tabla de los dos scripts." >&2
}

# traer <n> <repositorio> <commit> <ruta> <carpeta>: descarga solo esa ruta del commit y la deja en $preparado.
traer() {
  local n="$1" repo="$2" commit="$3" ruta="$4" carpeta="$5"
  local dir="$tmp/r$n" archivos tipo base patron nombres nombre padre
  echo "Traigo $repo@${commit:0:7} ($ruta)..."

  g init -q "$dir" && g -C "$dir" remote add origin "https://github.com/$repo.git" || return 1
  if ! g -C "$dir" fetch -q --depth 1 --filter=blob:none origin "$commit"; then
    echo "    No pude traer ese commit. Revisa la conexión; si el commit ya no existe, corre con --actualizar." >&2
    return 1
  fi
  archivos="$(g -C "$dir" ls-tree -r --name-only FETCH_HEAD)" || return 1

  if [[ "$ruta" == */\* ]]; then
    tipo=varias
    base="${ruta%/\*}"
    nombres="$(awk -v base="$base/" 'index($0, base) == 1 { r = substr($0, length(base) + 1); if (r ~ /^[^\/]+\/SKILL\.md$/) { sub(/\/SKILL\.md$/, "", r); print r } }' <<< "$archivos")"
    if [ -z "$nombres" ]; then
      echo "    No hay carpetas con SKILL.md dentro de $base/." >&2
      sugerir "$archivos" "$base"
      return 1
    fi
    patron="/$base/"
  elif grep -Fxq -- "$ruta/SKILL.md" <<< "$archivos"; then
    tipo=carpeta
    patron="/$ruta/"
  elif grep -Fxq -- "$ruta" <<< "$archivos"; then
    tipo=archivo
    patron="/$ruta"
  else
    echo "    No encontré «$ruta» con su SKILL.md en ese commit." >&2
    sugerir "$archivos" "$ruta"
    return 1
  fi

  g -C "$dir" config core.sparseCheckout true || return 1
  printf '%s\n' "$patron" > "$dir/.git/info/sparse-checkout"
  if ! g -C "$dir" checkout -q FETCH_HEAD; then
    echo "    Falló la descarga de los archivos." >&2
    return 1
  fi

  case "$tipo" in
    carpeta)
      nombre_valido "$carpeta" || { echo "    La tabla trae un nombre de carpeta no válido: $carpeta" >&2; return 1; }
      [ ! -e "$preparado/$carpeta" ] || { echo "    Otra fila ya usa la carpeta $carpeta." >&2; return 1; }
      mv "$dir/$ruta" "$preparado/$carpeta" || return 1
      lineas_manifiesto+=("$repo $commit $ruta $carpeta")
      traido="$carpeta"
      ;;
    varias)
      local lista=()
      while IFS= read -r nombre; do
        nombre_valido "$nombre" || { echo "    $base/$nombre no es un nombre de carpeta válido." >&2; return 1; }
        [ ! -e "$preparado/$nombre" ] || { echo "    Otra fila ya usa la carpeta $nombre." >&2; return 1; }
        mv "$dir/$base/$nombre" "$preparado/$nombre" || return 1
        lineas_manifiesto+=("$repo $commit $base/$nombre $nombre")
        lista+=("$nombre")
      done <<< "$nombres"
      traido="${#lista[@]} carpetas: ${lista[*]}"
      ;;
    archivo)
      nombre_valido "${carpeta%%/*}" || { echo "    La tabla trae un destino no válido: $carpeta" >&2; return 1; }
      padre="$(dirname "$carpeta")"
      if [ "$padre" != "." ] && [ ! -d "$preparado/$padre" ]; then
        echo "    Falta la carpeta $padre: la trae una fila anterior de la tabla." >&2
        return 1
      fi
      mv -f "$dir/$ruta" "$preparado/$carpeta" || return 1
      lineas_manifiesto+=("$repo $commit $ruta $carpeta")
      traido="$carpeta"
      ;;
  esac
}

main() {
  local actualizar=0
  case "${1:-}" in
    "") ;;
    --actualizar) actualizar=1 ;;
    -h | --help | --ayuda) uso; return 0 ;;
    *) echo "Opción desconocida: $1" >&2; uso >&2; return 2 ;;
  esac
  if [ $# -gt 1 ]; then
    echo "Sobran opciones: $*" >&2
    uso >&2
    return 2
  fi
  command -v git > /dev/null 2>&1 || { echo "Falta git: instálalo y vuelve a correr el script." >&2; return 1; }

  local filas=() linea
  while IFS= read -r linea; do
    linea="${linea%$'\r'}"
    if [ -n "${linea// /}" ]; then filas+=("$linea"); fi
  done <<< "$TABLA"

  local fallas=0 cambios=() i repo commit ruta carpeta ultimo
  if [ "$actualizar" = 1 ]; then
    echo "Busco el último commit de cada repositorio..."
    for i in "${!filas[@]}"; do
      read -r repo commit ruta carpeta <<< "${filas[$i]}"
      ultimo="$(git ls-remote "https://github.com/$repo.git" HEAD 2> /dev/null | cut -f1 || true)"
      if [[ ! "$ultimo" =~ ^[0-9a-f]{40}$ ]]; then
        printf '  FALLA   %-38s no pude consultar su último commit\n' "$repo"
        fallas=$((fallas + 1))
      elif [ "$ultimo" = "$commit" ]; then
        printf '  igual   %-38s %s\n' "$repo" "${commit:0:7}"
      else
        printf '  cambió  %-38s %s -> %s\n' "$repo" "${commit:0:7}" "${ultimo:0:7}"
        cambios+=("$commit $ultimo $repo")
        filas[$i]="$repo $ultimo $ruta $carpeta"
      fi
    done
    if [ "$fallas" -gt 0 ]; then
      echo "No pude consultar todos los repositorios: no cambié nada."
      return 1
    fi
  fi

  mkdir -p "$skills"
  rm -rf "$skills"/.temporal.*
  tmp="$(mktemp -d "$skills/.temporal.XXXXXX")"
  trap 'rm -rf "$tmp"' EXIT
  preparado="$tmp/preparado"
  mkdir -p "$preparado"

  local resumen=() n=0
  lineas_manifiesto=()
  traido=""
  for linea in "${filas[@]}"; do
    read -r repo commit ruta carpeta <<< "$linea"
    n=$((n + 1))
    if traer "$n" "$repo" "$commit" "$ruta" "$carpeta"; then
      resumen+=("  OK     $repo@${commit:0:7} -> $traido")
    else
      resumen+=("  FALLA  $repo@${commit:0:7} ($ruta)")
      fallas=$((fallas + 1))
    fi
  done

  echo
  echo "Resumen"
  printf '%s\n' "${resumen[@]}"
  if [ "$fallas" -gt 0 ]; then
    echo "Hubo $fallas falla(s): no cambié nada en .claude/skills."
    return 1
  fi

  # Reemplaza lo que instaló la corrida anterior (según su manifiesto) y lo que se instala ahora.
  local quitar=() nombre total
  if [ -f "$manifiesto" ]; then
    while read -r _ _ _ carpeta; do
      if [ -n "${carpeta:-}" ]; then quitar+=("${carpeta%%/*}"); fi
    done < <(grep -v '^#' "$manifiesto" || true)
  fi
  for nombre in "$preparado"/*; do quitar+=("$(basename "$nombre")"); done
  for nombre in "${quitar[@]}"; do
    if nombre_valido "$nombre"; then rm -rf "${skills:?}/$nombre"; fi
  done
  total=0
  for nombre in "$preparado"/*; do
    mv "$nombre" "$skills/"
    total=$((total + 1))
  done
  {
    echo "# Skills de frontend de AccesIA. Lo escribe scripts/preparar-skills; no lo edites a mano."
    echo "# Columnas: repositorio, commit, ruta en el repositorio y carpeta (o archivo) en .claude/skills."
    printf '%s\n' "${lineas_manifiesto[@]}"
  } > "$manifiesto"

  echo "Listo: $total carpetas en .claude/skills; los commits quedan en .claude/skills/VERSIONES.txt."

  if [ "$actualizar" = 1 ]; then
    if [ "${#cambios[@]}" -eq 0 ]; then
      echo "Todos los repositorios siguen en su commit fijo: la tabla no cambia."
    else
      local archivo contenido anterior nuevo
      for archivo in "${scripts_con_tabla[@]}"; do
        if [ ! -f "$archivo" ]; then
          echo "No encontré $archivo: actualiza su tabla a mano."
          continue
        fi
        # Reemplazo en bash, sin sed ni awk: en Git Bash esos quitan los CR del .ps1.
        # Así se conservan el BOM, el CRLF del .ps1 y el modo de cada archivo.
        contenido="$(cat "$archivo"; printf x)"
        contenido="${contenido%x}"
        for linea in "${cambios[@]}"; do
          read -r anterior nuevo repo <<< "$linea"
          contenido="${contenido//"$anterior"/"$nuevo"}"
        done
        printf '%s' "$contenido" > "$archivo"
      done
      echo "Anoté los commits nuevos en la tabla de preparar-skills.sh y preparar-skills.ps1."
      echo "Revisa el cambio (git diff scripts/), prueba los skills y súbelo en un PR."
      for linea in "${cambios[@]}"; do
        read -r anterior nuevo repo <<< "$linea"
        if [ "$repo" = "vercel-labs/web-interface-guidelines" ]; then
          echo "Cambió la copia de command.md: actualiza también el commit que nombra CLAUDE.md (sección Web)."
        fi
      done
    fi
  fi
  echo "Reinicia Claude Code para que cargue los skills."
}

# Todo corre dentro de main: bash ya leyó el script entero cuando --actualizar lo reescribe.
{ main "$@"; exit $?; }
