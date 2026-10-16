# Generează pictograma aplicației (app.ico, mai multe dimensiuni) — design original:
# o parcelă cadastrală (poligon) cu o enclavă, pe fundal întunecat.
import sys
from PIL import Image, ImageDraw

S = 1024
img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([40, 40, S - 40, S - 40], radius=190, fill=(11, 14, 20, 255),
                    outline=(30, 45, 69, 255), width=24)
# grilă discretă
for k in range(1, 6):
    x = 40 + k * (S - 80) / 6
    d.line([(x, 120), (x, S - 120)], fill=(16, 40, 56, 255), width=6)
    d.line([(120, x), (S - 120, x)], fill=(16, 40, 56, 255), width=6)
parcel = [(230, 300), (640, 210), (800, 470), (700, 800), (300, 760), (200, 540)]
d.polygon(parcel, fill=(10, 62, 80, 255))
d.line(parcel + [parcel[0]], fill=(0, 212, 255, 255), width=46, joint='curve')
hole = [(420, 450), (560, 430), (580, 570), (440, 600)]
d.polygon(hole, fill=(11, 14, 20, 255))
d.line(hole + [hole[0]], fill=(0, 255, 157, 255), width=30, joint='curve')
for (x, y) in parcel:
    d.ellipse([x - 42, y - 42, x + 42, y + 42], fill=(255, 255, 255, 255))
    d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(0, 212, 255, 255))

out = sys.argv[1]
sizes = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(out, format='ICO', sizes=sizes)
img.resize((512, 512), Image.LANCZOS).save(out.replace('.ico', '_512.png'))
print('ok', out)
