#!/usr/bin/env python3
"""Steel price image — company branding, RTL, Shamsi date."""
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta, timezone
import jdatetime
import arabic_reshaper
from bidi.algorithm import get_display

def fa(text):
    return get_display(arabic_reshaper.reshape(text))

# ── Fonts ─────────────────────────────────────────────────────
FB = '/data/workspace/fonts/Vazirmatn-Bold.ttf'
FR = '/data/workspace/fonts/Vazirmatn.ttf'

f_company = ImageFont.truetype(FB, 30)
f_title   = ImageFont.truetype(FB, 40)
f_date    = ImageFont.truetype(FR, 28)
f_head    = ImageFont.truetype(FB, 22)
f_prod    = ImageFont.truetype(FR, 22)
f_grade   = ImageFont.truetype(FB, 24)
f_size    = ImageFont.truetype(FR, 22)
f_price   = ImageFont.truetype(FB, 30)
f_branch  = ImageFont.truetype(FB, 22)
f_phone   = ImageFont.truetype(FR, 20)
f_foot    = ImageFont.truetype(FR, 18)

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
CYAN    = '#58a6ff'

# ── Date (Shamsi) ─────────────────────────────────────────────
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

# ── Contact info ──────────────────────────────────────────────
contacts = [
    ('شعبه تبریز', ['041-34461257', '041-34479961-4', '09144502358', '09120798972']),
    ('شعبه مرکزی (تهران)', ['021-48814676', '021-48814677']),
]

# ── Layout ────────────────────────────────────────────────────
W = 800
PAD = 30
ROW_H = 55

n_rows = len([r for r in rows if r != 'divider'])
n_divs = len([r for r in rows if r == 'divider'])

# Height: company + title + date + table + contacts + footer
H = (PAD + 50 + 55 + 40 + 20 + 40 + 8 +      # header area
     n_rows * ROW_H + n_divs * 20 +             # table
     20 + 40 + 40 + 10 + 40 + 10 + 30 +        # contacts
     PAD)

img = Image.new('RGB', (W, H), BG)
draw = ImageDraw.Draw(img)
y = PAD

# ── Company name ──────────────────────────────────────────────
company = fa('شرکت فولاد آروین تجارت امین ایرانیان')
cw = draw.textbbox((0,0), company, font=f_company)[2]
draw.text(((W-cw)//2, y), company, fill=CYAN, font=f_company)
y += 50

# ── Title ─────────────────────────────────────────────────────
title = fa('📊 قیمت روزانه میلگرد')
tw = draw.textbbox((0,0), title, font=f_title)[2]
draw.text(((W-tw)//2, y), title, fill=GOLD, font=f_title)
y += 55

# ── Date ──────────────────────────────────────────────────────
dt = fa(f'📅 {day_name}، {jdate}')
dw = draw.textbbox((0,0), dt, font=f_date)[2]
draw.text(((W-dw)//2, y), dt, fill=GRAY, font=f_date)
y += 40

# ── Top line ──────────────────────────────────────────────────
draw.line([(PAD, y), (W-PAD, y)], fill=RED, width=3)
y += 20

# ── Column positions ──────────────────────────────────────────
COL_W = (W - 2*PAD) // 4
c_prod  = PAD
c_grade = PAD + COL_W
c_size  = PAD + COL_W * 2
c_price = PAD + COL_W * 3

# ── Headers ───────────────────────────────────────────────────
for cx, label in [(c_prod, 'محصول'), (c_grade, 'گرید'), (c_size, 'سایز'), (c_price, 'قیمت (تومان)')]:
    draw.text((cx + 10, y), fa(label), fill=GRAY, font=f_head)
y += 40

draw.line([(PAD, y), (W-PAD, y)], fill=LINE, width=1)
y += 5

# ── Data rows ─────────────────────────────────────────────────
ri = 0
for item in rows:
    if item == 'divider':
        draw.line([(PAD+40, y+8), (W-PAD-40, y+8)], fill=RED, width=2)
        y += 20
        continue

    prod, grade, size, price = item
    bg = CARD if ri % 2 == 0 else CARD2
    draw.rounded_rectangle([(PAD-3, y), (W-PAD+3, y+ROW_H-4)], radius=6, fill=bg)
    ty = y + 12

    draw.text((c_prod + 10, ty), fa(prod), fill=WHITE, font=f_prod)
    draw.text((c_grade + 10, ty), fa(grade), fill=GREEN, font=f_grade)
    draw.text((c_size + 10, ty), fa(size), fill=WHITE, font=f_size)

    pw = draw.textbbox((0,0), price, font=f_price)[2]
    px = c_price + COL_W - pw - 10
    draw.text((px, ty - 1), price, fill=GOLD, font=f_price)

    y += ROW_H
    ri += 1

# ── Bottom table line ─────────────────────────────────────────
y += 3
draw.line([(PAD, y), (W-PAD, y)], fill=RED, width=3)
y += 20

# ── Contact info ──────────────────────────────────────────────
for branch, phones in contacts:
    # Branch name centered
    bt = fa(branch)
    bw = draw.textbbox((0,0), bt, font=f_branch)[2]
    draw.text(((W-bw)//2, y), bt, fill=CYAN, font=f_branch)
    y += 35

    # Phones centered
    phone_line = '  |  '.join(phones)
    pw = draw.textbbox((0,0), phone_line, font=f_phone)[2]
    draw.text(((W-pw)//2, y), phone_line, fill=WHITE, font=f_phone)
    y += 35

    # Small divider between branches
    if branch != contacts[-1][0]:
        draw.line([(PAD+100, y+5), (W-PAD-100, y+5)], fill=LINE, width=1)
        y += 15

y += 10

# ── Footer ────────────────────────────────────────────────────
ft = fa('🤖 گزارش خودکار | @IronwarePriceTestChannel')
fw = draw.textbbox((0,0), ft, font=f_foot)[2]
draw.text(((W-fw)//2, y), ft, fill=GRAY, font=f_foot)

# ── Save ──────────────────────────────────────────────────────
OUT = '/data/workspace/price_image.png'
img.save(OUT, 'PNG')
print(f'✅ {OUT} ({W}x{H})')
