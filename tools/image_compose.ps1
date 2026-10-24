<#
    image_compose.ps1 - places an image (PNG, WebP, JPEG, BMP, GIF, TIFF ...) scaled onto a canvas
    and saves it as PNG. Uses the Windows imaging library (WIC/WPF), no extra software needed.

    Parameters:
      -Src              input image
      -Dst              output PNG (not needed with -Analyze)
      -Width/-Height    canvas size in pixels
      -Background       "transparent" or "green" (pure green RGB 0,255,0 for the in-game chroma key)
      -ScalePercent     character size in percent (100 = image fits the canvas exactly)
      -OffsetTopPercent distance of the image's top edge from the canvas top, in percent of the canvas height
      -OffsetXPercent   horizontal shift in percent of the canvas width (0 = centered)
      -RemoveGreen      remove a green-screen background from the input image
      -KeyLow/-KeyHigh  thresholds for -RemoveGreen on the "green excess" (G minus max(R,B)):
                        above KeyLow a pixel becomes partly transparent, above KeyHigh fully transparent
      -NoTrim           do NOT crop transparent borders automatically
      -Analyze          only analyze (size, transparency, green-screen suspicion) and print the result
#>
param(
    [Parameter(Mandatory = $true)][string]$Src,
    [string]$Dst = "",
    [int]$Width = 1110,
    [int]$Height = 2156,
    [ValidateSet("transparent", "green")][string]$Background = "transparent",
    [double]$ScalePercent = 100,
    [double]$OffsetTopPercent = 0,
    [double]$OffsetXPercent = 0,
    [switch]$RemoveGreen,
    [int]$KeyLow = 40,
    [int]$KeyHigh = 110,
    [switch]$NoTrim,
    [switch]$Analyze
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName PresentationCore, WindowsBase

# Pixel work in C# (PowerShell loops would be far too slow for large images)
Add-Type -TypeDefinition @"
using System;
using System.Globalization;
public static class FamImage {
    // buf: BGRA, not premultiplied
    public static string Analyze(byte[] buf, int w, int h) {
        long transparent = 0, total = (long)w * h;
        for (int i = 3; i < buf.Length; i += 4) if (buf[i] < 250) transparent++;
        int greenEdges = 0;
        int[][] pts = new int[][] {
            new int[]{2,2}, new int[]{w-3,2}, new int[]{2,h-3}, new int[]{w-3,h-3},
            new int[]{w/2,2}, new int[]{2,h/2}, new int[]{w-3,h/2} };
        foreach (int[] p in pts) {
            int o = (p[1] * w + p[0]) * 4;
            int b = buf[o], g = buf[o+1], r = buf[o+2], a = buf[o+3];
            if (a > 200 && g > 120 && g - Math.Max(r, b) > 60) greenEdges++;
        }
        return string.Format(CultureInfo.InvariantCulture, "transparent_pct={0:F1} green_edges={1}/7",
                             100.0 * transparent / total, greenEdges);
    }

    // Remove a green screen: alpha from the green excess, despill the edges
    public static void RemoveGreen(byte[] buf, int lo, int hi) {
        for (int i = 0; i < buf.Length; i += 4) {
            int b = buf[i], g = buf[i+1], r = buf[i+2], a = buf[i+3];
            int m = Math.Max(r, b);
            int excess = g - m;
            if (excess <= lo) continue;
            int na = excess >= hi ? 0 : a * (hi - excess) / (hi - lo);
            buf[i+1] = (byte)m;               // remove the green tint on edges
            buf[i+3] = (byte)Math.Min(a, na);
        }
    }

    // Bounding box of all visible pixels (alpha > thr): x, y, width, height
    public static int[] ContentBounds(byte[] buf, int w, int h, int thr) {
        int minX = w, minY = h, maxX = -1, maxY = -1;
        for (int y = 0; y < h; y++) {
            int row = y * w * 4;
            for (int x = 0; x < w; x++) {
                if (buf[row + x * 4 + 3] > thr) {
                    if (x < minX) minX = x; if (x > maxX) maxX = x;
                    if (y < minY) minY = y; if (y > maxY) maxY = y;
                }
            }
        }
        if (maxX < 0) return new int[]{0, 0, w, h};
        return new int[]{minX, minY, maxX - minX + 1, maxY - minY + 1};
    }

    public static byte[] Crop(byte[] buf, int w, int cx, int cy, int cw, int ch) {
        byte[] o = new byte[cw * ch * 4];
        for (int y = 0; y < ch; y++)
            Buffer.BlockCopy(buf, ((cy + y) * w + cx) * 4, o, y * cw * 4, cw * 4);
        return o;
    }

    // For the in-game chroma key: hard edges, so no greenish blended pixels appear.
    // Semi-transparent pixels become fully opaque (from 50 %) or fully transparent.
    public static void HardenAlpha(byte[] buf) {
        for (int i = 0; i < buf.Length; i += 4) {
            int a = buf[i+3];
            if (a >= 128) {
                if (a < 255) {                 // edge pixel: limit the green channel
                    int m = Math.Max(buf[i], buf[i+2]);
                    if (buf[i+1] > m) buf[i+1] = (byte)m;
                }
                buf[i+3] = 255;
            } else {
                buf[i+3] = 0;
            }
        }
    }
}
"@

# Decode; PreservePixelFormat is required, otherwise WebP loses its alpha channel
$fs = [System.IO.File]::OpenRead($Src)
try {
    $dec = [System.Windows.Media.Imaging.BitmapDecoder]::Create(
        $fs,
        [System.Windows.Media.Imaging.BitmapCreateOptions]::PreservePixelFormat,
        [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad)
    $frame = $dec.Frames[0]
} finally { $fs.Close() }

$conv = New-Object System.Windows.Media.Imaging.FormatConvertedBitmap(
    $frame, [System.Windows.Media.PixelFormats]::Bgra32, $null, 0)
$sw = $conv.PixelWidth; $sh = $conv.PixelHeight; $stride = $sw * 4
$buf = New-Object byte[] ($stride * $sh)
$conv.CopyPixels($buf, $stride, 0)
$decoderName = $dec.CodecInfo.FriendlyName -replace ' ', '_'

if ($Analyze) {
    $a = [FamImage]::Analyze($buf, $sw, $sh)
    Write-Output ("ANALYSIS source={0}x{1} decoder={2} {3}" -f $sw, $sh, $decoderName, $a)
    exit 0
}
if ($Dst -eq "") { throw "Parameter -Dst is missing." }

if ($RemoveGreen) { [FamImage]::RemoveGreen($buf, $KeyLow, $KeyHigh) }
if (-not $NoTrim) {
    # Crop empty (transparent) borders so only the character counts
    $bb = [FamImage]::ContentBounds($buf, $sw, $sh, 16)
    if ($bb[2] -lt $sw -or $bb[3] -lt $sh) {
        $buf = [FamImage]::Crop($buf, $sw, $bb[0], $bb[1], $bb[2], $bb[3])
        $sw = $bb[2]; $sh = $bb[3]; $stride = $sw * 4
    }
}
if ($Background -eq "green") { [FamImage]::HardenAlpha($buf) }

$bmp = [System.Windows.Media.Imaging.BitmapSource]::Create(
    $sw, $sh, 96, 96, [System.Windows.Media.PixelFormats]::Bgra32, $null, $buf, $stride)

# Fit without distortion, then grow/shrink by ScalePercent
$fit = [Math]::Min($Width / $sw, $Height / $sh) * ($ScalePercent / 100.0)
$dw = $sw * $fit; $dh = $sh * $fit
$x = ($Width - $dw) / 2 + $Width * $OffsetXPercent / 100.0
$y = $Height * $OffsetTopPercent / 100.0

$visual = New-Object System.Windows.Media.DrawingVisual
# Smooth scaling; on a green background the edges are hardened again afterwards
[System.Windows.Media.RenderOptions]::SetBitmapScalingMode($visual, [System.Windows.Media.BitmapScalingMode]::HighQuality)
$dc = $visual.RenderOpen()
$dc.DrawImage($bmp, (New-Object System.Windows.Rect($x, $y, $dw, $dh)))
$dc.Close()

$rtb = New-Object System.Windows.Media.Imaging.RenderTargetBitmap($Width, $Height, 96, 96, [System.Windows.Media.PixelFormats]::Pbgra32)
$rtb.Render($visual)

# Read back as non-premultiplied BGRA and, if needed, prepare for the green background
$outConv = New-Object System.Windows.Media.Imaging.FormatConvertedBitmap($rtb, [System.Windows.Media.PixelFormats]::Bgra32, $null, 0)
$ostride = $Width * 4
$obuf = New-Object byte[] ($ostride * $Height)
$outConv.CopyPixels($obuf, $ostride, 0)
if ($Background -eq "green") { [FamImage]::HardenAlpha($obuf) }
$final = [System.Windows.Media.Imaging.BitmapSource]::Create(
    $Width, $Height, 96, 96, [System.Windows.Media.PixelFormats]::Bgra32, $null, $obuf, $ostride)

if ($Background -eq "green") {
    # Replace transparent areas with pure green
    $visual2 = New-Object System.Windows.Media.DrawingVisual
    $dc2 = $visual2.RenderOpen()
    $green = New-Object System.Windows.Media.SolidColorBrush([System.Windows.Media.Color]::FromRgb(0, 255, 0))
    $dc2.DrawRectangle($green, $null, (New-Object System.Windows.Rect(0, 0, $Width, $Height)))
    $dc2.DrawImage($final, (New-Object System.Windows.Rect(0, 0, $Width, $Height)))
    $dc2.Close()
    $rtb2 = New-Object System.Windows.Media.Imaging.RenderTargetBitmap($Width, $Height, 96, 96, [System.Windows.Media.PixelFormats]::Pbgra32)
    $rtb2.Render($visual2)
    $final = $rtb2
}

$enc = New-Object System.Windows.Media.Imaging.PngBitmapEncoder
$enc.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($final))
$out = [System.IO.File]::Create($Dst)
try { $enc.Save($out) } finally { $out.Close() }

Write-Output ("OK source={0}x{1} decoder={2} target={3}x{4}" -f $conv.PixelWidth, $conv.PixelHeight, $decoderName, $Width, $Height)
