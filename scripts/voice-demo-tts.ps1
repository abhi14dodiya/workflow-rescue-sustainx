param(
    [Parameter(Mandatory = $true)][string]$Manifest,
    [string]$Voice = 'Microsoft Zira Desktop'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $speech.SelectVoice($Voice)
    $speech.Rate = 0
    $items = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($item in $items) {
        $speech.SetOutputToWaveFile($item.wav)
        $speech.Speak($item.text)
        $speech.SetOutputToNull()
    }
} finally {
    $speech.Dispose()
}
