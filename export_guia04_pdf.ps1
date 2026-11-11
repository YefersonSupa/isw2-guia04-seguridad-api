$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($scriptDir) { Set-Location $scriptDir }

try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $fullPptx = (Resolve-Path "Guia4_Act1y2_Seguridad_ISW_Equipo05.pptx").Path
    $fullPdf = [System.IO.Path]::ChangeExtension($fullPptx, ".pdf")
    Write-Host "Opening $fullPptx..."
    $presentation = $ppt.Presentations.Open($fullPptx, $false, $false, $false)
    Write-Host "Exporting to $fullPdf..."
    $presentation.SaveAs($fullPdf, 32) # 32 = ppSaveAsPDF
    $presentation.Close()
    $ppt.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($ppt) | Out-Null
    Write-Host "SUCCESS: PDF generated at $fullPdf"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
}

