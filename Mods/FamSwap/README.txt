FamSwap 1.0 - replace Fam (the opponent) with your own images
=============================================================

EASIEST WAY: run FamSwap-Wizard.bat (in the FamSwap package folder).
It asks step by step for your image (PNG, WebP, JPEG ..., drag & drop into the window works),
removes a green-screen background if there is one, converts the image, puts it into this
folder and lets you adjust size and position.

Manual: put your images into this folder (...\Binaries\Win64\ue4ss\Mods\FamSwap\):

  bar.png   Fam behind the bar counter (search mode, before the match)
            - PNG WITH A TRANSPARENT BACKGROUND
            - 2220 x 4312 (or the same aspect ratio, e.g. 1110 x 2156), character top-center,
              head at the top - the counter hides the legs.

  game.png  Fam at the table during the drinking game (replaces her videos with a still image)
            - 16:9 (e.g. 1920 x 1080), pure green background RGB(0,255,0), character top-center

If a file is missing, the original Fam stays.
In-game: F8 = toggle replacement on/off, F9 = reload images (no restart needed).

Example images: examples\example_bar.png and examples\example_game.png
(rename to bar.png / game.png and copy them into this folder to try it out).

Log: ...\Binaries\Win64\ue4ss\UE4SS.log (lines starting with [FamSwap]).
