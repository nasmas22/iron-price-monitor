# 🇮🇷 Iran Steel Price Monitor

Automatic monitoring of iron & steel prices from 13 Iranian Telegram channels, with smart averaging, branded image generation, and automated publishing.

## ✨ Features

- **Real-time Monitoring** — Checks channels every 10 minutes during business hours
- **Smart Price Extraction** — Regex-based extraction with Persian/Arabic numeral support
- **Vision AI Integration** — Uses AI vision to read prices from photo-only channels
- **Branded Image Generation** — Creates professional price cards with company branding
- **Automatic Publishing** — Posts to Telegram channel with source links
- **Duplicate Prevention** — Tracks last processed message per channel
- **Outlier Detection** — Removes prices >20% from median
- **Weighted Averaging** — Calculates accurate average prices per product

## 🔌 Channels Monitored (13)

### Text-Based Channels (8)
| Channel | Description | Format |
|---------|-------------|--------|
| [@saebsteelco](https://t.me/saebsteelco) | فولاد صائب تبریز | Text (rial) |
| [@zafarSteelbonab](https://t.me/zafarSteelbonab) | مجتمع فولاد ظفر بناب | Text (← arrow) |
| [@FSDTABRIZ](https://t.me/FSDTABRIZ) | فولاد سازان دقيقی هشترود | Text (Persian numerals) |
| [@sfk_steels](https://t.me/sfk_steels) | SFK Steels | Text (dot: 72.300) |
| [@dorpadtabriz_co](https://t.me/dorpadtabriz_co) | گروه صنعتی درپاد | Text (rial) |
| [@afasteel](https://t.me/afasteel) | آذر فولاد امین | Text (rial) |
| [@oxintrading](https://t.me/oxintrading) | اوکسین تریدینگ | Text |
| [@steelradhamedan](https://t.me/steelradhamedan) | فولاد راد همدان | Text |

### Photo-Only Channels (4) — Vision Required
| Channel | Description | Method |
|---------|-------------|--------|
| [@damirbazar](https://t.me/damirbazar) | دمیر بازار | AI Vision |
| [@pardissteel1](https://t.me/pardissteel1) | پردیس استیل | AI Vision |
| [@ArianSteel](https://t.me/ArianSteel) | آرین استیل | AI Vision |
| [@javidsteel_bonab](https://t.me/javidsteel_bonab) | جاوید استیل بناب | AI Vision |

### Other Channels (1)
| Channel | Description |
|---------|-------------|
| [@Fuladnab](https://t.me/Fuladnab) | فولاد ناب |

## 🖼️ Branded Image Generation

Each price update is converted to a professional branded image featuring:

- **Company Header** — شرکت فولاد آروین تجارت امین ایرانیان
- **Shamsi Date** — Today's date in Iranian calendar
- **Price Table** — Product, Grade, Size, Price columns
- **Contact Info** — Branch phone numbers
- **Source Link** — Link to original channel post

### Sample Output
```
┌─────────────────────────────────┐
│  شرکت فولاد آروین تجارت امین ایرانیان  │
│        قیمت روزانه میلگرد        │
│     شنبه، 1405/05/17            │
├─────────────────────────────────┤
│ محصول │ گرید │ سایز │ قیمت(تومان) │
├─────────────────────────────────┤
│ میلگرد │  A2  │  8   │   77,600  │
│ میلگرد │  A2  │  10  │   77,300  │
│ میلگرد │  A3  │  12  │   77,300  │
│ میلگرد │  A3  │14 الی32│  77,000  │
├─────────────────────────────────┤
│ ☎️ شعبه تبریز: 041-34461257     │
│ ☎️ شعبه مرکزی تهران: 021-48814676│
└─────────────────────────────────┘
```

## 🚀 Usage

### Manual Monitoring
```bash
# Check single channel
python3 monitor_channel.py saebsteelco

# Run full aggregator
python3 steel_scraper.py --post

# Generate image only
python3 generate_price_image.py
```

### Automated Monitoring (Cron Job)
The system runs automatically via Hermes Agent cron jobs:

- **Schedule:** Every 10 minutes
- **Hours:** 8:00 AM - 5:00 PM
- **Days:** Saturday - Thursday (Iranian business week)
- **Timezone:** Asia/Tehran

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Hermes Agent                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │              Cron Job (*/10 8-16)               │  │
│  └─────────────────────────────────────────────────┘  │
│                         │                               │
│         ┌───────────────┼───────────────┐               │
│         ▼               ▼               ▼               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ Text Channels│ │Photo Channels│ │  AI Vision  │       │
│  │  (Scraper)   │ │  (Scraper)  │ │  (Analyze)  │       │
│  └─────────────┘ └─────────────┘ └─────────────┘       │
│         │               │               │               │
│         └───────────────┼───────────────┘               │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────┐  │
│  │           Price Extraction & Validation          │  │
│  └─────────────────────────────────────────────────┘  │
│                         │                               │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────┐  │
│  │        Image Generation (PIL + RTL Persian)     │  │
│  └─────────────────────────────────────────────────┘  │
│                         │                               │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────┐  │
│  │      Telegram Bot API (Post to Channel)         │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## ⚙️ Configuration

### Environment Variables
Set these in `~/.hermes/.env`:

```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=-1004431236647
```

### Cron Job Settings
- **Timezone:** `Asia/Tehran` in `~/.hermes/config.yaml`
- **Schedule:** `*/10 8-16 * * 6,0-4`

## 📁 Project Structure

```
iron-price-monitor/
├── steel_scraper.py          # Main aggregator script
├── monitor_channel.py        # Per-channel monitor
├── generate_price_image.py   # PIL image generator
├── fonts/                    # Vazirmatn fonts
│   ├── Vazirmatn-Regular.ttf
│   └── Vazirmatn-Bold.ttf
├── .price_monitor_cache.json # Last processed message IDs
├── price_monitor_output.png  # Generated price images
└── docs/
    └── SKILL.md              # Hermes skill documentation
```

## 🛠 Dependencies

```bash
pip3 install requests beautifulsoup4 Pillow jdatetime arabic-reshaper python-bidi
```

## 📜 License

MIT

## 🙏 Credits

Built with [Hermes Agent](https://github.com/nousresearch/hermes-agent) by Nous Research
