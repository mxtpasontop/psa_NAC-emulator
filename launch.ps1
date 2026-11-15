param([switch]$Rootfs)
$ErrorActionPreference = 'Stop'
$nacRoot = $PSScriptRoot
$nacQemu = Join-Path $nacRoot 'tools\qemu\qemu-system-arm.exe'
$nacImages = Join-Path $nacRoot 'images'
$nacArgs = @(
    '-M', 'sabrelite', '-accel', 'tcg,thread=multi', '-smp', '1', '-m', '1G',
    '-device', 'loader,addr=0x02098000,data=0x349,data-len=4',
    '-display', 'none', '-monitor', 'none', '-serial', 'stdio', '-nic', 'none',
    '-kernel', (Join-Path $nacImages 'zImage'),
    '-dtb', (Join-Path $nacImages 'board-headless.dtb'),
    '-initrd', (Join-Path $nacImages 'earlyaudio.cpio'),
    '-append', 'console=ttymxc0,115200 clk_ignore_unused nowatchdog rdinit=/bin/sh'
)
if ($Rootfs) {
    $nacCard = Join-Path $nacImages 'rootfs-sd.img'
    $nacArgs += @('-drive', "file=$nacCard,if=none,id=nacroot,format=raw,snapshot=on", '-device', 'sd-card,drive=nacroot,bus=sd-bus')
}
Write-Host 'Booting the NAC diagnostic shell with TCG software emulation. Ctrl+C stops QEMU.'
& $nacQemu @nacArgs
exit $LASTEXITCODE
