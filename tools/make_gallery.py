"""Erzeugt eine HTML-Übersicht aller Spielvideos (zum Anschauen im Browser).

Benutzung: py make_gallery.py <Ordner mit Bacchus/Movie/...> <ausgabe.html>
Die Videos werden relativ zur HTML-Datei verlinkt.
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mp4_info  # noqa: E402

# Bedeutung der Namensbestandteile (aus Dateinamen und Spielablauf abgeleitet)
BEDEUTUNG = [
    ("STANDBY_A_TYPEA_MABATAKI", "Warten – Blinzeln"),
    ("STANDBY", "Warten / Leerlauf"),
    ("DRINK_A_KEY", "Trinken (Schlüsselszene)"),
    ("DRINK", "Trinken"),
    ("CHEERS", "Anstoßen"),
    ("SUGGEST", "Schlägt eine Regel vor"),
    ("YES", "Stimmt zu"),
    ("RESULT", "Ergebnis eines Zugs"),
    ("WIN", "Gewinnt"),
    ("PUKE", "Übergibt sich"),
    ("BOW", "Verbeugung"),
    ("SHUFFLE", "Mischt die Gläser"),
    ("PLAYER_", "Spieler-Aktion (Trick/Skill)"),
    ("PRERENDER_TITLE", "Titelbildschirm-Hintergrund"),
    ("PRERENDER_DOOR", "Tür öffnet sich"),
    ("PRERENDER_TOILET", "Treppe zur Toilette"),
    ("PRERENDER_CRIME", "Rückblende"),
    ("EVENT", "Event-Szene"),
    ("logo", "Hersteller-Logo"),
]

GRUPPEN = [
    ("Fam", "Fam – Animationen der Gegnerin", "Greenscreen-Videos, im Spiel wird das Grün ausgestanzt."),
    ("Player", "Spieler – Trick- und Skill-Animationen", ""),
    ("Event", "Zwischensequenzen", ""),
    ("Logo", "Logo", ""),
]


def bedeutung(name):
    for key, text in BEDEUTUNG:
        if key.lower() in name.lower():
            return text
    return ""


def main(root, out):
    movie = os.path.join(root, "Bacchus", "Movie")
    out_dir = os.path.dirname(os.path.abspath(out))
    teile = []
    gesamt = 0
    for ordner, titel, hinweis in GRUPPEN:
        pfad = os.path.join(movie, ordner)
        if not os.path.isdir(pfad):
            continue
        dateien = []
        for dp, _, names in os.walk(pfad):
            dateien += [os.path.join(dp, n) for n in names if n.lower().endswith(".mp4")]
        dateien.sort(key=lambda p: os.path.basename(p))
        karten = []
        for f in dateien:
            name = os.path.basename(f)
            rel_html = os.path.relpath(f, out_dir).replace(os.sep, "/")
            rel_swap = "Bacchus/Movie/" + os.path.relpath(f, movie).replace(os.sep, "/")
            info = mp4_info.info(f)
            dauer = ""
            for teil in info.split():
                if teil.endswith("s") and teil[:-1].replace(".", "").isdigit():
                    dauer = teil
            karten.append(f"""
      <figure class="card">
        <video src="{html.escape(rel_html)}" muted loop playsinline preload="metadata"></video>
        <figcaption>
          <b>{html.escape(name.replace('.mp4', ''))}</b>
          <span class="meaning">{html.escape(bedeutung(name))}</span>
          <span class="meta">{html.escape(dauer)}</span>
          <code title="Pfad für MovieSwap">{html.escape(rel_swap)}</code>
        </figcaption>
      </figure>""")
        gesamt += len(dateien)
        teile.append(f"""
  <section>
    <h2>{html.escape(titel)} <small>({len(dateien)})</small></h2>
    {f'<p class="hint">{html.escape(hinweis)}</p>' if hinweis else ''}
    <div class="grid">{''.join(karten)}
    </div>
  </section>""")

    seite = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>Spielvideos</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{ color-scheme: dark; --bg:#17131a; --card:#241e29; --text:#eee; --muted:#a99db0; --accent:#e0457b; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.45 system-ui, sans-serif; }}
  header {{ padding:24px 20px 8px; }}
  h1 {{ margin:0 0 6px; font-size:24px; }}
  header p {{ margin:4px 0; color:var(--muted); max-width:900px; }}
  section {{ padding:8px 20px 24px; }}
  h2 {{ font-size:18px; border-bottom:1px solid #3a3040; padding-bottom:6px; }}
  h2 small {{ color:var(--muted); font-weight:normal; }}
  .hint {{ color:var(--muted); margin-top:-4px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:14px; }}
  .card {{ margin:0; background:var(--card); border-radius:8px; overflow:hidden; }}
  .card video {{ width:100%; aspect-ratio:16/9; background:#000; display:block; cursor:pointer; }}
  figcaption {{ padding:8px 10px 10px; display:flex; flex-direction:column; gap:2px; }}
  .meaning {{ color:var(--accent); }}
  .meta {{ color:var(--muted); font-size:13px; }}
  code {{ color:var(--muted); font-size:11px; word-break:break-all; }}
</style></head><body>
<header>
  <h1>Spielvideos ({gesamt})</h1>
  <p>Maus über ein Video bewegen = abspielen. Klick = mit Ton im Vollbild.</p>
  <p>Ersetzen: eigenes MP4 unter dem angezeigten Pfad in <code>ue4ss/Mods/MovieSwap/Movies/</code> ablegen
     (H.264, gleiche Auflösung; Fam-Videos mit reinem grünem Hintergrund).</p>
</header>
{''.join(teile)}
<script>
  document.querySelectorAll('video').forEach(v => {{
    v.addEventListener('mouseenter', () => v.play());
    v.addEventListener('mouseleave', () => {{ v.pause(); v.currentTime = 0; }});
    v.addEventListener('click', () => {{ v.muted = false; v.requestFullscreen?.(); v.play(); }});
  }});
</script>
</body></html>
"""
    open(out, "w", encoding="utf-8").write(seite)
    print(f"Übersicht geschrieben: {out} ({gesamt} Videos)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
