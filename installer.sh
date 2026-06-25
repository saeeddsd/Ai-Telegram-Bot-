#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

VENV_DIR="venv"
ENV_FILE=".env"

echo ""
echo "========================================================"
echo "   نصب خودکار ربات تلگرام هوش مصنوعی"
echo "   AI Telegram Bot Installer"
echo "========================================================"
echo ""

# ─── 1. ساخت محیط مجازی ───
echo -e "${CYAN}[1/5] ساخت محیط مجازی ...${NC}"
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[!] محیط مجازی '$VENV_DIR' از قبل وجود دارد.${NC}"
    read -p "    آیا می‌خواهید دوباره ساخته شود؟ (y/N): " remake
    if [ "$remake" = "y" ] || [ "$remake" = "Y" ]; then
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
        echo -e "${GREEN}[+] محیط مجازی ساخته شد.${NC}"
    fi
else
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}[+] محیط مجازی ساخته شد.${NC}"
fi
echo ""

# ─── 2. نصب وابستگی‌ها ───
echo -e "${CYAN}[2/5] نصب وابستگی‌ها ...${NC}"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo -e "${GREEN}[+] وابستگی‌ها نصب شدند.${NC}"
echo ""

# ─── 3. تنظیمات محیطی ───
echo "--------------------------------------------------------"
echo "  تنظیمات فایل .env"
echo "  مقادیر پیش‌فرض را با Enter بپذیرید یا مقدار جدید وارد کنید."
echo "--------------------------------------------------------"
echo ""

ask() {
    local prompt="$1"
    local default="$2"
    local required="$3"
    local label="اختیاری"
    [ "$required" = "true" ] && label="الزامی"

    while true; do
        if [ -n "$default" ]; then
            echo -e "  (${label}) ${prompt} [${default}]:"
        else
            echo -e "  (${label}) ${prompt}:"
        fi
        printf "    > "
        read -r value
        value="${value:-$default}"
        if [ "$required" = "true" ] && [ -z "$value" ]; then
            echo -e "    ${RED}⚠ این فیلد الزامی است.${NC}"
            continue
        fi
        echo "$value"
        return
    done
}

TELEGRAM_TOKEN=$(ask "توکن ربات تلگرام (از BotFather بگیرید)" "" "true")
OPENAI_API_KEY=$(ask "کلید API هوش مصنوعی" "" "true")
OPENAI_BASE_URL=$(ask "آدرس سرور API" "https://api.freemodel.dev/v1" "false")
ADMIN_IDS=$(ask "آیدی عددی ادمین‌ها (با کاما انگلیسی جدا کنید)" "" "true")
PANEL_PASSWORD=$(ask "رمز عبور پنل وب مدیریت" "admin123" "false")
PANEL_PORT=$(ask "پورت پنل وب" "5000" "false")

echo ""
echo "--------------------------------------------------------"
echo "  تنظیمات اختیاری (برای پیش‌فرض Enter بزنید)"
echo "--------------------------------------------------------"
echo ""

MAX_USERS=$(ask "حداکثر تعداد کاربران" "100" "false")
RATE_LIMIT_MESSAGES=$(ask "تعداد پیام مجاز در بازه زمانی" "20" "false")
RATE_LIMIT_SECONDS=$(ask "بازه زمانی محدودیت (ثانیه)" "60" "false")
MAX_MESSAGE_LENGTH=$(ask "حداکثر طول پیام کاربر" "4000" "false")

PANEL_SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9-_' | fold -w 32 | head -n 1)

# ─── 4. ساخت فایل .env ───
echo ""
echo -e "${CYAN}[4/5] ساخت فایل .env ...${NC}"

cat > "$ENV_FILE" << EOF
TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_BASE_URL=${OPENAI_BASE_URL}
ADMIN_IDS=${ADMIN_IDS}
PANEL_PASSWORD=${PANEL_PASSWORD}
PANEL_PORT=${PANEL_PORT}
PANEL_SECRET_KEY=${PANEL_SECRET_KEY}
MAX_USERS=${MAX_USERS}
RATE_LIMIT_MESSAGES=${RATE_LIMIT_MESSAGES}
RATE_LIMIT_SECONDS=${RATE_LIMIT_SECONDS}
MAX_MESSAGE_LENGTH=${MAX_MESSAGE_LENGTH}
EOF

echo -e "${GREEN}[+] فایل '$ENV_FILE' ساخته شد.${NC}"

# ─── 5. ساخت پوشه‌ها ───
echo -e "${CYAN}[5/5] ساخت پوشه‌ها ...${NC}"
mkdir -p data logs
echo -e "${GREEN}[+] پوشه‌های data/ و logs/ ساخته شدند.${NC}"

# ─── پیام نهایی ───
echo ""
echo "========================================================"
echo -e "  ${GREEN}✅ نصب با موفقیت انجام شد!${NC}"
echo "========================================================"
echo ""
echo "  برای اجرای ربات تلگرام:"
echo ""
echo "    source venv/bin/activate"
echo "    python bot.py"
echo ""
echo "  برای اجرای پنل وب مدیریت:"
echo ""
echo "    source venv/bin/activate"
echo "    python web_panel.py"
echo ""
echo "  آدرس پنل وب: http://localhost:5000"
echo "  رمز عبور: مقداری که در PANEL_PASSWORD وارد کردید"
echo ""
echo "========================================================"
echo ""
