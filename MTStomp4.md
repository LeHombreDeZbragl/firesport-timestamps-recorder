$src = "c:\Users\tombu\Documents\Hasici\FIRE\zl\2026\zbraslav\zips\mts"
$dst = "c:\Users\tombu\Documents\Hasici\FIRE\zl\2026\zbraslav\in"

if (-not (Test-Path $dst)) {
    New-Item -ItemType Directory -Path $dst | Out-Null
}

Get-ChildItem $src -Filter *.MTS | ForEach-Object {
    $out = Join-Path $dst ($_.BaseName + ".mp4")
    ffmpeg -i $_.FullName `
        -vf yadif `
        -c:v libx264 `
        -crf 18 `
        -preset slow `
        $out
}