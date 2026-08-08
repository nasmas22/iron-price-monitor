---
name: iron-price-monitor
description: "Monitor steel price Telegram channels and generate images."
version: 1.0.0
author: Samimi
---

# Iron Price Monitor

Monitors 13 Iranian steel price Telegram channels for new price posts, generates branded images with company info, and publishes to @IronwarePriceTestChannel.

## Architecture

- **steel_scraper.py** — Scrapes all channels, calculates averages, formats report
- **monitor_channel.py** — Per-channel monitor: detects new posts, generates image, posts
- **generate_price_image.py** — PIL-based image generator with RTL Persian support

## Channels Monitored

| Channel | Format |
|---------|--------|
| @saebsteelco | Text (rial) |
| @zafarSteelbonab | Text (← arrow format) |
| @FSDTABRIZ | Text (Persian numerals) |
| @sfk_steels | Text (dot separator: 72.300) |
| @dorpadtabriz_co | Text (rial) |
| @afasteel | Text (rial) |
| @oxintrading | Text |
| @damirbazar | Photo only |
| @pardissteel1 | Photo only |
| @ArianSteel | Text |
| @Fuladnab | Text |
| @javidsteel_bonab | Photo only |
| @steelradhamedan | Text |

## Working Hours

- **Schedule:** Every 10 minutes, 8am-5pm, Saturday-Thursday
- **Cron:** `*/10 8-16 * * 6,0-4`

## IMPORTANT: Photo-Only Channels

For photo-only channels (damirbazar, pardissteel1, ArianSteel, javidsteel_bonab):
- Use `vision_analyze` to read prices from images
- NEVER skip photo channels
- Extract prices, generate branded image, post with source link

## Usage

```bash
# Check single channel
python3 monitor_channel.py saebsteelco

# Run full aggregator
python3 steel_scraper.py --post

# Generate image only
python3 generate_price_image.py
```

## Dependencies

```
pip3 install requests beautifulsoup4 Pillow jdatetime arabic-reshaper python-bidi
```

## Fonts

Download Vazirmatn to `fonts/` directory:
```bash
curl -sL -o fonts/Vazirmatn.ttf "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Regular.ttf"
curl -sL -o fonts/Vazirmatn-Bold.ttf "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Bold.ttf"
```

## Environment

- Bot token in `~/.hermes/.env` as `TELEGRAM_BOT_TOKEN=...`
- Target channel: `-1004431236647` (@IronwarePriceTestChannel)
