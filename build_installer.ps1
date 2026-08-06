# CleanMyCompu - arma el installer con Inno Setup, con UI de progreso.
# Todo en ASCII para evitar problemas de encoding con Windows PowerShell 5.1.

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Set-Location $PSScriptRoot

$form = New-Object System.Windows.Forms.Form
$form.Text = "CleanMyCompu - Armando Installer"
$form.Size = New-Object System.Drawing.Size(680, 460)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.BackColor = [System.Drawing.Color]::White
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9)

$title = New-Object System.Windows.Forms.Label
$title.Text = "Armando CleanMyCompu-Setup.exe"
$title.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$title.ForeColor = [System.Drawing.Color]::FromArgb(29, 29, 31)
$title.Location = New-Object System.Drawing.Point(24, 20)
$title.Size = New-Object System.Drawing.Size(640, 32)
$form.Controls.Add($title)

$subtitle = New-Object System.Windows.Forms.Label
$subtitle.Text = "El installer sale en installer_output - es lo que le mandas a tu pareja."
$subtitle.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$subtitle.ForeColor = [System.Drawing.Color]::FromArgb(110, 110, 115)
$subtitle.Location = New-Object System.Drawing.Point(24, 56)
$subtitle.Size = New-Object System.Drawing.Size(640, 20)
$form.Controls.Add($subtitle)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = "Preparando..."
$statusLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$statusLabel.Location = New-Object System.Drawing.Point(24, 92)
$statusLabel.Size = New-Object System.Drawing.Size(640, 24)
$form.Controls.Add($statusLabel)

$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(24, 122)
$progress.Size = New-Object System.Drawing.Size(632, 22)
$progress.Style = "Continuous"
$progress.Value = 0
$form.Controls.Add($progress)

$logLabel = New-Object System.Windows.Forms.Label
$logLabel.Text = "Detalle:"
$logLabel.Location = New-Object System.Drawing.Point(24, 158)
$logLabel.Size = New-Object System.Drawing.Size(200, 20)
$form.Controls.Add($logLabel)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Multiline = $true
$logBox.ScrollBars = "Vertical"
$logBox.ReadOnly = $true
$logBox.Location = New-Object System.Drawing.Point(24, 182)
$logBox.Size = New-Object System.Drawing.Size(632, 180)
$logBox.Font = New-Object System.Drawing.Font("Consolas", 8)
$logBox.BackColor = [System.Drawing.Color]::FromArgb(245, 245, 247)
$logBox.WordWrap = $false
$form.Controls.Add($logBox)

$openBtn = New-Object System.Windows.Forms.Button
$openBtn.Text = "Abrir carpeta installer_output"
$openBtn.Location = New-Object System.Drawing.Point(340, 380)
$openBtn.Size = New-Object System.Drawing.Size(190, 32)
$openBtn.FlatStyle = "Flat"
$openBtn.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(200, 200, 205)
$openBtn.BackColor = [System.Drawing.Color]::White
$openBtn.Enabled = $false
$openBtn.Add_Click({
    Start-Process explorer.exe -ArgumentList "$PSScriptRoot\installer_output"
})
$form.Controls.Add($openBtn)

$closeBtn = New-Object System.Windows.Forms.Button
$closeBtn.Text = "Cerrar"
$closeBtn.Location = New-Object System.Drawing.Point(540, 380)
$closeBtn.Size = New-Object System.Drawing.Size(116, 32)
$closeBtn.FlatStyle = "Flat"
$closeBtn.BackColor = [System.Drawing.Color]::FromArgb(52, 199, 89)
$closeBtn.ForeColor = [System.Drawing.Color]::White
$closeBtn.FlatAppearance.BorderSize = 0
$closeBtn.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$closeBtn.Enabled = $false
$closeBtn.Add_Click({ $form.Close() })
$form.Controls.Add($closeBtn)

function Set-Progress {
    param([int]$percent, [string]$status)
    $script:progress.Value = [Math]::Min(100, [Math]::Max(0, $percent))
    if ($status) { $script:statusLabel.Text = $status }
    [System.Windows.Forms.Application]::DoEvents()
}

function Add-Log {
    param([string]$text)
    if (-not $text) { return }
    $ts = Get-Date -Format "HH:mm:ss"
    $script:logBox.AppendText("[$ts] $text`r`n")
    $script:logBox.SelectionStart = $script:logBox.Text.Length
    $script:logBox.ScrollToCaret()
    [System.Windows.Forms.Application]::DoEvents()
}

function Find-InnoSetup {
    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        "C:\Program Files\Inno Setup 5\ISCC.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    $inPath = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }
    return $null
}

function Show-InnoMissing {
    [System.Windows.Forms.MessageBox]::Show(
        "No encontre Inno Setup instalado.`n`n" +
        "Descargalo GRATIS de:`nhttps://jrsoftware.org/isdl.php`n`n" +
        "Instalalo con las opciones por defecto y volve a correr build_installer.bat.",
        "Falta Inno Setup",
        "OK", "Warning"
    ) | Out-Null
    Start-Process "https://jrsoftware.org/isdl.php"
}

