param(
    [Parameter(Mandatory=$true)]
    [string]$Script
)

$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) { $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $pyCmd) {
    Write-Error "No se encontro Python en el PATH. Instala Python 3.x y agregalo al PATH."
    exit 1
}
$pyFull = $pyCmd.Source

$pysparkDir = Join-Path (Split-Path $pyFull -Parent) 'Lib\site-packages\pyspark'
if (-not (Test-Path $pysparkDir)) {
    Write-Error "No se encontro PySpark en $pysparkDir. Ejecuta: pip install pyspark"
    exit 1
}

$shell      = New-Object -ComObject Scripting.FileSystemObject
$pyShort    = $shell.GetFile($pyFull).ShortPath
$sparkShort = $shell.GetFolder($pysparkDir).ShortPath

$env:PYSPARK_PYTHON        = $pyShort
$env:PYSPARK_DRIVER_PYTHON = $pyShort
$env:SPARK_HOME            = $sparkShort
$env:HADOOP_HOME           = 'C:\hadoop'

Write-Host "Python         : $pyFull"
Write-Host "PYSPARK_PYTHON : $pyShort"
Write-Host "SPARK_HOME     : $sparkShort"
Write-Host "Ejecutando     : $Script"
Write-Host ("-" * 60)

Set-Location $PSScriptRoot
& $pyFull $Script