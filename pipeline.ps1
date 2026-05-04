$defaultFile = "C:\Users\tomat\OneDrive\デスクトップ\fx\バックテスト\USDJPY-ボリンジャーバンド逆張り戦略.py"
$inputFile = Read-Host "File path (Enterでデフォルト)"
if ($inputFile -eq "") { $file = $defaultFile } else { $file = $inputFile }
Write-Host "対象ファイル: $file"

while ($true) {
    $design = Read-Host "設計を入力"
    if ($design -eq "" -or $design -eq "quit") { break }
    python "C:\Users\tomat\OneDrive\デスクトップ\fx\プログラムするうえで\ollama_groq_pipeline.py" --file "$file" --design "$design"
    $ans = Read-Host "続けて修正する？(y/n)"
    if ($ans -eq "n") { break }
}
Write-Host "終了"