function Run-BuildInstaller {
    try {
        Set-Progress 5 "Chequeando dist\CleanMyCompu\CleanMyCompu.exe..."
        if (-not (Test-Path "dist\CleanMyCompu\CleanMyCompu.exe")) {
            Add-Log "ERROR: falta el .exe compilado. Corre build_win.bat primero."
            Set-Progress 100 "Falta el .exe compilado"
            return $false
        }
        Add-Log "OK: encontre dist\CleanMyCompu\CleanMyCompu.exe"

        Set-Progress 15 "Buscando Inno Setup..."
        $iscc = Find-InnoSetup
        if (-not $iscc) {
            Add-Log "No encontre ISCC.exe. Abriendo la pagina de descarga de Inno Setup..."
            Set-Progress 100 "Falta Inno Setup"
            Show-InnoMissing
            return $false
        }
        Add-Log "OK: Inno Setup en $iscc"

        Set-Progress 25 "Compilando installer con Inno Setup..."
        # Barra marquee (indeterminada) porque ISCC no reporta progreso lineal
        $script:progress.Style = "Marquee"
        $script:progress.MarqueeAnimationSpeed = 30

        # .NET Process directo (evita bug de Start-Process con ExitCode vacio)
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $iscc
        $psi.Arguments = "installer.iss"
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.WorkingDirectory = $PSScriptRoot

        $p = New-Object System.Diagnostics.Process
        $p.StartInfo = $psi

        $script:iscOutBuf = New-Object System.Text.StringBuilder
        $script:iscErrBuf = New-Object System.Text.StringBuilder

        $outAction = {
            if (-not [string]::IsNullOrEmpty($EventArgs.Data)) {
                [void]$Event.MessageData.AppendLine($EventArgs.Data)
            }
        }
        $subOut = Register-ObjectEvent -InputObject $p -EventName OutputDataReceived `
            -MessageData $script:iscOutBuf -Action $outAction
        $subErr = Register-ObjectEvent -InputObject $p -EventName ErrorDataReceived `
            -MessageData $script:iscErrBuf -Action $outAction

        $p.Start() | Out-Null
        $p.BeginOutputReadLine()
        $p.BeginErrorReadLine()

        $lastOutLen = 0
        while (-not $p.HasExited) {
            $outText = $script:iscOutBuf.ToString()
            if ($outText.Length -gt $lastOutLen) {
                foreach ($l in $outText.Substring($lastOutLen) -split "`r?`n") {
                    if ($l.Trim()) { Add-Log $l.TrimEnd() }
                }
                $lastOutLen = $outText.Length
            }
            [System.Windows.Forms.Application]::DoEvents()
            Start-Sleep -Milliseconds 200
        }

        # CRITICO: WaitForExit para poblar ExitCode
        $p.WaitForExit()
        Start-Sleep -Milliseconds 300

        # Drenar output restante
        $outText = $script:iscOutBuf.ToString()
        if ($outText.Length -gt $lastOutLen) {
            foreach ($l in $outText.Substring($lastOutLen) -split "`r?`n") {
                if ($l.Trim()) { Add-Log $l.TrimEnd() }
            }
        }
        $errText = $script:iscErrBuf.ToString()
        if ($errText.Trim()) {
            foreach ($l in $errText -split "`r?`n") {
                if ($l.Trim()) { Add-Log ("! " + $l.TrimEnd()) }
            }
        }

        try {
            Unregister-Event -SourceIdentifier $subOut.Name -ErrorAction SilentlyContinue
            Unregister-Event -SourceIdentifier $subErr.Name -ErrorAction SilentlyContinue
        } catch { }

        $script:progress.Style = "Continuous"

        $rc = $p.ExitCode
        Add-Log "  ISCC exit code: $rc"

        # Verificacion ground-truth: si el .exe existe, es exito aunque ExitCode sea raro
        $expectedExe = Get-ChildItem "installer_output\*.exe" -ErrorAction SilentlyContinue |
                       Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $recentEnough = $expectedExe -and (New-TimeSpan -Start $expectedExe.LastWriteTime -End (Get-Date)).TotalMinutes -lt 2

        if ($rc -ne 0 -and -not $recentEnough) {
            Add-Log "ERROR: ISCC fallo con codigo $rc"
            Set-Progress 100 "Fallo la compilacion del installer"
            return $false
        }
        if ($rc -ne 0 -and $recentEnough) {
            Add-Log "AVISO: ISCC devolvio codigo raro ($rc) pero el .exe SI se genero, todo OK."
        }

        $out = Get-ChildItem "installer_output\*.exe" -ErrorAction SilentlyContinue |
               Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($out) {
            $sizeMb = [Math]::Round($out.Length / 1MB, 1)
            Add-Log ""
            Add-Log "==============================================="
            Add-Log "LISTO! Installer generado:"
            Add-Log "  $($out.FullName)"
            Add-Log "  Tamano: $sizeMb MB"
            Add-Log "==============================================="
            Add-Log ""
            Add-Log "PARA MANDAR A TU PAREJA:"
            Add-Log "  1. Copia $($out.Name) a un pendrive, WeTransfer, o Google Drive"
            Add-Log "  2. Que doble-clic al .exe -> wizard -> Siguiente -> Instalar"
            Add-Log "  3. Si Windows Defender avisa 'Windows protegio tu equipo':"
            Add-Log "     Mas informacion -> Ejecutar de todos modos"
            Add-Log ""
        }
        Set-Progress 100 "Listo - $($out.Name)"
        return $true
    } catch {
        Add-Log "EXCEPCION: $_"
        Set-Progress 100 "Excepcion inesperada"
        return $false
    }
}

$form.Add_Shown({
    $ok = Run-BuildInstaller
    $closeBtn.Enabled = $true
    $openBtn.Enabled = $ok
    if (-not $ok) {
        $closeBtn.Text = "Cerrar (con errores)"
        $closeBtn.BackColor = [System.Drawing.Color]::FromArgb(255, 59, 48)
    }
})

[void]$form.ShowDialog()
