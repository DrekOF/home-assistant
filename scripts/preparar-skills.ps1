# Nombre: preparar-skills.ps1
# Descripción: Trae los skills de frontend a .claude/skills/ en los commits fijos de su tabla (Windows).
# Fecha de creación: 2026-11-11
# Actualización: 2026-11-11
# Autor: Equipo AccesIA
# Versión: 1.0
#
# Uso, desde la raíz del repositorio:
#   .\scripts\preparar-skills.ps1               trae los skills en los commits fijos de la tabla
#   .\scripts\preparar-skills.ps1 -Actualizar   trae la última versión de cada repositorio, muestra qué
#                                               commits cambiaron y anota los nuevos en la tabla de los dos scripts
#
# Necesita git (Git for Windows). Al terminar, reinicia Claude Code para que cargue los skills.
# Hace lo mismo que preparar-skills.sh y lleva la misma tabla.

param([switch]$Actualizar)

$ErrorActionPreference = 'Stop'

# Tabla de skills, igual en preparar-skills.sh. Columnas: repositorio en GitHub, commit fijo,
# ruta en el repositorio y carpeta (o archivo) en .claude/skills. Las filas se procesan en orden.
#   skills/*    copia cada carpeta de skills/ que tenga SKILL.md, con su mismo nombre.
#   command.md  es la copia local de las reglas de web-design-guidelines (CLAUDE.md, sección Web):
#               va dentro de la carpeta que trae la fila anterior.
$Tabla = @'
Leonxlnx/taste-skill                  f6b76575f949707b4e3c37cd86cb44b0b98643e8  skills/taste-skill            taste-skill
pbakaus/impeccable                    b4bff1626c344067788c2679f048a20057c7cc5a  .claude/skills/impeccable     impeccable
emilkowalski/skills                   4061b67b8d976a186aca118594f54b638c5f718a  skills/*                      *
anthropics/skills                     2c5958ecac7cee2b583967a2c4981d0f4a75c579  skills/frontend-design        frontend-design
wondelai/skills                       d8d5d75f83da9f16d8aad5bab5f5b341a4770a30  refactoring-ui                refactoring-ui
vercel-labs/agent-skills              1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62  skills/web-design-guidelines  web-design-guidelines
vercel-labs/web-interface-guidelines  434b7f91364665f2f733b310ec54809bf8f37937  command.md                    web-design-guidelines/command.md
'@

$raiz = Split-Path -Parent $PSScriptRoot
$skills = Join-Path $raiz '.claude\skills'
$manifiesto = Join-Path $skills 'VERSIONES.txt'
$scriptsConTabla = @((Join-Path $PSScriptRoot 'preparar-skills.ps1'), (Join-Path $PSScriptRoot 'preparar-skills.sh'))
$sinBom = New-Object System.Text.UTF8Encoding $false

# git sin conversión de fin de línea, con rutas largas y sin avisos de HEAD suelto.
# Devuelve el código de salida y las líneas de la salida; si falla, muestra lo que dijo git.
function Invocar-Git {
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $salida = & git -c core.longpaths=true -c core.autocrlf=false -c core.quotepath=false -c advice.detachedHead=false @args 2>&1
        $codigo = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $anterior
    }
    $lineas = New-Object System.Collections.Generic.List[string]
    $errores = New-Object System.Collections.Generic.List[string]
    foreach ($s in @($salida)) {
        if ($s -is [System.Management.Automation.ErrorRecord]) { $errores.Add($s.ToString()) } else { $lineas.Add([string]$s) }
    }
    if ($codigo -ne 0) { foreach ($e in $errores) { Write-Host "    $e" } }
    return [pscustomobject]@{ Codigo = $codigo; Lineas = $lineas.ToArray() }
}

# Nombres de carpeta que el script puede crear y borrar dentro de .claude/skills.
function Nombre-Valido([string]$nombre) {
    return $nombre -cmatch '^[A-Za-z0-9_][A-Za-z0-9._-]*$'
}

# Cuando una ruta no aparece, muestra dónde quedaron las carpetas con SKILL.md (no copia nada).
function Sugerir([string[]]$archivos, [string]$ruta) {
    $buscado = ($ruta -split '/')[-1]
    $mismas = @($archivos | ForEach-Object {
            $partes = $_ -split '/'
            $i = [Array]::IndexOf($partes, $buscado)
            if ($i -ge 0) { $partes[0..$i] -join '/' }
        } | Sort-Object -Unique | Select-Object -First 10)
    $carpetas = @($archivos | Where-Object { $_ -cmatch '(^|/)SKILL\.md$' } | ForEach-Object {
            $c = $_ -creplace '/?SKILL\.md$', ''
            if ($c) { $c } else { '(raíz)' }
        } | Select-Object -First 15)
    if ($mismas.Count -gt 0) {
        Write-Host "    Rutas con el nombre «$buscado» en ese commit:"
        foreach ($m in $mismas) { Write-Host "      $m" }
    }
    if ($carpetas.Count -gt 0) {
        Write-Host '    Carpetas con SKILL.md en ese commit:'
        foreach ($c in $carpetas) { Write-Host "      $c" }
    }
    Write-Host '    Si la ruta cambió, revisa esa carpeta y corrige la tabla de los dos scripts.'
}

# Descarga solo la ruta de la fila en su commit y la deja en $preparado. Devuelve $true si salió bien.
function Traer([int]$n, $fila) {
    $dir = Join-Path $tmp "r$n"
    $ruta = $fila.Ruta
    $carpeta = $fila.Carpeta
    Write-Host "Traigo $($fila.Repo)@$($fila.Commit.Substring(0, 7)) ($ruta)..."

    if ((Invocar-Git init -q $dir).Codigo -ne 0) { return $false }
    if ((Invocar-Git -C $dir remote add origin "https://github.com/$($fila.Repo).git").Codigo -ne 0) { return $false }
    if ((Invocar-Git -C $dir fetch -q --depth 1 --filter=blob:none origin $fila.Commit).Codigo -ne 0) {
        Write-Host '    No pude traer ese commit. Revisa la conexión; si el commit ya no existe, corre con -Actualizar.'
        return $false
    }
    $r = Invocar-Git -C $dir ls-tree -r --name-only FETCH_HEAD
    if ($r.Codigo -ne 0) { return $false }
    $archivos = $r.Lineas

    $nombres = @()
    if ($ruta.EndsWith('/*')) {
        $tipo = 'varias'
        $base = $ruta.Substring(0, $ruta.Length - 2)
        $prefijo = "$base/"
        $nombres = @($archivos | Where-Object { $_.StartsWith($prefijo, [StringComparison]::Ordinal) } | ForEach-Object {
                if ($_.Substring($prefijo.Length) -cmatch '^([^/]+)/SKILL\.md$') { $Matches[1] }
            })
        if ($nombres.Count -eq 0) {
            Write-Host "    No hay carpetas con SKILL.md dentro de $base/."
            Sugerir $archivos $base
            return $false
        }
        $patron = "/$base/"
    } elseif ($archivos -ccontains "$ruta/SKILL.md") {
        $tipo = 'carpeta'
        $patron = "/$ruta/"
    } elseif ($archivos -ccontains $ruta) {
        $tipo = 'archivo'
        $patron = "/$ruta"
    } else {
        Write-Host "    No encontré «$ruta» con su SKILL.md en ese commit."
        Sugerir $archivos $ruta
        return $false
    }

    if ((Invocar-Git -C $dir config core.sparseCheckout true).Codigo -ne 0) { return $false }
    [System.IO.File]::WriteAllText((Join-Path $dir '.git\info\sparse-checkout'), "$patron`n", $sinBom)
    if ((Invocar-Git -C $dir checkout -q FETCH_HEAD).Codigo -ne 0) {
        Write-Host '    Falló la descarga de los archivos.'
        return $false
    }

    switch ($tipo) {
        'carpeta' {
            if (-not (Nombre-Valido $carpeta)) { Write-Host "    La tabla trae un nombre de carpeta no válido: $carpeta"; return $false }
            $destino = Join-Path $preparado $carpeta
            if (Test-Path -LiteralPath $destino) { Write-Host "    Otra fila ya usa la carpeta $carpeta."; return $false }
            Move-Item -LiteralPath (Join-Path $dir $ruta) -Destination $destino
            $script:lineasManifiesto.Add("$($fila.Repo) $($fila.Commit) $ruta $carpeta")
            $script:traido = $carpeta
        }
        'varias' {
            foreach ($nombre in $nombres) {
                if (-not (Nombre-Valido $nombre)) { Write-Host "    $base/$nombre no es un nombre de carpeta válido."; return $false }
                $destino = Join-Path $preparado $nombre
                if (Test-Path -LiteralPath $destino) { Write-Host "    Otra fila ya usa la carpeta $nombre."; return $false }
                Move-Item -LiteralPath (Join-Path $dir "$base/$nombre") -Destination $destino
                $script:lineasManifiesto.Add("$($fila.Repo) $($fila.Commit) $base/$nombre $nombre")
            }
            $script:traido = "$($nombres.Count) carpetas: $($nombres -join ' ')"
        }
        'archivo' {
            if (-not (Nombre-Valido ($carpeta -split '/')[0])) { Write-Host "    La tabla trae un destino no válido: $carpeta"; return $false }
            $padre = Split-Path -Parent $carpeta
            if ($padre -and -not (Test-Path -LiteralPath (Join-Path $preparado $padre) -PathType Container)) {
                Write-Host "    Falta la carpeta ${padre}: la trae una fila anterior de la tabla."
                return $false
            }
            Move-Item -LiteralPath (Join-Path $dir $ruta) -Destination (Join-Path $preparado $carpeta) -Force
            $script:lineasManifiesto.Add("$($fila.Repo) $($fila.Commit) $ruta $carpeta")
            $script:traido = $carpeta
        }
    }
    return $true
}

function Preparar {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host 'Falta git: instala Git for Windows y vuelve a correr el script.'
        return 1
    }

    $filas = @($Tabla -split "\r?\n" | Where-Object { $_.Trim() } | ForEach-Object {
            $c = -split $_
            [pscustomobject]@{ Repo = $c[0]; Commit = $c[1]; Ruta = $c[2]; Carpeta = $c[3] }
        })

    $fallas = 0
    $cambios = @()
    if ($Actualizar) {
        Write-Host 'Busco el último commit de cada repositorio...'
        foreach ($fila in $filas) {
            $r = Invocar-Git ls-remote "https://github.com/$($fila.Repo).git" HEAD
            $ultimo = ''
            if ($r.Codigo -eq 0 -and $r.Lineas.Count -gt 0) { $ultimo = ($r.Lineas[0] -split "`t")[0] }
            if ($ultimo -cnotmatch '^[0-9a-f]{40}$') {
                Write-Host ('  FALLA   {0,-38} no pude consultar su último commit' -f $fila.Repo)
                $fallas++
            } elseif ($ultimo -eq $fila.Commit) {
                Write-Host ('  igual   {0,-38} {1}' -f $fila.Repo, $fila.Commit.Substring(0, 7))
            } else {
                Write-Host ('  cambió  {0,-38} {1} -> {2}' -f $fila.Repo, $fila.Commit.Substring(0, 7), $ultimo.Substring(0, 7))
                $cambios += [pscustomobject]@{ Anterior = $fila.Commit; Nuevo = $ultimo; Repo = $fila.Repo }
                $fila.Commit = $ultimo
            }
        }
        if ($fallas -gt 0) {
            Write-Host 'No pude consultar todos los repositorios: no cambié nada.'
            return 1
        }
    }

    $resumen = @()
    $n = 0
    foreach ($fila in $filas) {
        $n++
        $corto = "$($fila.Repo)@$($fila.Commit.Substring(0, 7))"
        if (Traer $n $fila) {
            $resumen += "  OK     $corto -> $script:traido"
        } else {
            $resumen += "  FALLA  $corto ($($fila.Ruta))"
            $fallas++
        }
    }

    Write-Host ''
    Write-Host 'Resumen'
    foreach ($l in $resumen) { Write-Host $l }
    if ($fallas -gt 0) {
        Write-Host "Hubo $fallas falla(s): no cambié nada en .claude/skills."
        return 1
    }

    # Reemplaza lo que instaló la corrida anterior (según su manifiesto) y lo que se instala ahora.
    $quitar = New-Object System.Collections.Generic.List[string]
    if (Test-Path -LiteralPath $manifiesto) {
        foreach ($l in [System.IO.File]::ReadAllLines($manifiesto)) {
            if ($l -match '^\s*#' -or -not $l.Trim()) { continue }
            $c = -split $l
            if ($c.Count -ge 4) { $quitar.Add(($c[3] -split '/')[0]) }
        }
    }
    $nuevos = @(Get-ChildItem -LiteralPath $preparado -Force)
    foreach ($item in $nuevos) { $quitar.Add($item.Name) }
    foreach ($nombre in $quitar) {
        $viejo = Join-Path $skills $nombre
        if ((Nombre-Valido $nombre) -and (Test-Path -LiteralPath $viejo)) { Remove-Item -LiteralPath $viejo -Recurse -Force }
    }
    foreach ($item in $nuevos) { Move-Item -LiteralPath $item.FullName -Destination (Join-Path $skills $item.Name) }
    $texto = "# Skills de frontend de AccesIA. Lo escribe scripts/preparar-skills; no lo edites a mano.`n" +
        "# Columnas: repositorio, commit, ruta en el repositorio y carpeta (o archivo) en .claude/skills.`n" +
        ($script:lineasManifiesto -join "`n") + "`n"
    [System.IO.File]::WriteAllText($manifiesto, $texto, $sinBom)

    Write-Host "Listo: $($nuevos.Count) carpetas en .claude/skills; los commits quedan en .claude/skills/VERSIONES.txt."

    if ($Actualizar) {
        if ($cambios.Count -eq 0) {
            Write-Host 'Todos los repositorios siguen en su commit fijo: la tabla no cambia.'
        } else {
            foreach ($archivo in $scriptsConTabla) {
                if (-not (Test-Path -LiteralPath $archivo)) { Write-Host "No encontré ${archivo}: actualiza su tabla a mano."; continue }
                # Reemplaza solo los commits: conserva el BOM del .ps1 y el fin de línea de cada archivo.
                $bytes = [System.IO.File]::ReadAllBytes($archivo)
                $conBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
                $contenido = $sinBom.GetString($bytes)
                if ($conBom) { $contenido = $contenido.Substring(1) }
                foreach ($c in $cambios) { $contenido = $contenido.Replace($c.Anterior, $c.Nuevo) }
                [System.IO.File]::WriteAllText($archivo, $contenido, (New-Object System.Text.UTF8Encoding $conBom))
            }
            Write-Host 'Anoté los commits nuevos en la tabla de preparar-skills.ps1 y preparar-skills.sh.'
            Write-Host 'Revisa el cambio (git diff scripts/), prueba los skills y súbelo en un PR.'
            if (@($cambios | Where-Object { $_.Repo -eq 'vercel-labs/web-interface-guidelines' }).Count -gt 0) {
                Write-Host 'Cambió la copia de command.md: actualiza también el commit que nombra CLAUDE.md (sección Web).'
            }
        }
    }
    Write-Host 'Reinicia Claude Code para que cargue los skills.'
    return 0
}

# git escribe en UTF-8: así PowerShell lee bien sus rutas.
$codificacionAnterior = $null
try { $codificacionAnterior = [Console]::OutputEncoding; [Console]::OutputEncoding = $sinBom } catch { }

New-Item -ItemType Directory -Force -Path $skills | Out-Null
Get-ChildItem -LiteralPath $skills -Directory -Force | Where-Object { $_.Name -like '.temporal.*' } | Remove-Item -Recurse -Force
$tmp = Join-Path $skills ('.temporal.' + [Guid]::NewGuid().ToString('N').Substring(0, 6))
$preparado = Join-Path $tmp 'preparado'
New-Item -ItemType Directory -Force -Path $preparado | Out-Null
$lineasManifiesto = New-Object System.Collections.Generic.List[string]
$traido = ''

$codigo = 1
try {
    $codigo = @(Preparar)[-1]
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    if ($codificacionAnterior) { try { [Console]::OutputEncoding = $codificacionAnterior } catch { } }
}
exit $codigo
