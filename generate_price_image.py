#!/usr/bin/env python3
"""Steel price image — tight columns, proper date, no cut-off."""
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta, timezone
import arabic_reshaper
from bidi.algorithm import get_display

def fa(text):
    """Reshape + bidi for correct RTL rendering in PIL."""
    return get_display(arabic_reshaper.reshape(text))

# ── Fonts ─────────────────────────────────────────────────────
FB = '/data/workspace/fonts/Vazirmatn-Bold.ttf'
FR = '/data/workspace/fonts/Vazirmatn.ttf'

f_title = ImageFont.truetype(FB, 44)
f_date  = ImageFont.truetype(FR, 30)
f_head  = ImageFont.truetype(FB, 24)
f_prod  = ImageFont.truetype(FR, 24)
f_grade = ImageFont.truetype(FB, 26)
f_size  = ImageFont.truetype(FR, 24)
f_price = ImageFont.truetype(FB, 32)
f_foot  = ImageFont.truetype(FR, 20)

# ── Colors ────────────────────────────────────────────────────
BG      = '#0d1117'
CARD    = '#161b22'
CARD2   = '#0d1117'
RED     = '#da3633'
GOLD    = '#f0c040'
GREEN   = '#3fb950'
WHITE   = '#e6edf3'
GRAY    = '#8b949e'
LINE    = '#30363d'

# ── Date (Shamsi) ─────────────────────────────────────────────
import jdatetime
tz = timezone(timedelta(hours=3, minutes=30))
now = datetime.now(tz)
day_names = ['دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه','شنبه','یکشنبه']
day_name = day_names[now.weekday()]
shamsi = jdatetime.datetime.fromgregorian(datetime=now)
jdate = shamsi.strftime('%Y/%m/%d')

# ── Data ──────────────────────────────────────────────────────
rows = [
    ('میلگرد آجدار', 'A2', '8',         '776,000'),
    ('میلگرد آجدار', 'A2', '10',        '773,000'),
    ('میلگرد آجدار', 'A3', '12',        '77,300'),
    ('میلگرد آجدار', 'A3', '14 الی 32', '77,000'),
    'divider',
    ('میلگرد آجدار', 'A3', '8',         '77,900'),
    ('میلگرد آجدار', 'A3', '10',        '77,600'),
    ('میلگرد (ساده)','A1', '8',         '80,000'),
]

# ── Layout ────────────────────────────────────────────────────
W = 800
PAD = 30
ROW_H = 60

n_rows = len([r for r in rows if r != 'divider'])
n_divs = len([r for r in rows if r == 'divider'])
H = PAD + 65 + 45 + 20 + 45 + 8 + (n_rows * ROW_H) + (n_divs * 20) + 45 + PAD

img = Image.new('RGB', (W, H), BG)
draw = ImageDraw.Draw(img)
y = PAD

# ── Title ─────────────────────────────────────────────────────
t = fa('📊 قیمت روزانه میلگرد')
tw = draw.textbbox((0,0), t, font=f_title)[2]
draw.text(((W-tw)//2, y), t, fill=GOLD, font=f_title)
y += 65

# ── Date ──────────────────────────────────────────────────────
dt = fa(f'📅 {day_name}، {jdate}')
dw = draw.textbbox((0,0), dt, font=f_date)[2]
draw.text(((W-dw)//2, y), dt, fill=GRAY, font=f_date)
y += 45

# ── Top line ──────────────────────────────────────────────────
draw.line([(PAD, y), (W-PAD, y)], fill=RED, width=3)
y += 20

# ── Column positions (4 columns, tight spacing) ──────────────
# RTL visual order: محصول | گرید | سایز | قیمت
# After bidi, text is visual LTR, so we position left-to-right
COL_W = (W - 2*PAD) // 4  # = 185 px per column

c_prod  = PAD
c_grade = PAD + COL_W
c_size  = PAD + COL_W * 2
c_price = PAD + COL_W * 3

# ── Headers ───────────────────────────────────────────────────
for cx, label in [(c_prod, 'محصول'), (c_grade, 'گرید'), (c_size, 'سایز'), (c_price, 'قیمت (تومان)')]:
    draw.text((cx + 10, y), fa(label), fill=GRAY, font=f_head)
y += 45

draw.line([(PAD, y), (W-PAD, y)], fill=LINE, width=1)
y += 8

# ── Data rows ─────────────────────────────────────────────────
ri = 0
for item in rows:
    if item == 'divider':
        draw.line([(PAD+40, y+8), (W-PAD-40, y+8)], fill=RED, width=2)
        y += 20
        continue

    prod, grade, size, price = item

    # Row bg
    bg = CARD if ri % 2 == 0 else CARD2
    draw.rounded_rectangle([(PAD-3, y), (W-PAD+3, y+ROW_H-4)], radius=6, fill=bg)

    ty = y + 14

    # Product
    draw.text((c_prod + 10, ty), fa(prod), fill=WHITE, font=f_prod)

    # Grade
    draw.text((c_grade + 10, ty), fa(grade), fill=GREEN, font=f_grade)

    # Size
    draw.text((c_size + 10, ty), fa(size), fill=WHITE, font=f_size)

    # Price — right-aligned within its column, ensure no cut-off
    pw = draw.textbbox((0,0), price, font=f_price)[2]
    px = c_price + COL_W - pw - 10  # right-align inside column
    draw.text((px, ty - 1), price, fill=GOLD, font=f_price)

    y += ROW_H
    ri += 1

# ── Bottom line ───────────────────────────────────────────────
y += 3
draw.line([(PAD, y), (W-PAD, y)], fill=RED, width=3)
y += 15

# ── Footer ────────────────────────────────────────────────────
ft = fa('🤖 گزارش خودکار | @IronwarePriceTestChannel')
fw = draw.textbbox((0,0), ft, font=f_foot)[2]
draw.text(((W-fw)//2, y), ft, fill=GRAY, font=f_foot)

# ── Save ──────────────────────────────────────────────────────
OUT = '/data/workspace/price_image.png'
img.save(OUT, 'PNG')
print(f'✅ {OUT} ({W}x{H})')
