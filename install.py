#!/usr/bin/env python3
import os
import sys
import subprocess
import secrets
import string

VENV_DIR = "venv"
ENV_FILE = ".env"
REQ_FILE = "requirements.txt"

REQUIRED_VARS = [
    {
        "key": "TELEGRAM_TOKEN",
        "prompt": "توکن ربات تلگرام (از BotFather بگیرید)",
        "default": "",
        "required": True,
    },
    {
        "key": "OPENAI_API_KEY",
        "prompt": "کلید API هوش مصنوعی",
        "default": "",
        "required": True,
    },
    {
        "key": "OPENAI_BASE_URL",
        "prompt": "آدرس سرور API",
        "default": "https://api.freemodel.dev/v1",
        "required": False,
    },
    {
        "key": "ADMIN_IDS",
        "prompt": "آیدی عددی ادمین‌ها (با کاما انگلیسی جدا کنید، مثال: 123456,789012)",
        "default": "",
        "required": True,
    },
    {
        "key": "PANEL_PASSWORD",
        "prompt": "رمز عبور پنل وب مدیریت",
        "default": "admin123",
        "required": False,
    },
    {
        "key": "PANEL_PORT",
        "prompt": "پورت پنل وب",
        "default": "5000",
        "required": False,
    },
]

OPTIONAL_VARS = [
    {
        "key": "MAX_USERS",
        "prompt": "حداکثر تعداد کاربران",
        "default": "100",
    },
    {
        "key": "RATE_LIMIT_MESSAGES",
        "prompt": "تعداد پیام مجاز در بازه زمانی",
        "default": "20",
    },
    {
        "key": "RATE_LIMIT_SECONDS",
        "prompt": "بازه زمانی محدودیت (ثانیه)",
        "default": "60",
    },
    {
        "key": "MAX_MESSAGE_LENGTH",
        "prompt": "حداکثر طول پیام کاربر",
        "default": "4000",
    },
]


def print_banner():
    print()
    print("=" * 55)
    print("   نصب خودکار ربات تلگرام هوش مصنوعی")
    print("   AI Telegram Bot Installer")
    print("=" * 55)
    print()


def get_python():
    return sys.executable


def create_venv():
    if os.path.isdir(VENV_DIR):
        print(f"[*] محیط مجازی '{VENV_DIR}' از قبل وجود دارد.")
        ans = input("    آیا می‌خواهید دوباره ساخته شود؟ (y/N): ").strip().lower()
        if ans != "y":
            return
        import shutil
        shutil.rmtree(VENV_DIR, ignore_errors=True)

    print(f"[*] در حال ساخت محیط مجازی '{VENV_DIR}' ...")
    subprocess.check_call([get_python(), "-m", "venv", VENV_DIR])
    print("[+] محیط مجازی ساخته شد.\n")


def get_venv_python():
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def get_venv_pip():
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    return os.path.join(VENV_DIR, "bin", "pip")


def install_deps():
    print(f"[*] در حال نصب وابستگی‌ها از {REQ_FILE} ...")
    pip = get_venv_pip()
    subprocess.check_call([pip, "install", "--upgrade", "pip"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call([pip, "install", "-r", REQ_FILE])
    print("[+] وابستگی‌ها نصب شدند.\n")


def generate_secret_key(length=32):
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ask_var(var, is_optional=False):
    default = var["default"]
    required = var["required"] if "required" in var else not is_optional
    label = "اختیاری" if is_optional or not required else "الزامی"

    if default:
        hint = f" [{default}]"
    else:
        hint = ""

    while True:
        print(f"  ({label}) {var['prompt']}{hint}:")
        value = input("    > ").strip()

        if not value and default:
            value = default
        if not value and required:
            print("    ⚠ این فیلد الزامی است. لطفاً مقدار وارد کنید.\n")
            continue
        return value


def collect_env():
    print("-" * 55)
    print("  تنظیمات فایل .env")
    print("  مقادیر پیش‌فرض را با Enter بپذیرید یا مقدار جدید وارد کنید.")
    print("-" * 55)
    print()

    lines = []

    for var in REQUIRED_VARS:
        value = ask_var(var, is_optional=False)
        lines.append(f"{var['key']}={value}")
        print()

    print("-" * 55)
    print("  تنظیمات اختیاری (برای پیش‌فرض Enter بزنید)")
    print("-" * 55)
    print()

    for var in OPTIONAL_VARS:
        value = ask_var(var, is_optional=True)
        lines.append(f"{var['key']}={value}")
        print()

    secret_key = generate_secret_key()
    lines.append(f"PANEL_SECRET_KEY={secret_key}")

    return lines


def write_env(lines):
    content = """# توکن ربات تلگرام (از BotFather دریافت می‌کنید) - الزامی
# TELEGRAM_TOKEN=...

# کلید API هوش مصنوعی - الزامی
# OPENAI_API_KEY=...

# آدرس سرور API
# OPENAI_BASE_URL=...

# آیدی عددی ادمین‌ها (با کاما انگلیسی جدا کنید)
# ADMIN_IDS=...

# تنظیمات پنل وب مدیریت
# PANEL_PASSWORD=...
# PANEL_PORT=...
# PANEL_SECRET_KEY=...

# تنظیمات اختیاری
# MAX_USERS=100
# RATE_LIMIT_MESSAGES=20
# RATE_LIMIT_SECONDS=60
# MAX_MESSAGE_LENGTH=4000

# ===== مقادیر واقعی (توسط نصب‌کننده ساخته شده) =====
"""
    content += "\n".join(lines) + "\n"

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[+] فایل '{ENV_FILE}' ساخته شد.\n")


def create_data_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    print("[+] پوشه‌های data/ و logs/ ساخته شدند.\n")


def print_final(venv_python):
    print("=" * 55)
    print("  ✅ نصب با موفقیت انجام شد!")
    print("=" * 55)
    print()
    print("  برای اجرای ربات تلگرام:")
    print()

    if os.name == "nt":
        print(f"    {VENV_DIR}\\Scripts\\activate")
    else:
        print(f"    source {VENV_DIR}/bin/activate")
    print("    python bot.py")
    print()
    print("  برای اجرای پنل وب مدیریت:")
    print()
    if os.name == "nt":
        print(f"    {VENV_DIR}\\Scripts\\activate")
    else:
        print(f"    source {VENV_DIR}/bin/activate")
    print("    python web_panel.py")
    print()
    print("  آدرس پنل وب: http://localhost:5000")
    print("  رمز عبور: مقداری که در PANEL_PASSWORD وارد کردید")
    print()
    print("  فایل .env را ویرایش کنید تا تنظیمات را تغییر دهید.")
    print("=" * 55)
    print()


def main():
    print_banner()

    venv_python = get_venv_python()

    print("[1/5] ساخت محیط مجازی ...")
    create_venv()

    print("[2/5] نصب وابستگی‌ها ...")
    install_deps()

    print("[3/5] تنظیمات محیطی ...")
    lines = collect_env()

    print("[4/5] ساخت فایل‌ها ...")
    write_env(lines)
    create_data_dirs()

    print("[5/5] تمام!")
    print_final(venv_python)


if __name__ == "__main__":
    main()
