"""Genera docs/demo.mp4 y docs/demo.gif a partir de la salida REAL de una corrida.

Entradas (en docs/fuentes/):
  corrida.txt   salida de `python main.py --demo`
  aprobar.txt   salida de `python main.py --aprobar ...`
  carta.txt     una carta generada (data/cartas/<hilo>/01.txt)
  ../arquitectura.png, resumen.png
Uso: .venv/Scripts/python docs/fuentes/hacer_video.py
"""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).resolve().parent
DOCS = AQUI.parent
W, H, FPS = 1280, 720, 15
FONDO, TARJETA, BORDE = (11, 18, 32), (17, 26, 46), (36, 50, 79)
TEXTO, TENUE, AZUL, MORADO, AMBAR, VERDE = (230, 237, 247), (141, 162, 192), (14, 165, 233), (167, 139, 250), (245, 158, 11), (16, 185, 129)
F = "C:/Windows/Fonts/"
MONO = ImageFont.truetype(F + "consola.ttf", 17)
SANS = ImageFont.truetype(F + "segoeui.ttf", 26)
SANS_B = ImageFont.truetype(F + "segoeuib.ttf", 52)
SANS_M = ImageFont.truetype(F + "segoeuib.ttf", 30)
CHICA = ImageFont.truetype(F + "segoeui.ttf", 20)


def color_linea(l):
    if l.startswith("$"):
        return VERDE
    if "esperan tu aprobación" in l or "REVISAR" in l:
        return AMBAR
    if l.lstrip().startswith("#") and "[" in l:
        return TEXTO
    if "simulada" in l or "enviada" in l:
        return VERDE
    if "Filtro:" in l or "Tokens" in l:
        return AZUL
    if "Hilo" in l:
        return MORADO
    return TENUE


def ventana(titulo):
    im = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 30, W - 40, H - 30), 14, fill=TARJETA, outline=BORDE, width=2)
    for i, c in enumerate([(244, 63, 94), (245, 158, 11), (16, 185, 129)]):
        d.ellipse((62 + i * 24, 48, 76 + i * 24, 62), fill=c)
    d.text((W // 2, 55), titulo, font=CHICA, fill=TENUE, anchor="mm")
    return im, d


def limpiar(l):
    """Consolas no trae el guion no separable (U+2011) que suele usar el LLM."""
    return l.replace("‑", "-").replace("‐", "-")


def recortar(l, n=118):
    l = limpiar(l)
    return l if len(l) <= n else l[: n - 1] + "…"


def escena_terminal(lineas, titulo, frames, cps=40):
    """Escribe el comando letra por letra y luego va soltando las líneas de salida."""
    comando, salida = lineas[0], lineas[1:]
    total = []
    pasos = [comando[:i] for i in range(2, len(comando) + 1, 2)] + [comando] * 6
    for parcial in pasos:
        total.append([parcial + "▌"])
    vis = [comando]
    for l in salida:
        vis = vis + [l]
        rep = 2 if l.strip() else 1
        for _ in range(rep):
            total.append(list(vis))
    total += [list(vis)] * (FPS * 3)
    for estado in total:
        im, d = ventana(titulo)
        visibles = estado[-29:]
        for i, l in enumerate(visibles):
            d.text((66, 86 + i * 20.5), recortar(l), font=MONO, fill=color_linea(l))
        frames.append(im)


def escena_imagen(ruta, titulo, frames, seg=5, desplazar=False):
    base = Image.open(ruta).convert("RGB")
    escala = (W - 80) / base.width
    img = base.resize((W - 80, int(base.height * escala)))
    n = FPS * seg
    for k in range(n):
        im = Image.new("RGB", (W, H), FONDO)
        d = ImageDraw.Draw(im)
        alto_vis = H - 110
        y0 = int((img.height - alto_vis) * k / (n - 1)) if desplazar and img.height > alto_vis else 0
        im.paste(img.crop((0, y0, img.width, y0 + min(alto_vis, img.height))), (40, 90))
        d.text((40, 30), titulo, font=SANS_M, fill=TEXTO)
        frames.append(im)


def escena_carta(texto, frames, seg=7):
    lineas = []
    for l in limpiar(texto).splitlines():
        while len(l) > 112:
            corte = l.rfind(" ", 0, 112)
            lineas.append(l[:corte]); l = l[corte + 1:]
        lineas.append(l)
    for k in range(FPS * seg):
        im, d = ventana("data/cartas/…/03.txt  ·  redactada por el agente redactor, aprobada por el revisor")
        for i, l in enumerate(lineas[:29]):
            col = TENUE if l.startswith("#") else (AZUL if l.startswith("ASUNTO") else TEXTO)
            d.text((66, 86 + i * 20.5), l, font=MONO, fill=col)
        frames.append(im)


def portada(titulo, sub, frames, seg=3, pie=""):
    for k in range(FPS * seg):
        im = Image.new("RGB", (W, H), FONDO)
        d = ImageDraw.Draw(im)
        a = min(1, k / (FPS * 0.6))
        c = tuple(int(FONDO[i] + (TEXTO[i] - FONDO[i]) * a) for i in range(3))
        d.text((W // 2, H // 2 - 40), titulo, font=SANS_B, fill=c, anchor="mm")
        d.text((W // 2, H // 2 + 30), sub, font=SANS, fill=TENUE, anchor="mm")
        if pie:
            d.text((W // 2, H - 80), pie, font=CHICA, fill=AZUL, anchor="mm")
        frames.append(im)


def main():
    leer = lambda n: (AQUI / n).read_text(encoding="utf-8").splitlines()
    frames = []
    portada("Sistema multiagente de empleo", "LangGraph · LLM · humano en el ciclo", frames)
    escena_imagen(DOCS / "arquitectura.png", "Arquitectura", frames, seg=6)
    escena_terminal(["$ python main.py --demo"] + leer("corrida.txt"), "Corrida diaria (demo sin internet)", frames)
    escena_carta((AQUI / "carta.txt").read_text(encoding="utf-8"), frames)
    escena_terminal(["$ python main.py --aprobar 2,3"] + leer("aprobar.txt"), "Reanudar el grafo con tu decisión", frames)
    if (DOCS / "resumen.png").exists():
        escena_imagen(DOCS / "resumen.png", "Resumen diario que llega por correo", frames, seg=6, desplazar=True)
    portada("github.com/CARLYGP", "Agente_Empleo_LangGraph", frames, seg=3)

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    mp4 = DOCS / "demo.mp4"
    p = subprocess.Popen([ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", str(mp4)],
                         stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
    gif = DOCS / "demo.gif"
    subprocess.run([ff, "-y", "-i", str(mp4), "-vf",
                    "fps=8,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
                    str(gif)], stderr=subprocess.DEVNULL, check=True)
    print(f"{len(frames) / FPS:.0f} s | mp4 {mp4.stat().st_size / 1e6:.1f} MB | gif {gif.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    sys.exit(main())
