# Favourite `cd ...; claude` commands on UpArrow (empty prompt), then the normal history.
# DownArrow walks back. With text typed, arrows work as always. Favourites are NOT written to history.
# Switch on from the profile:  if ($env:TERM_PROGRAM -eq 'vscode') { . "<LAB>/extras/terminal-favoritos/favoritos.ps1" }

# ---- the list: favoritos.txt next to this file, one command per line (made by detectar.py, after the person's OK) ----
$script:Favoritos = @(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'favoritos.txt') -Encoding UTF8 -ErrorAction SilentlyContinue |
    Where-Object { $_.Trim() -and -not $_.StartsWith('#') })
if ($script:Favoritos.Count -eq 0) { return }   # no list, no key rebinding
# ---------------------------------------------------------
$script:favIdx = -1     # >=0: showing Favoritos[favIdx]
$script:favDepth = 0    # >0: that many history steps past the last favourite
Import-Module PSReadLine -ErrorAction SilentlyContinue
$PSRL = [Microsoft.PowerShell.PSConsoleReadLine]

function script:FavLine { $l = $null; $c = 0; $PSRL::GetBufferState([ref]$l, [ref]$c); $l }
function script:FavTrace { if ($global:FavTraceHook) { & $global:FavTraceHook } }   # tests only
function script:FavReset { $script:favIdx = -1; $script:favDepth = 0 }
function script:FavShow($i) { $PSRL::Replace(0, (FavLine).Length, $script:Favoritos[$i]); $script:favIdx = $i }

try {
    Set-PSReadLineKeyHandler -Key UpArrow -BriefDescription FavUp -ScriptBlock {
        $line = FavLine
        if ($line -eq '') { FavReset }
        elseif ($favDepth -eq 0 -and $favIdx -ge 0 -and $line -ne $Favoritos[$favIdx]) { FavReset }   # edited: normal behaviour
        if ($favIdx -ge 0 -or $favDepth -gt 0) {
            if ($favDepth -eq 0 -and $favIdx -lt $Favoritos.Count - 1) { FavShow ($favIdx + 1); FavTrace; return }
            $script:favIdx = $Favoritos.Count - 1; $script:favDepth++
            $PSRL::PreviousHistory(); FavTrace; return
        }
        if ($line -eq '') { FavShow 0 } else { $PSRL::PreviousHistory() }
        FavTrace
    }
    Set-PSReadLineKeyHandler -Key DownArrow -BriefDescription FavDown -ScriptBlock {
        $line = FavLine
        if ($line -eq '') { FavReset }
        elseif ($favDepth -eq 0 -and $favIdx -ge 0 -and $line -ne $Favoritos[$favIdx]) { FavReset }
        if ($favDepth -gt 0) {
            $PSRL::NextHistory(); $script:favDepth--; FavTrace; return   # at 0 the buffer is the last favourite again
        }
        if ($favIdx -gt 0) { FavShow ($favIdx - 1) }
        elseif ($favIdx -eq 0) { $PSRL::Replace(0, $line.Length, ''); FavReset }
        else { $PSRL::NextHistory() }
        FavTrace
    }
    # new prompt = new command line: forget the state (also after Ctrl+C / Enter)
    $script:__favPrompt = $function:prompt
    function global:prompt { FavReset; & $script:__favPrompt }
} catch { }
