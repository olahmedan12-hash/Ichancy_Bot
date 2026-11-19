import os
import re
import sqlite3
from datetime import datetime
import telebot
from telebot.types import (
    BotCommand,
    BotCommandScopeChat,
    MenuButtonCommands,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)

# قراءة الإعدادات من متغيرات البيئة مع قيم افتراضية للاختبار المحلي
BOT_TOKEN = os.getenv("BOT_TOKEN", "9038004780:AAG5HYm4at5yOq8VIVnbB8gaLU0OJE5C9Hk")
DB_PATH = os.getenv("DB_PATH", "bot_data.db")
DEFAULT_CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/ichancyadam")
DEFAULT_CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@ichancyadam")

# تعيين المشرف الجديد والرئيسي الوحيد Ola276 وإلغاء المشرف القديم
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Ola276").lstrip("@").strip()
ENV_ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

# إعدادات طرق الشحن الافتراضية
DEFAULT_SYRIATEL_CODE = os.getenv("SYRIATEL_CODE", "0933380467")
MIN_SYRIATEL_AMOUNT = 200.0

DEFAULT_SHAM_CASH_SYP_CODE = os.getenv(
    "SHAM_CASH_SYP_CODE",
    "658544223c0e72faa9776f6a22cbfeba",
)
MIN_SHAM_CASH_SYP_AMOUNT = 200.0

DEFAULT_SHAM_CASH_USD_CODE = os.getenv(
    "SHAM_CASH_USD_CODE",
    "658544223c0e72faa9776f6a22cbfeba",
)
DEFAULT_SHAM_CASH_USD_RATE_SYP = 142.0

# إعدادات سحب الرصيد من البوت الافتراضية
MIN_WITHDRAW_SYRIATEL = 250.0
MAX_WITHDRAW_SYRIATEL = 5000000.0
MIN_WITHDRAW_SHAM_CASH = 2000.0
DEFAULT_WITHDRAW_COMMISSION_RATE = 0.10
DEFAULT_WITHDRAW_USD_RATE_SYP = 145.0

# إعدادات شحن وسحب رصيد الحساب في المنصة
MIN_ACCOUNT_DEPOSIT = 200.0
MIN_ACCOUNT_WITHDRAW = 200.0

# تعريف الأزرار القابلة لتخصيص الرسائل والصور
CUSTOMIZABLE_BUTTONS: list[tuple[str, str]] = [
    ("btn_ichancy", "⚡ichancy ⚡"),
    ("btn_deposit_bot", "شحن رصيد الى البوت ⬇️"),
    ("btn_withdraw_bot", "سحب رصيد من البوت ⬆️"),
    ("btn_deposit_acc", "شحن رصيد في الحساب 🔽"),
    ("btn_withdraw_acc", "سحب رصيد من الحساب 🔼"),
    ("btn_logs", "السجلات 🗃️"),
    ("btn_support", "التواصل مع الدعم 📩"),
    ("btn_offers", "العروض الحاليه 🎁"),
    ("btn_terms", "الشروط والاحكام 📝"),
    ("btn_lottery", "الياناصيب الاسبوعي💵"),
]
BUTTON_KEY_TO_TITLE = dict(CUSTOMIZABLE_BUTTONS)

# شرط الاسم: 8 أحرف إنجليزية صغيرة على الأقل وأحرف فقط بدون رموز أو أرقام أو مسافات
USERNAME_PATTERN = re.compile(r"^[a-z]{8,}$")
# شرط الأرقام الإنجليزية فقط (صحيحة أو عشرية بنقطة إنجليزية)
ENGLISH_NUMBER_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def get_connection() -> sqlite3.Connection:
    """إنشاء اتصال بقاعدة بيانات SQLite."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """إنشاء الجداول المطلوبة في قاعدة البيانات إذا لم تكن موجودة."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL,
                temp_data TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ichancy_accounts (
                user_id INTEGER PRIMARY KEY,
                acc_username TEXT NOT NULL,
                acc_password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS account_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                acc_username TEXT NOT NULL,
                acc_password TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_deposit_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                amount REAL NOT NULL,
                tx_number TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                destination TEXT NOT NULL,
                amount REAL NOT NULL,
                commission REAL NOT NULL,
                net_amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS account_transfer_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transfer_type TEXT NOT NULL,
                acc_username TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_type TEXT NOT NULL,
                content_text TEXT,
                photo_file_id TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS button_configs (
                button_key TEXT PRIMARY KEY,
                custom_message TEXT,
                photo_file_id TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        if ENV_ADMIN_CHAT_ID.isdigit():
            conn.execute(
                """
                INSERT INTO bot_settings (key, value)
                VALUES ('ola276_chat_id', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (ENV_ADMIN_CHAT_ID,),
            )
        conn.commit()


def set_setting(key: str, value: str):
    """حفظ قيمة إعداد في قاعدة البيانات."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO bot_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        conn.commit()


def get_setting(key: str, default: str | None = None) -> str | None:
    """قراءة قيمة إعداد من قاعدة البيانات."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM bot_settings WHERE key = ?",
            (key,),
        ).fetchone()
        return row["value"] if row else default


def get_channel_username() -> str:
    val = (get_setting("channel_username", DEFAULT_CHANNEL_USERNAME) or DEFAULT_CHANNEL_USERNAME).strip()
    return val if val.startswith("@") else f"@{val}"


def get_channel_url() -> str:
    val = (get_setting("channel_url", DEFAULT_CHANNEL_URL) or DEFAULT_CHANNEL_URL).strip()
    if val.startswith("http://") or val.startswith("https://"):
        return val
    clean_u = val.lstrip("@")
    return f"https://t.me/{clean_u}"


def get_syriatel_code() -> str:
    return (get_setting("syriatel_code", DEFAULT_SYRIATEL_CODE) or DEFAULT_SYRIATEL_CODE).strip()


def get_sham_cash_syp_code() -> str:
    return (get_setting("sham_cash_syp_code", DEFAULT_SHAM_CASH_SYP_CODE) or DEFAULT_SHAM_CASH_SYP_CODE).strip()


def get_sham_cash_usd_code() -> str:
    return (get_setting("sham_cash_usd_code", DEFAULT_SHAM_CASH_USD_CODE) or DEFAULT_SHAM_CASH_USD_CODE).strip()


def get_sham_cash_usd_rate_syp() -> float:
    raw = get_setting("sham_cash_usd_rate_syp")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return DEFAULT_SHAM_CASH_USD_RATE_SYP


def get_withdraw_usd_rate_syp() -> float:
    raw = get_setting("withdraw_usd_rate_syp")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return DEFAULT_WITHDRAW_USD_RATE_SYP


def get_withdraw_commission_rate() -> float:
    raw = get_setting("withdraw_commission_rate")
    if raw:
        try:
            val = float(raw)
            if 0.0 <= val < 1.0:
                return val
        except ValueError:
            pass
    return DEFAULT_WITHDRAW_COMMISSION_RATE


def get_button_config(button_key: str) -> sqlite3.Row | None:
    """جلب إعدادات الرسالة والصورة المخصصة لزر معين."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM button_configs WHERE button_key = ?",
            (button_key,),
        ).fetchone()


def save_button_message(button_key: str, custom_message: str | None):
    """حفظ أو مسح رسالة مخصصة لزر معين."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    existing = get_button_config(button_key)
    photo_id = existing["photo_file_id"] if existing else None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO button_configs (button_key, custom_message, photo_file_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(button_key) DO UPDATE SET
                custom_message = excluded.custom_message,
                updated_at = excluded.updated_at
            """,
            (button_key, custom_message, photo_id, now_str),
        )
        conn.commit()


def save_button_photo(button_key: str, photo_file_id: str | None):
    """حفظ أو حذف صورة مخصصة لزر معين."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    existing = get_button_config(button_key)
    custom_msg = existing["custom_message"] if existing else None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO button_configs (button_key, custom_message, photo_file_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(button_key) DO UPDATE SET
                photo_file_id = excluded.photo_file_id,
                updated_at = excluded.updated_at
            """,
            (button_key, custom_msg, photo_file_id, now_str),
        )
        conn.commit()


def send_custom_button_media_if_any(chat_id: int, button_key: str, default_caption: str | None = None):
    """إرسال صورة الزر المخصصة إذا وُجدت (مع الرسالة المخصصة أو الافتراضية)."""
    cfg = get_button_config(button_key)
    if not cfg:
        return False
    photo_id = cfg["photo_file_id"]
    custom_msg = (cfg["custom_message"] or "").strip() if cfg["custom_message"] else None
    if photo_id:
        caption = custom_msg if custom_msg is not None else (default_caption or "")
        bot.send_photo(chat_id, photo=str(photo_id), caption=caption or None)
        return True
    return False


def get_custom_button_text(button_key: str, default_text: str) -> str:
    """إرجاع الرسالة المخصصة للزر إذا تم ضبطها من لوحة التحكم أو النص الافتراضي."""
    cfg = get_button_config(button_key)
    if cfg and cfg["custom_message"] is not None and str(cfg["custom_message"]).strip() != "":
        return str(cfg["custom_message"])
    return default_text


def get_ola276_chat_id() -> int | None:
    """إرجاع معرف محادثة المشرف الرئيسي Ola276."""
    val = get_setting("ola276_chat_id")
    if val and val.isdigit():
        return int(val)
    return None


def sync_ola276_identity(user):
    """تثبيت معرف المشرف الرئيسي Ola276 عند تواصله مع البوت."""
    if not user:
        return
    uname = (user.username or "").lstrip("@").strip().lower()
    if uname == ADMIN_USERNAME.lower():
        set_setting("ola276_chat_id", str(user.id))


def is_main_admin(user) -> bool:
    """التحقق الحصري من أن المستخدم هو المشرف الرئيسي Ola276."""
    if not user:
        return False
    uname = (user.username or "").lstrip("@").strip().lower()
    if uname and uname == ADMIN_USERNAME.lower():
        set_setting("ola276_chat_id", str(user.id))
        return True
    ola_id = get_ola276_chat_id()
    return ola_id is not None and int(user.id) == ola_id


def set_user_state(user_id: int, state: str | None, temp_data: str | None = None):
    """حفظ أو مسح حالة المحادثة الحالية للمستخدم."""
    with get_connection() as conn:
        if state is None:
            conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        else:
            now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO user_states (user_id, state, temp_data, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    state = excluded.state,
                    temp_data = excluded.temp_data,
                    updated_at = excluded.updated_at
                """,
                (user_id, state, temp_data, now_str),
            )
        conn.commit()


def get_user_state(user_id: int) -> tuple[str | None, str | None]:
    """قراءة حالة المحادثة الحالية للمستخدم."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT state, temp_data FROM user_states WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None, None
        return row["state"], row["temp_data"]


def get_active_ichancy_account(user_id: int) -> sqlite3.Row | None:
    """التحقق ما إذا كان لدى المشترك حساب ichancy مفعل مسبقاً."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM ichancy_accounts WHERE user_id = ?",
            (user_id,),
        ).fetchone()


def save_active_ichancy_account(user_id: int, acc_username: str, acc_password: str):
    """حفظ حساب ichancy المفعل نهائياً للمستخدم."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ichancy_accounts (user_id, acc_username, acc_password, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                acc_username = excluded.acc_username,
                acc_password = excluded.acc_password
            """,
            (user_id, acc_username, acc_password, now_str),
        )
        conn.commit()


def create_account_request(user_id: int, acc_username: str, acc_password: str) -> int:
    """إنشاء طلب إنشاء حساب جديد وإرجاع رقم الطلب."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO account_requests (user_id, acc_username, acc_password, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (user_id, acc_username, acc_password, now_str),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_account_request(req_id: int) -> sqlite3.Row | None:
    """جلب بيانات طلب إنشاء الحساب."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM account_requests WHERE id = ?",
            (req_id,),
        ).fetchone()


def update_request_username(req_id: int, new_username: str):
    """تحديث اسم الحساب داخل طلب معلق."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE account_requests SET acc_username = ? WHERE id = ?",
            (new_username, req_id),
        )
        conn.commit()


def update_request_password(req_id: int, new_password: str):
    """تحديث كلمة المرور داخل طلب معلق."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE account_requests SET acc_password = ? WHERE id = ?",
            (new_password, req_id),
        )
        conn.commit()


def set_request_status(req_id: int, status: str):
    """تحديث حالة الطلب (approved / rejected)."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE account_requests SET status = ? WHERE id = ?",
            (status, req_id),
        )
        conn.commit()


def create_bot_deposit_request(user_id: int, method: str, amount: float, tx_number: str) -> int:
    """إنشاء طلب شحن رصيد إلى البوت وإرجاع رقم الطلب."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO bot_deposit_requests (user_id, method, amount, tx_number, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, method, amount, tx_number, now_str),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_bot_deposit_request(dep_id: int) -> sqlite3.Row | None:
    """جلب بيانات طلب شحن رصيد إلى البوت."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM bot_deposit_requests WHERE id = ?",
            (dep_id,),
        ).fetchone()


def set_bot_deposit_status(dep_id: int, status: str):
    """تحديث حالة طلب شحن البوت."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE bot_deposit_requests SET status = ? WHERE id = ?",
            (status, dep_id),
        )
        conn.commit()


def create_bot_withdraw_request(
    user_id: int,
    method: str,
    destination: str,
    amount: float,
    commission: float,
    net_amount: float,
) -> int:
    """إنشاء طلب سحب رصيد من البوت وإرجاع رقم الطلب."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO bot_withdraw_requests (
                user_id, method, destination, amount, commission, net_amount, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, method, destination, amount, commission, net_amount, now_str),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_bot_withdraw_request(w_id: int) -> sqlite3.Row | None:
    """جلب بيانات طلب سحب رصيد من البوت."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM bot_withdraw_requests WHERE id = ?",
            (w_id,),
        ).fetchone()


def approve_withdraw_and_deduct_balance(w_id: int) -> tuple[str, float]:
    """تنفيذ الموافقة على طلب السحب وخصم المبلغ من رصيد البوت في معاملة واحدة."""
    with get_connection() as conn:
        w_row = conn.execute(
            "SELECT * FROM bot_withdraw_requests WHERE id = ?",
            (w_id,),
        ).fetchone()
        if not w_row:
            return "not_found", 0.0
        if w_row["status"] != "pending":
            user_row = conn.execute(
                "SELECT balance FROM users WHERE user_id = ?",
                (int(w_row["user_id"]),),
            ).fetchone()
            bal = float(user_row["balance"]) if user_row else 0.0
            return "not_pending", bal

        target_user_id = int(w_row["user_id"])
        amount = round(float(w_row["amount"]), 2)
        user_row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        current_balance = float(user_row["balance"]) if user_row else 0.0

        if current_balance < amount:
            return "insufficient_balance", current_balance

        conn.execute(
            """
            UPDATE users
            SET balance = ROUND(balance - ?, 2)
            WHERE user_id = ?
            """,
            (amount, target_user_id),
        )
        conn.execute(
            """
            UPDATE bot_withdraw_requests
            SET status = 'approved'
            WHERE id = ? AND status = 'pending'
            """,
            (w_id,),
        )
        conn.commit()

        updated_row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        new_balance = float(updated_row["balance"]) if updated_row else 0.0
        return "approved", new_balance


def set_bot_withdraw_status(w_id: int, status: str):
    """تحديث حالة طلب سحب البوت."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE bot_withdraw_requests SET status = ? WHERE id = ?",
            (status, w_id),
        )
        conn.commit()


def create_account_transfer_request(
    user_id: int,
    transfer_type: str,
    acc_username: str,
    amount: float,
) -> int:
    """إنشاء طلب شحن أو سحب رصيد في حساب المنصة وإرجاع رقم الطلب."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO account_transfer_requests (
                user_id, transfer_type, acc_username, amount, status, created_at
            )
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, transfer_type, acc_username, amount, now_str),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_account_transfer_request(tr_id: int) -> sqlite3.Row | None:
    """جلب بيانات طلب شحن أو سحب رصيد في حساب المنصة."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM account_transfer_requests WHERE id = ?",
            (tr_id,),
        ).fetchone()


def set_account_transfer_status(tr_id: int, status: str):
    """تحديث حالة طلب شحن أو سحب الحساب."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE account_transfer_requests SET status = ? WHERE id = ?",
            (status, tr_id),
        )
        conn.commit()


def approve_account_deposit_and_deduct_bot_balance(tr_id: int) -> tuple[str, float]:
    """الموافقة على شحن الحساب في المنصة وخصم المبلغ تلقائياً من رصيد البوت."""
    with get_connection() as conn:
        tr_row = conn.execute(
            "SELECT * FROM account_transfer_requests WHERE id = ?",
            (tr_id,),
        ).fetchone()
        if not tr_row:
            return "not_found", 0.0
        if tr_row["status"] != "pending":
            user_row = conn.execute(
                "SELECT balance FROM users WHERE user_id = ?",
                (int(tr_row["user_id"]),),
            ).fetchone()
            bal = float(user_row["balance"]) if user_row else 0.0
            return "not_pending", bal

        target_user_id = int(tr_row["user_id"])
        amount = round(float(tr_row["amount"]), 2)
        user_row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        current_balance = float(user_row["balance"]) if user_row else 0.0

        if current_balance < amount:
            return "insufficient_balance", current_balance

        conn.execute(
            """
            UPDATE users
            SET balance = ROUND(balance - ?, 2)
            WHERE user_id = ?
            """,
            (amount, target_user_id),
        )
        conn.execute(
            """
            UPDATE account_transfer_requests
            SET status = 'approved'
            WHERE id = ? AND status = 'pending'
            """,
            (tr_id,),
        )
        conn.commit()

        updated_row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        new_balance = float(updated_row["balance"]) if updated_row else 0.0
        return "approved", new_balance


def approve_account_withdraw_and_add_bot_balance(tr_id: int) -> tuple[str, float]:
    """الموافقة على سحب الرصيد من الحساب وإضافة المبلغ تلقائياً إلى رصيد البوت."""
    with get_connection() as conn:
        tr_row = conn.execute(
            "SELECT * FROM account_transfer_requests WHERE id = ?",
            (tr_id,),
        ).fetchone()
        if not tr_row:
            return "not_found", 0.0
        if tr_row["status"] != "pending":
            user_row = conn.execute(
                "SELECT balance FROM users WHERE user_id = ?",
                (int(tr_row["user_id"]),),
            ).fetchone()
            bal = float(user_row["balance"]) if user_row else 0.0
            return "not_pending", bal

        target_user_id = int(tr_row["user_id"])
        amount = round(float(tr_row["amount"]), 2)

        conn.execute(
            """
            UPDATE users
            SET balance = ROUND(balance + ?, 2)
            WHERE user_id = ?
            """,
            (amount, target_user_id),
        )
        conn.execute(
            """
            UPDATE account_transfer_requests
            SET status = 'approved'
            WHERE id = ? AND status = 'pending'
            """,
            (tr_id,),
        )
        conn.commit()

        updated_row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (target_user_id,),
        ).fetchone()
        new_balance = float(updated_row["balance"]) if updated_row else 0.0
        return "approved", new_balance


def create_support_ticket(
    user_id: int,
    message_type: str,
    content_text: str | None = None,
    photo_file_id: str | None = None,
) -> int:
    """إنشاء تذكرة دعم جديدة وإرجاع رقمها."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO support_tickets (
                user_id, message_type, content_text, photo_file_id, status, created_at
            )
            VALUES (?, ?, ?, ?, 'open', ?)
            """,
            (user_id, message_type, content_text, photo_file_id, now_str),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_support_ticket(ticket_id: int) -> sqlite3.Row | None:
    """جلب بيانات تذكرة الدعم."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM support_tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()


def mark_support_ticket_replied(ticket_id: int):
    """تحديث حالة تذكرة الدعم إلى تم الرد."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE support_tickets SET status = 'replied' WHERE id = ?",
            (ticket_id,),
        )
        conn.commit()


def get_user_bot_operations_history(user_id: int) -> list[dict]:
    """
    جلب جميع عمليات الشحن إلى البوت وعمليات السحب من البوت للمشترك
    من تاريخ إنشاء حسابه حتى وقت الطلب مرتبة زمنياً من الأحدث إلى الأقدم.
    """
    with get_connection() as conn:
        user_row = conn.execute(
            "SELECT created_at FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        account_created_at = user_row["created_at"] if user_row else None

        if account_created_at:
            dep_rows = conn.execute(
                """
                SELECT id, method, amount, status, created_at
                FROM bot_deposit_requests
                WHERE user_id = ? AND created_at >= ?
                ORDER BY id DESC
                """,
                (user_id, account_created_at),
            ).fetchall()

            wdr_rows = conn.execute(
                """
                SELECT id, method, amount, net_amount, status, created_at
                FROM bot_withdraw_requests
                WHERE user_id = ? AND created_at >= ?
                ORDER BY id DESC
                """,
                (user_id, account_created_at),
            ).fetchall()
        else:
            dep_rows = conn.execute(
                """
                SELECT id, method, amount, status, created_at
                FROM bot_deposit_requests
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()

            wdr_rows = conn.execute(
                """
                SELECT id, method, amount, net_amount, status, created_at
                FROM bot_withdraw_requests
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()

    operations = []
    for r in dep_rows:
        operations.append(
            {
                "kind": "deposit",
                "id": int(r["id"]),
                "method": str(r["method"]),
                "amount": float(r["amount"]),
                "net_amount": None,
                "status": str(r["status"]),
                "created_at": str(r["created_at"]),
            }
        )
    for r in wdr_rows:
        operations.append(
            {
                "kind": "withdraw",
                "id": int(r["id"]),
                "method": str(r["method"]),
                "amount": float(r["amount"]),
                "net_amount": float(r["net_amount"]),
                "status": str(r["status"]),
                "created_at": str(r["created_at"]),
            }
        )

    operations.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    return operations


def is_first_time_user(user_id: int) -> bool:
    """التحقق ما إذا كان المشترك يدخل البوت للمرة الأولى."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row is None


def ensure_user(user) -> float:
    """إضافة المستخدم إذا لم يكن مسجلاً وإرجاع رصيده الحالي."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (user_id, username, first_name, balance, created_at)
            VALUES (?, ?, ?, 0.0, ?)
            """,
            (user.id, user.username, user.first_name, now_str),
        )
        conn.execute(
            """
            UPDATE users
            SET username = ?, first_name = ?
            WHERE user_id = ?
            """,
            (user.username, user.first_name, user.id),
        )
        conn.commit()

        row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (user.id,),
        ).fetchone()
        return float(row["balance"]) if row else 0.0


def get_user_row_by_id(user_id: int) -> sqlite3.Row | None:
    """جلب سجل المستخدم من قاعدة البيانات عبر الآيدي."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()


def find_user_by_query(query: str) -> sqlite3.Row | None:
    """البحث عن مستخدم عبر الآيدي أو المعرف (@username)."""
    q = query.strip().lstrip("@")
    with get_connection() as conn:
        if q.isdigit():
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (int(q),),
            ).fetchone()
            if row:
                return row
        return conn.execute(
            "SELECT * FROM users WHERE LOWER(COALESCE(username, '')) = LOWER(?)",
            (q,),
        ).fetchone()


def get_user_balance(user) -> float:
    """جلب رصيد المستخدم من قاعدة البيانات."""
    return ensure_user(user)


def add_user_balance(user_id: int, amount: float) -> float:
    """إضافة مبلغ إلى رصيد المستخدم في قاعدة البيانات وإرجاع الرصيد الجديد."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET balance = ROUND(balance + ?, 2)
            WHERE user_id = ?
            """,
            (amount, user_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return float(row["balance"]) if row else 0.0


def set_user_balance_exact(user_id: int, new_balance: float) -> float:
    """تعيين رصيد محدد للمشترك وإرجاع الرصيد بعد التعديل."""
    clean_val = round(max(0.0, new_balance), 2)
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET balance = ?
            WHERE user_id = ?
            """,
            (clean_val, user_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return float(row["balance"]) if row else 0.0


def get_bot_stats() -> dict:
    """جلب إحصائيات سريعة للبوت من قاعدة البيانات."""
    with get_connection() as conn:
        users_count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        total_bal = conn.execute("SELECT COALESCE(SUM(balance), 0) AS s FROM users").fetchone()["s"]
        acc_count = conn.execute("SELECT COUNT(*) AS c FROM ichancy_accounts").fetchone()["c"]
        pending_acc = conn.execute("SELECT COUNT(*) AS c FROM account_requests WHERE status='pending'").fetchone()["c"]
        pending_dep = conn.execute("SELECT COUNT(*) AS c FROM bot_deposit_requests WHERE status='pending'").fetchone()["c"]
        pending_wdr = conn.execute("SELECT COUNT(*) AS c FROM bot_withdraw_requests WHERE status='pending'").fetchone()["c"]
        pending_tr = conn.execute("SELECT COUNT(*) AS c FROM account_transfer_requests WHERE status='pending'").fetchone()["c"]
        open_tickets = conn.execute("SELECT COUNT(*) AS c FROM support_tickets WHERE status='open'").fetchone()["c"]
    return {
        "users_count": int(users_count),
        "total_balance": float(total_bal),
        "acc_count": int(acc_count),
        "pending_acc": int(pending_acc),
        "pending_dep": int(pending_dep),
        "pending_wdr": int(pending_wdr),
        "pending_tr": int(pending_tr),
        "open_tickets": int(open_tickets),
    }


def is_user_subscribed(user_id: int) -> bool:
    """التحقق من اشتراك المستخدم في قناة البوت."""
    ch_username = get_channel_username()
    try:
        member = bot.get_chat_member(ch_username, user_id)
        return member.status in {"creator", "administrator", "member"}
    except Exception as exc:
        print(f"Subscription check error for user {user_id}: {exc}")
        return False


def format_amount(amount: float) -> str:
    """تنسيق المبلغ بدون أصفار عشرية زائدة إذا كان عدداً صحيحاً."""
    if float(amount).is_integer():
        return str(int(amount))
    return f"{amount:.2f}"


def force_sub_keyboard() -> InlineKeyboardMarkup:
    """أزرار الاشتراك الإجباري والتأكد من الاشتراك."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("الاشتراك في القناة", url=get_channel_url()),
    )
    markup.row(
        InlineKeyboardButton("التاكد من الاشتراك ✅", callback_data="verify_sub"),
    )
    return markup


def main_features_keyboard() -> InlineKeyboardMarkup:
    """الأزرار العشرة الرئيسية مع تبديل الزر الثاني مكان الثالث والرابع مكان الخامس."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("⚡ichancy ⚡", callback_data="btn_ichancy"),
    )
    markup.row(
        InlineKeyboardButton("شحن رصيد الى البوت ⬇️", callback_data="btn_deposit_bot"),
        InlineKeyboardButton("سحب رصيد من البوت ⬆️", callback_data="btn_withdraw_bot"),
    )
    markup.row(
        InlineKeyboardButton("شحن رصيد في الحساب 🔽", callback_data="btn_deposit_acc"),
        InlineKeyboardButton("سحب رصيد من الحساب 🔼", callback_data="btn_withdraw_acc"),
    )
    remaining_buttons = [
        ("السجلات 🗃️", "btn_logs"),
        ("التواصل مع الدعم 📩", "btn_support"),
        ("العروض الحاليه 🎁", "btn_offers"),
        ("الشروط والاحكام 📝", "btn_terms"),
        ("الياناصيب الاسبوعي💵", "btn_lottery"),
    ]
    for label, cb_data in remaining_buttons:
        markup.row(InlineKeyboardButton(label, callback_data=cb_data))
    return markup


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """القائمة الرئيسية للوحة تحكم المشرف Ola276."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📊 الإحصائيات", callback_data="adm_stats"),
        InlineKeyboardButton("💰 تعديل رصيد مشترك", callback_data="adm_user_bal"),
    )
    markup.row(
        InlineKeyboardButton("✏️ تغيير رسالة زر", callback_data="adm_edit_btn_msg"),
        InlineKeyboardButton("🖼️ صورة لأي زر", callback_data="adm_edit_btn_photo"),
    )
    markup.row(
        InlineKeyboardButton("⚙️ إعدادات القناة والأكواد", callback_data="adm_settings"),
        InlineKeyboardButton("📣 إذاعة جماعية", callback_data="adm_broadcast"),
    )
    markup.row(
        InlineKeyboardButton("القائمه الرئيسيه ♻️", callback_data="back_to_main_menu"),
    )
    return markup


def admin_buttons_picker_keyboard(mode: str) -> InlineKeyboardMarkup:
    """قائمة اختيار أي زر لتعديل رسالته أو صورته (mode: 'msg' أو 'photo')."""
    markup = InlineKeyboardMarkup()
    for btn_key, btn_label in CUSTOMIZABLE_BUTTONS:
        cfg = get_button_config(btn_key)
        has_photo = " 🖼️" if (cfg and cfg["photo_file_id"]) else ""
        has_msg = " ✍️" if (cfg and cfg["custom_message"]) else ""
        markup.row(
            InlineKeyboardButton(
                f"{btn_label}{has_msg}{has_photo}",
                callback_data=f"adm_pick_{mode}:{btn_key}",
            )
        )
    markup.row(
        InlineKeyboardButton("⬅️ رجوع للوحة التحكم", callback_data="adm_open_panel"),
    )
    return markup


def admin_single_button_actions_keyboard(btn_key: str) -> InlineKeyboardMarkup:
    """خيارات التعديل لزر محدد (تغيير الرسالة، حذف الرسالة المخصصة، إضافة/تغيير الصورة، حذف الصورة)."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✍️ كتابة / تغيير رسالة الزر", callback_data=f"adm_set_msg:{btn_key}"),
        InlineKeyboardButton("🗑️ حذف الرسالة المخصصة", callback_data=f"adm_del_msg:{btn_key}"),
    )
    markup.row(
        InlineKeyboardButton("🖼️ إضافة / تغيير صورة الزر", callback_data=f"adm_set_photo:{btn_key}"),
        InlineKeyboardButton("🚫 حذف صورة الزر", callback_data=f"adm_del_photo:{btn_key}"),
    )
    markup.row(
        InlineKeyboardButton("⬅️ رجوع للأزرار", callback_data="adm_edit_btn_msg"),
    )
    return markup


def admin_settings_keyboard() -> InlineKeyboardMarkup:
    """إعدادات القناة وأكواد الشحن والأسعار."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📢 قناة الاشتراك", callback_data="adm_set_channel"),
        InlineKeyboardButton("💱 سعر الصرف والعمولة", callback_data="adm_set_rates"),
    )
    markup.row(
        InlineKeyboardButton("📱 كود سيرياتيل كاش", callback_data="adm_set_code_syr"),
    )
    markup.row(
        InlineKeyboardButton("💵 كود شام كاش سوري", callback_data="adm_set_code_sham_syp"),
        InlineKeyboardButton("💲 كود شام كاش دولار", callback_data="adm_set_code_sham_usd"),
    )
    markup.row(
        InlineKeyboardButton("⬅️ رجوع للوحة التحكم", callback_data="adm_open_panel"),
    )
    return markup


def bot_deposit_methods_keyboard() -> InlineKeyboardMarkup:
    """أزرار طرق الشحن المتاحة إلى البوت."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("سريتيل كاش 🪙", callback_data="dep_method_syriatel"),
    )
    markup.row(
        InlineKeyboardButton("شام كاش سوري 💵", callback_data="dep_method_sham_syp"),
    )
    markup.row(
        InlineKeyboardButton("شام كاش دولار 💲", callback_data="dep_method_sham_usd"),
    )
    markup.row(
        InlineKeyboardButton("بنك بيمو 🏛️", callback_data="dep_method_bemo"),
    )
    markup.row(
        InlineKeyboardButton("القائمه الرئيسيه ♻️", callback_data="back_to_main_menu"),
    )
    return markup


def bot_withdraw_methods_keyboard() -> InlineKeyboardMarkup:
    """أزرار طرق السحب المتاحة من البوت."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("سريتيل كاش 🪙", callback_data="wdr_method_syriatel"),
    )
    markup.row(
        InlineKeyboardButton("شام كاش سوري 💵", callback_data="wdr_method_sham_syp"),
    )
    markup.row(
        InlineKeyboardButton("شام كاش دولار 💲", callback_data="wdr_method_sham_usd"),
    )
    markup.row(
        InlineKeyboardButton("بنك بيمو 🏛️", callback_data="wdr_method_bemo"),
    )
    markup.row(
        InlineKeyboardButton("القائمه الرئيسيه ♻️", callback_data="back_to_main_menu"),
    )
    return markup


def ichancy_menu_keyboard() -> InlineKeyboardMarkup:
    """قائمة قسم ichancy: إنشاء حساب جديد والقائمة الرئيسية."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("أنشاء حساب جديد", callback_data="ichancy_create"),
    )
    markup.row(
        InlineKeyboardButton("القائمه الرئيسيه", callback_data="back_to_main_menu"),
    )
    return markup


def cancel_to_main_keyboard() -> InlineKeyboardMarkup:
    """زر إلغاء والعودة للقائمة الرئيسية."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("إلغاء والعوده للقائمه الرئيسيه ♻️", callback_data="back_to_main_menu"),
    )
    return markup


def support_cancel_keyboard() -> InlineKeyboardMarkup:
    """زر إلغاء لرسالة التواصل مع الدعم."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("إلغاء ❌", callback_data="support_cancel"),
    )
    return markup


def admin_support_reply_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    """زر الرد للمشرف على رسالة الدعم القادمة من المشترك."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("رد 💬", callback_data=f"sup_reply:{ticket_id}"),
    )
    return markup


def admin_request_keyboard(req_id: int) -> InlineKeyboardMarkup:
    """أزرار تحكم المشرف الرئيسي على طلب إنشاء الحساب."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("موافقة ✅", callback_data=f"req_approve:{req_id}"),
        InlineKeyboardButton("رفض ❌", callback_data=f"req_reject:{req_id}"),
    )
    markup.row(
        InlineKeyboardButton("تعديل الاسم ✏️", callback_data=f"req_edit_user:{req_id}"),
        InlineKeyboardButton("تعديل كلمة المرور 🔑", callback_data=f"req_edit_pass:{req_id}"),
    )
    return markup


def admin_deposit_keyboard(dep_id: int) -> InlineKeyboardMarkup:
    """أزرار الموافقة أو الرفض لطلب شحن الرصيد إلى البوت."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("موافقة ✅", callback_data=f"dep_approve:{dep_id}"),
        InlineKeyboardButton("رفض ❌", callback_data=f"dep_reject:{dep_id}"),
    )
    return markup


def admin_withdraw_keyboard(w_id: int) -> InlineKeyboardMarkup:
    """أزرار الموافقة أو الرفض لطلب سحب الرصيد من البوت."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("موافقة ✅", callback_data=f"wdr_approve:{w_id}"),
        InlineKeyboardButton("رفض ❌", callback_data=f"wdr_reject:{w_id}"),
    )
    return markup


def admin_account_transfer_keyboard(tr_id: int) -> InlineKeyboardMarkup:
    """أزرار الموافقة أو الرفض لطلب شحن أو سحب رصيد في الحساب."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("موافقة ✅", callback_data=f"acc_tr_approve:{tr_id}"),
        InlineKeyboardButton("رفض ❌", callback_data=f"acc_tr_reject:{tr_id}"),
    )
    return markup


def send_admin_panel(chat_id: int):
    """إرسال لوحة تحكم المشرف الرئيسي Ola276."""
    stats = get_bot_stats()
    text = (
        f"🛠️ <b>لوحة تحكم المشرف الرئيسي (@{ADMIN_USERNAME})</b>\n\n"
        f"👥 المشتركون: <b>{stats['users_count']}</b> | 🏦 حسابات ichancy: <b>{stats['acc_count']}</b>\n"
        f"💰 مجموع أرصدة البوت: <b>{format_amount(stats['total_balance'])} SYP</b>\n"
        f"⏳ طلبات معلقة: حسابات (<b>{stats['pending_acc']}</b>) | شحن (<b>{stats['pending_dep']}</b>) | سحب (<b>{stats['pending_wdr']}</b>) | تحويلات (<b>{stats['pending_tr']}</b>)\n"
        f"📩 رسائل دعم مفتوحة: <b>{stats['open_tickets']}</b>"
    )
    bot.send_message(chat_id, text, reply_markup=admin_panel_keyboard())


def send_force_sub_message(chat_id: int, is_new_user: bool = False):
    """إرسال رسالة الترحيب للمشترك الجديد أو رسالة الاشتراك الإجباري."""
    text = (
        "مرحبا بك معنا 🌸\n\n"
        "للاستمرار واستخدام البوت، يرجى الاشتراك في قناة البوت أولاً ثم الضغط على "
        "<b>التاكد من الاشتراك ✅</b>:"
        if is_new_user
        else "عذراً، يجب الاشتراك في قناة البوت أولاً للمتابعة.\n"
        "بعد الاشتراك اضغط على <b>التاكد من الاشتراك ✅</b>:"
    )
    bot.send_message(chat_id, text, reply_markup=force_sub_keyboard())


def setup_bottom_menu(chat_id: int, user=None):
    """ضبط زر القائمة في الشريط السفلي: يظهر خيار (لوحة التحكم) للمشرف الرئيسي فقط."""
    commands = [
        BotCommand("start", "أبدء"),
        BotCommand("balance", "رصيدي"),
    ]
    if is_main_admin(user):
        commands.append(BotCommand("admin", "لوحة التحكم"))
    bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id))
    bot.set_chat_menu_button(chat_id=chat_id, menu_button=MenuButtonCommands())


def format_display_username(user) -> str:
    """تنسيق اسم المستخدم لعرضه في رسالة (أبدء)."""
    if user.username:
        return f"@{user.username}"
    return user.first_name or "غير محدد"


def build_start_profile_text(user, balance: float) -> str:
    """بناء رسالة (أبدء) بالصيغة المطلوبة."""
    display_user = format_display_username(user)
    return (
        f"👤اسم المستخدم : {display_user}\n"
        f"🆔: <code>{user.id}</code>\n"
        f"رصيد البوت : <b>{balance:.2f}</b>"
    )


def send_main_menu_message(chat_id: int, user):
    """إرسال القائمة الرئيسية للمشترك."""
    balance = ensure_user(user)
    bot.send_message(
        chat_id,
        build_start_profile_text(user, balance),
        reply_markup=main_features_keyboard(),
    )


def send_support_ticket_to_ola276(ticket_id: int) -> bool:
    """إرسال رسالة الدعم الخاصة بالمشترك مرفقة بمعلوماته الشخصية وزر الرد إلى المشرف Ola276."""
    ticket = get_support_ticket(ticket_id)
    if not ticket:
        return False

    ola_chat_id = get_ola276_chat_id()
    if not ola_chat_id:
        print(f"Pending support ticket #{ticket_id}: waiting for @{ADMIN_USERNAME} to message the bot once.")
        return False

    target_user_id = int(ticket["user_id"])
    user_row = get_user_row_by_id(target_user_id)
    full_name = (user_row["first_name"] if user_row and user_row["first_name"] else "غير محدد")
    uname_display = (
        f"@{user_row['username']}"
        if user_row and user_row["username"]
        else "غير متوفر"
    )
    current_balance = float(user_row["balance"]) if user_row else 0.0

    header_info = (
        f"📩 <b>رسالة جديدة من التواصل مع الدعم (#{ticket_id})</b>\n\n"
        f"👤 الاسم: <b>{full_name}</b>\n"
        f"🔗 المعرف: {uname_display}\n"
        f"🆔 الآيدي: <code>{target_user_id}</code>\n"
        f"💰 رصيد البوت: <b>{format_amount(current_balance)} SYP</b>"
    )

    if ticket["message_type"] == "photo" and ticket["photo_file_id"]:
        caption = header_info
        if ticket["content_text"]:
            caption += f"\n\n📝 <b>الوصف / الرسالة:</b>\n{ticket['content_text']}"
        bot.send_photo(
            ola_chat_id,
            photo=str(ticket["photo_file_id"]),
            caption=caption,
            reply_markup=admin_support_reply_keyboard(ticket_id),
        )
    else:
        body = f"{header_info}\n\n💬 <b>الرسالة:</b>\n{ticket['content_text'] or ''}"
        bot.send_message(
            ola_chat_id,
            body,
            reply_markup=admin_support_reply_keyboard(ticket_id),
        )
    return True


def build_admin_request_text(req_row: sqlite3.Row) -> str:
    """بناء رسالة طلب إنشاء الحساب للمشرف الرئيسي Ola276."""
    status_ar = {
        "pending": "قيد المراجعة",
        "approved": "تمت الموافقة",
        "rejected": "مرفوض",
    }.get(req_row["status"], req_row["status"])

    return (
        f"📥 <b>طلب إنشاء حساب ichancy جديد (#{req_row['id']})</b>\n"
        f"المشرف الرئيسي: @{ADMIN_USERNAME}\n"
        f"الحالة: <b>{status_ar}</b>\n\n"
        f"🆔 آيدي المشترك: <code>{req_row['user_id']}</code>\n"
        f"👤 اسم الحساب: <code>{req_row['acc_username']}</code>\n"
        f"🔑 كلمة المرور: <code>{req_row['acc_password']}</code>"
    )


def send_request_to_ola276(req_id: int) -> bool:
    """إرسال طلب إنشاء الحساب إلى المشرف الرئيسي Ola276 فقط."""
    req_row = get_account_request(req_id)
    if not req_row:
        return False

    ola_chat_id = get_ola276_chat_id()
    if not ola_chat_id:
        print(f"Pending account request #{req_id}: waiting for @{ADMIN_USERNAME} to message the bot once.")
        return False

    bot.send_message(
        ola_chat_id,
        build_admin_request_text(req_row),
        reply_markup=admin_request_keyboard(req_id),
    )
    return True


def send_deposit_request_to_ola276(dep_id: int) -> bool:
    """إرسال طلب شحن الرصيد إلى المشرف الرئيسي Ola276."""
    dep_row = get_bot_deposit_request(dep_id)
    if not dep_row:
        return False

    ola_chat_id = get_ola276_chat_id()
    if not ola_chat_id:
        print(f"Pending deposit request #{dep_id}: waiting for @{ADMIN_USERNAME} to message the bot once.")
        return False

    user_row = get_user_row_by_id(int(dep_row["user_id"]))
    uname_display = f"@{user_row['username']}" if user_row and user_row["username"] else (
        user_row["first_name"] if user_row and user_row["first_name"] else "غير محدد"
    )
    current_balance = float(user_row["balance"]) if user_row else 0.0
    amount = float(dep_row["amount"])
    method = str(dep_row["method"])
    usd_rate = get_sham_cash_usd_rate_syp()

    status_ar = {
        "pending": "قيد المراجعة",
        "approved": "تمت الموافقة",
        "rejected": "مرفوض",
    }.get(dep_row["status"], dep_row["status"])

    if method == "شام كاش دولار 💲":
        syp_value = round(amount * usd_rate, 2)
        amount_line = (
            f"💵 المبلغ المراد شحنه: <b>{format_amount(amount)} USD</b> "
            f"(ما يعادل <b>{format_amount(syp_value)} SYP</b>)"
        )
    else:
        amount_line = f"💵 المبلغ المراد شحنه: <b>{format_amount(amount)} SYP</b>"

    text = (
        f"💳 <b>طلب شحن رصيد إلى البوت (#{dep_row['id']})</b>\n"
        f"الحالة: <b>{status_ar}</b>\n\n"
        f"👤 اسم المشترك: {uname_display}\n"
        f"🆔 آيدي المشترك: <code>{dep_row['user_id']}</code>\n"
        f"💰 رصيد البوت الأساسي: <b>{format_amount(current_balance)} SYP</b>\n"
        f"{amount_line}\n"
        f"🧾 رقم العملية: <code>{dep_row['tx_number']}</code>\n"
        f"📱 طريقة الشحن: {method}"
    )

    bot.send_message(
        ola_chat_id,
        text,
        reply_markup=admin_deposit_keyboard(dep_id),
    )
    return True


def send_withdraw_request_to_ola276(w_id: int) -> bool:
    """إرسال طلب سحب الرصيد من البوت إلى المشرف الرئيسي Ola276."""
    w_row = get_bot_withdraw_request(w_id)
    if not w_row:
        return False

    ola_chat_id = get_ola276_chat_id()
    if not ola_chat_id:
        print(f"Pending withdraw request #{w_id}: waiting for @{ADMIN_USERNAME} to message the bot once.")
        return False

    user_row = get_user_row_by_id(int(w_row["user_id"]))
    uname_display = f"@{user_row['username']}" if user_row and user_row["username"] else (
        user_row["first_name"] if user_row and user_row["first_name"] else "غير محدد"
    )
    current_balance = float(user_row["balance"]) if user_row else 0.0
    method = str(w_row["method"])
    amount = float(w_row["amount"])
    commission = float(w_row["commission"])
    net_amount = float(w_row["net_amount"])
    wdr_usd_rate = get_withdraw_usd_rate_syp()
    comm_pct = int(round(get_withdraw_commission_rate() * 100))

    status_ar = {
        "pending": "قيد المراجعة",
        "approved": "تمت الموافقة",
        "rejected": "مرفوض",
    }.get(w_row["status"], w_row["status"])

    if method == "شام كاش دولار 💲":
        net_line = (
            f"✅ صافي المبلغ بعد خصم العمولة: <b>{format_amount(net_amount)} USD</b> "
            f"(سعر الصرف: {format_amount(wdr_usd_rate)} SYP = 1 USD)"
        )
    else:
        net_line = f"✅ صافي المبلغ بعد خصم العمولة: <b>{format_amount(net_amount)} SYP</b>"

    text = (
        f"📤 <b>طلب سحب رصيد من البوت (#{w_row['id']})</b>\n"
        f"الحالة: <b>{status_ar}</b>\n\n"
        f"👤 اسم المشترك: {uname_display}\n"
        f"🆔 آيدي المشترك: <code>{w_row['user_id']}</code>\n"
        f"💰 رصيد البوت الحالي: <b>{format_amount(current_balance)} SYP</b>\n"
        f"📱 طريقة السحب: {method}\n"
        f"🎯 الرقم / الكود المرسل إليه: <code>{w_row['destination']}</code>\n"
        f"💵 المبلغ المسحوب كامل: <b>{format_amount(amount)} SYP</b>\n"
        f"📉 عمولة {comm_pct}%: <b>{format_amount(commission)} SYP</b>\n"
        f"{net_line}"
    )

    bot.send_message(
        ola_chat_id,
        text,
        reply_markup=admin_withdraw_keyboard(w_id),
    )
    return True


def send_account_transfer_request_to_ola276(tr_id: int) -> bool:
    """إرسال طلب شحن أو سحب رصيد في الحساب إلى المشرف الرئيسي Ola276."""
    tr_row = get_account_transfer_request(tr_id)
    if not tr_row:
        return False

    ola_chat_id = get_ola276_chat_id()
    if not ola_chat_id:
        print(f"Pending account transfer request #{tr_id}: waiting for @{ADMIN_USERNAME} to message the bot once.")
        return False

    user_row = get_user_row_by_id(int(tr_row["user_id"]))
    uname_display = f"@{user_row['username']}" if user_row and user_row["username"] else (
        user_row["first_name"] if user_row and user_row["first_name"] else "غير محدد"
    )
    current_balance = float(user_row["balance"]) if user_row else 0.0
    transfer_type = str(tr_row["transfer_type"])
    amount = float(tr_row["amount"])

    status_ar = {
        "pending": "قيد المراجعة",
        "approved": "تمت الموافقة",
        "rejected": "مرفوض",
    }.get(tr_row["status"], tr_row["status"])

    if transfer_type == "deposit_acc":
        text = (
            f"🔽 <b>طلب شحن رصيد في الحساب من رصيد البوت (#{tr_row['id']})</b>\n"
            f"الحالة: <b>{status_ar}</b>\n\n"
            f"👤 اسم المشترك: {uname_display}\n"
            f"🆔 آيدي المشترك: <code>{tr_row['user_id']}</code>\n"
            f"🏦 حساب ichancy: <code>{tr_row['acc_username']}</code>\n"
            f"💰 رصيد البوت الحالي: <b>{format_amount(current_balance)} SYP</b>\n"
            f"💵 المبلغ المراد شحنه في الحساب: <b>{format_amount(amount)} SYP</b>"
        )
    else:
        text = (
            f"🔼 <b>طلب سحب رصيد من الحساب إلى رصيد البوت (#{tr_row['id']})</b>\n"
            f"الحالة: <b>{status_ar}</b>\n\n"
            f"👤 اسم المشترك: {uname_display}\n"
            f"🆔 آيدي المشترك: <code>{tr_row['user_id']}</code>\n"
            f"🏦 حساب ichancy: <code>{tr_row['acc_username']}</code>\n"
            f"💰 رصيد البوت الحالي: <b>{format_amount(current_balance)} SYP</b>\n"
            f"💵 المبلغ المراد سحبه من الحساب: <b>{format_amount(amount)} SYP</b>"
        )

    bot.send_message(
        ola_chat_id,
        text,
        reply_markup=admin_account_transfer_keyboard(tr_id),
    )
    return True


def flush_pending_requests_to_ola276():
    """عند تفاعل Ola276، إرسال أي طلبات معلقة إليه."""
    ola_chat_id = get_ola276_chat_id()
    if not ola_chat_id:
        return
    with get_connection() as conn:
        pending_acc = conn.execute(
            "SELECT id FROM account_requests WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
        pending_dep = conn.execute(
            "SELECT id FROM bot_deposit_requests WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
        pending_wdr = conn.execute(
            "SELECT id FROM bot_withdraw_requests WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
        pending_tr = conn.execute(
            "SELECT id FROM account_transfer_requests WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()

    for row in pending_acc:
        try:
            send_request_to_ola276(int(row["id"]))
        except Exception as exc:
            print(f"Failed sending pending account request #{row['id']}: {exc}")

    for row in pending_dep:
        try:
            send_deposit_request_to_ola276(int(row["id"]))
        except Exception as exc:
            print(f"Failed sending pending deposit request #{row['id']}: {exc}")

    for row in pending_wdr:
        try:
            send_withdraw_request_to_ola276(int(row["id"]))
        except Exception as exc:
            print(f"Failed sending pending withdraw request #{row['id']}: {exc}")

    for row in pending_tr:
        try:
            send_account_transfer_request_to_ola276(int(row["id"]))
        except Exception as exc:
            print(f"Failed sending pending account transfer request #{row['id']}: {exc}")


def send_start_response(chat_id: int, user, remove_reply_kb: bool = False):
    """تنفيذ منطق (أبدء) مع فحص الدخول الأول والاشتراك الإجباري."""
    sync_ola276_identity(user)
    first_time = is_first_time_user(user.id)
    balance = ensure_user(user)
    setup_bottom_menu(chat_id, user=user)

    if is_main_admin(user):
        flush_pending_requests_to_ola276()

    if remove_reply_kb:
        menu_hint = "أبدء / رصيدي / لوحة التحكم" if is_main_admin(user) else "أبدء / رصيدي"
        bot.send_message(
            chat_id,
            f"تم تفعيل قائمة الشريط السفلي ({menu_hint}).",
            reply_markup=ReplyKeyboardRemove(),
        )

    if first_time:
        send_force_sub_message(chat_id, is_new_user=True)
        return

    if not is_user_subscribed(user.id):
        send_force_sub_message(chat_id, is_new_user=False)
        return

    set_user_state(user.id, None, None)
    bot.send_message(
        chat_id,
        build_start_profile_text(user, balance),
        reply_markup=main_features_keyboard(),
    )


def send_balance_response(chat_id: int, user):
    """تنفيذ منطق (رصيدي) بعد التحقق من الاشتراك."""
    sync_ola276_identity(user)
    first_time = is_first_time_user(user.id)
    balance = get_user_balance(user)
    setup_bottom_menu(chat_id, user=user)

    if is_main_admin(user):
        flush_pending_requests_to_ola276()

    if first_time:
        send_force_sub_message(chat_id, is_new_user=True)
        return

    if not is_user_subscribed(user.id):
        send_force_sub_message(chat_id, is_new_user=False)
        return

    bot.send_message(
        chat_id,
        f"💰 رصيدك الحالي في البوت: <b>{balance:.2f}</b>",
    )


@bot.message_handler(commands=["start"])
def handle_start(message):
    """معالجة خيار أبدء (/start)."""
    send_start_response(message.chat.id, message.from_user, remove_reply_kb=True)


@bot.message_handler(commands=["balance"])
def handle_balance_command(message):
    """معالجة خيار رصيدي (/balance)."""
    send_balance_response(message.chat.id, message.from_user)


@bot.message_handler(commands=["admin", "panel"])
def handle_admin_command(message):
    """فتح لوحة تحكم المشرف الرئيسي Ola276."""
    user = message.from_user
    sync_ola276_identity(user)
    setup_bottom_menu(message.chat.id, user=user)
    if not is_main_admin(user):
        bot.send_message(message.chat.id, "هذه اللوحة مخصصة للمشرف الرئيسي فقط.")
        return
    set_user_state(user.id, None, None)
    send_admin_panel(message.chat.id)


# ==================== كولباكات لوحة تحكم المشرف ====================

@bot.callback_query_handler(func=lambda call: call.data == "adm_open_panel")
def handle_adm_open_panel(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    setup_bottom_menu(call.message.chat.id, user=call.from_user)
    set_user_state(call.from_user.id, None, None)
    bot.answer_callback_query(call.id, "لوحة التحكم")
    send_admin_panel(call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data == "adm_stats")
def handle_adm_stats(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    stats = get_bot_stats()
    bot.answer_callback_query(call.id, "الإحصائيات")
    bot.send_message(
        call.message.chat.id,
        f"📊 <b>إحصائيات البوت التفصيلية</b>\n\n"
        f"👥 إجمالي المشتركين: <b>{stats['users_count']}</b>\n"
        f"🏦 حسابات ichancy المفعلة: <b>{stats['acc_count']}</b>\n"
        f"💰 مجموع أرصدة المشتركين في البوت: <b>{format_amount(stats['total_balance'])} SYP</b>\n"
        f"📥 طلبات إنشاء حساب معلقة: <b>{stats['pending_acc']}</b>\n"
        f"⬇️ طلبات شحن للبوت معلقة: <b>{stats['pending_dep']}</b>\n"
        f"⬆️ طلبات سحب من البوت معلقة: <b>{stats['pending_wdr']}</b>\n"
        f"🔄 طلبات شحن/سحب حساب معلقة: <b>{stats['pending_tr']}</b>\n"
        f"📩 رسائل دعم مفتوحة: <b>{stats['open_tickets']}</b>",
        reply_markup=admin_panel_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "adm_user_bal")
def handle_adm_user_bal(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    set_user_state(call.from_user.id, "adm_waiting_user_query", None)
    bot.answer_callback_query(call.id, "بحث عن مشترك")
    bot.send_message(
        call.message.chat.id,
        "🔍 أرسل <b>آيدي المشترك</b> أو <b>معرفه (@username)</b> لعرض بياناته وتعديل رصيده:",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_bal_op:"))
def handle_adm_bal_op(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    _, op_type, target_id_str = call.data.split(":", 2)
    target_id = int(target_id_str)
    user_row = get_user_row_by_id(target_id)
    if not user_row:
        bot.answer_callback_query(call.id, "المشترك غير موجود.", show_alert=True)
        return

    set_user_state(call.from_user.id, f"adm_bal_amount_{op_type}", str(target_id))
    op_ar = {"add": "إضافة مبلغ إلى رصيد", "sub": "خصم مبلغ من رصيد", "set": "تعيين رصيد جديد لـ"}.get(op_type, "تعديل")
    bot.answer_callback_query(call.id, "أدخل المبلغ")
    bot.send_message(
        call.message.chat.id,
        f"💵 أرسل المبلغ بالأرقام الإنجليزية لـ ({op_ar}) المشترك <code>{target_id}</code> (رصيده الحالي: <b>{format_amount(float(user_row['balance']))} SYP</b>):",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data in {"adm_edit_btn_msg", "adm_edit_btn_photo"})
def handle_adm_btn_picker(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    mode = "msg" if call.data == "adm_edit_btn_msg" else "photo"
    title = "اختر الزر لتعديل رسالته ✍️:" if mode == "msg" else "اختر الزر لإضافة/تعديل صورته 🖼️:"
    bot.answer_callback_query(call.id, "اختر الزر")
    bot.send_message(
        call.message.chat.id,
        title,
        reply_markup=admin_buttons_picker_keyboard(mode),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_pick_"))
def handle_adm_pick_button(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    prefix, btn_key = call.data.split(":", 1)
    mode = prefix.replace("adm_pick_", "")
    btn_label = BUTTON_KEY_TO_TITLE.get(btn_key, btn_key)
    cfg = get_button_config(btn_key)
    cur_msg = cfg["custom_message"] if (cfg and cfg["custom_message"]) else "(الرسالة الافتراضية)"
    cur_photo = "موجودة ✅" if (cfg and cfg["photo_file_id"]) else "غير مضافة ❌"

    if mode == "msg":
        set_user_state(call.from_user.id, "adm_waiting_btn_msg", btn_key)
        bot.answer_callback_query(call.id, "اكتب الرسالة الجديدة")
        bot.send_message(
            call.message.chat.id,
            f"✍️ <b>تعديل رسالة الزر:</b> {btn_label}\n"
            f"الرسالة الحالية: {cur_msg}\n\n"
            "أرسل نص الرسالة الجديد الآن:",
            reply_markup=admin_single_button_actions_keyboard(btn_key),
        )
    else:
        set_user_state(call.from_user.id, "adm_waiting_btn_photo", btn_key)
        bot.answer_callback_query(call.id, "أرسل الصورة")
        bot.send_message(
            call.message.chat.id,
            f"🖼️ <b>إضافة / تغيير صورة الزر:</b> {btn_label}\n"
            f"حالة الصورة الحالية: <b>{cur_photo}</b>\n\n"
            "أرسل الصورة الآن (يمكن إرفاق وصف معها أو إرسالها كصورة فقط):",
            reply_markup=admin_single_button_actions_keyboard(btn_key),
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_set_msg:"))
def handle_adm_set_msg_btn(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    _, btn_key = call.data.split(":", 1)
    set_user_state(call.from_user.id, "adm_waiting_btn_msg", btn_key)
    bot.answer_callback_query(call.id, "أرسل نص الرسالة")
    bot.send_message(
        call.message.chat.id,
        f"✍️ أرسل النص الجديد للزر <b>{BUTTON_KEY_TO_TITLE.get(btn_key, btn_key)}</b>:",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_del_msg:"))
def handle_adm_del_msg_btn(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    _, btn_key = call.data.split(":", 1)
    save_button_message(btn_key, None)
    set_user_state(call.from_user.id, None, None)
    bot.answer_callback_query(call.id, "تم حذف الرسالة المخصصة ✅")
    bot.send_message(
        call.message.chat.id,
        f"✅ تم حذف الرسالة المخصصة للزر <b>{BUTTON_KEY_TO_TITLE.get(btn_key, btn_key)}</b> والعودة للرسالة الافتراضية.",
        reply_markup=admin_single_button_actions_keyboard(btn_key),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_set_photo:"))
def handle_adm_set_photo_btn(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    _, btn_key = call.data.split(":", 1)
    set_user_state(call.from_user.id, "adm_waiting_btn_photo", btn_key)
    bot.answer_callback_query(call.id, "أرسل الصورة")
    bot.send_message(
        call.message.chat.id,
        f"🖼️ أرسل الصورة المراد إرفاقها مع الزر <b>{BUTTON_KEY_TO_TITLE.get(btn_key, btn_key)}</b>:",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_del_photo:"))
def handle_adm_del_photo_btn(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    _, btn_key = call.data.split(":", 1)
    save_button_photo(btn_key, None)
    set_user_state(call.from_user.id, None, None)
    bot.answer_callback_query(call.id, "تم حذف صورة الزر ✅")
    bot.send_message(
        call.message.chat.id,
        f"✅ تم حذف الصورة المرفقة مع الزر <b>{BUTTON_KEY_TO_TITLE.get(btn_key, btn_key)}</b>.",
        reply_markup=admin_single_button_actions_keyboard(btn_key),
    )


@bot.callback_query_handler(func=lambda call: call.data == "adm_settings")
def handle_adm_settings(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return
    bot.answer_callback_query(call.id, "الإعدادات")
    bot.send_message(
        call.message.chat.id,
        "⚙️ <b>إعدادات البوت الحالية</b>\n\n"
        f"📢 القناة: <code>{get_channel_username()}</code> ({get_channel_url()})\n"
        f"📱 كود سيرياتيل: <code>{get_syriatel_code()}</code>\n"
        f"💵 كود شام كاش سوري: <code>{get_sham_cash_syp_code()}</code>\n"
        f"💲 كود شام كاش دولار: <code>{get_sham_cash_usd_code()}</code>\n"
        f"💱 سعر صرف الشحن USD: <b>{format_amount(get_sham_cash_usd_rate_syp())} SYP</b>\n"
        f"💱 سعر صرف السحب USD: <b>{format_amount(get_withdraw_usd_rate_syp())} SYP</b>\n"
        f"📉 عمولة السحب: <b>{int(round(get_withdraw_commission_rate() * 100))}%</b>",
        reply_markup=admin_settings_keyboard(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data in {
        "adm_set_channel",
        "adm_set_rates",
        "adm_set_code_syr",
        "adm_set_code_sham_syp",
        "adm_set_code_sham_usd",
        "adm_broadcast",
    }
)
def handle_adm_setting_prompts(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return

    prompts = {
        "adm_set_channel": (
            "adm_waiting_channel",
            "📢 أرسل معرف القناة الجديد (مثال: <code>@ichancyadam</code>):",
        ),
        "adm_set_rates": (
            "adm_waiting_rates",
            "💱 أرسل القيم الثلاث مفصولة بمسافة أو سطر:\n"
            "<code>سعر_صرف_الشحن_USD سعر_صرف_السحب_USD نسبة_العمولة_بالمئة</code>\n"
            "مثال: <code>142 145 10</code>",
        ),
        "adm_set_code_syr": (
            "adm_waiting_code_syr",
            "📱 أرسل كود / رقم سيرياتيل كاش الجديد:",
        ),
        "adm_set_code_sham_syp": (
            "adm_waiting_code_sham_syp",
            "💵 أرسل كود شام كاش السوري الجديد:",
        ),
        "adm_set_code_sham_usd": (
            "adm_waiting_code_sham_usd",
            "💲 أرسل كود شام كاش الدولار الجديد:",
        ),
        "adm_broadcast": (
            "adm_waiting_broadcast",
            "📣 أرسل نص الرسالة الجماعية لإرسالها إلى جميع المشتركين:",
        ),
    }
    next_state, prompt_msg = prompts[call.data]
    set_user_state(call.from_user.id, next_state, None)
    bot.answer_callback_query(call.id, "أدخل القيمة")
    bot.send_message(call.message.chat.id, prompt_msg, reply_markup=cancel_to_main_keyboard())


# ==================== بقية الكولباكات والأقسام ====================

@bot.callback_query_handler(func=lambda call: call.data == "verify_sub")
def handle_verify_subscription(call):
    """التحقق من الاشتراك دون إرسال أي رسالة إضافية للمشترك بعد التأكيد."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    ensure_user(user)
    setup_bottom_menu(chat_id, user=user)

    if is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "تم التحقق من اشتراكك بنجاح ✅")
        try:
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        except Exception:
            pass
    else:
        bot.answer_callback_query(
            call.id,
            "لم يتم العثور على اشتراكك في القناة بعد.",
            show_alert=True,
        )


@bot.callback_query_handler(func=lambda call: call.data == "back_to_main_menu")
def handle_back_to_main_menu(call):
    """إلغاء أي حالة حالية والعودة إلى القائمة الرئيسية."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)
    set_user_state(user.id, None, None)
    bot.answer_callback_query(call.id, "القائمة الرئيسية")
    send_main_menu_message(chat_id, user)


@bot.callback_query_handler(func=lambda call: call.data == "support_cancel")
def handle_support_cancel(call):
    """إلغاء وضع التواصل مع الدعم والعودة للمشترك."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    set_user_state(user.id, None, None)
    bot.answer_callback_query(call.id, "تم الإلغاء ❌")
    try:
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
    except Exception:
        pass
    bot.send_message(chat_id, "تم إلغاء التواصل مع الدعم ❌")


@bot.callback_query_handler(func=lambda call: call.data == "btn_logs")
def handle_logs_button(call):
    """عرض جميع عمليات الشحن إلى البوت والسحب من البوت منذ تاريخ إنشاء الحساب حتى وقت الطلب."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return

    ensure_user(user)
    set_user_state(user.id, None, None)
    bot.answer_callback_query(call.id, "السجلات 🗃️")
    send_custom_button_media_if_any(chat_id, "btn_logs")

    ops = get_user_bot_operations_history(user.id)
    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    user_row = get_user_row_by_id(user.id)
    since_date = user_row["created_at"] if user_row else now_utc

    if not ops:
        default_empty = (
            f"🗃️ <b>سجل عمليات البوت</b>\n"
            f"من تاريخ إنشاء الحساب: <code>{since_date}</code>\n"
            f"حتى وقت الطلب: <code>{now_utc}</code>\n\n"
            "لا توجد عمليات شحن إلى البوت أو سحب من البوت مسجلة حتى الآن."
        )
        bot.send_message(chat_id, get_custom_button_text("btn_logs", default_empty))
        return

    status_map = {
        "pending": "قيد المراجعة ⏳",
        "approved": "مقبولة ✅",
        "rejected": "مرفوضة ❌",
    }

    lines = [
        f"🗃️ <b>سجل عمليات البوت ({len(ops)})</b>",
        f"منذ إنشاء الحساب: <code>{since_date}</code>",
        f"حتى وقت الطلب: <code>{now_utc}</code>",
        "────────────────────",
    ]

    for op in ops[:30]:
        st_label = status_map.get(op["status"], op["status"])
        if op["kind"] == "deposit":
            lines.append(
                f"⬇️ <b>شحن إلى البوت #{op['id']}</b> ({op['method']})\n"
                f"💵 المبلغ: <b>{format_amount(op['amount'])}</b> | الحالة: <b>{st_label}</b>\n"
                f"🕒 التاريخ: <code>{op['created_at']}</code>"
            )
        else:
            unit = "USD" if op["method"] == "شام كاش دولار 💲" else "SYP"
            lines.append(
                f"⬆️ <b>سحب من البوت #{op['id']}</b> ({op['method']})\n"
                f"💵 المبلغ: <b>{format_amount(op['amount'])} SYP</b> | الصافي: <b>{format_amount(op['net_amount'] or 0.0)} {unit}</b>\n"
                f"📌 الحالة: <b>{st_label}</b> | 🕒 <code>{op['created_at']}</code>"
            )

    default_logs_text = "\n\n".join(lines)
    bot.send_message(chat_id, get_custom_button_text("btn_logs", default_logs_text))


@bot.callback_query_handler(func=lambda call: call.data == "btn_support")
def handle_support_button(call):
    """بدء التواصل مع الدعم عند الضغط على زر التواصل مع الدعم 📩."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return

    ensure_user(user)
    set_user_state(user.id, "support_waiting_message", None)
    bot.answer_callback_query(call.id, "التواصل مع الدعم")
    send_custom_button_media_if_any(chat_id, "btn_support")
    default_support_msg = (
        "💬 التواصل مع الدعم\n\n"
        "اكتب رسالتك أو أرسل صورة مع وصف وسنرد عليك في أقرب وقت:"
    )
    bot.send_message(
        chat_id,
        get_custom_button_text("btn_support", default_support_msg),
        reply_markup=support_cancel_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("sup_reply:"))
def handle_admin_support_reply_button(call):
    """تفعيل وضع الرد للمشرف Ola276 على رسالة دعم محددة."""
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "هذا الإجراء مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return

    _, ticket_id_str = call.data.split(":", 1)
    ticket_id = int(ticket_id_str)
    ticket = get_support_ticket(ticket_id)
    if not ticket:
        bot.answer_callback_query(call.id, "رسالة الدعم غير موجودة.", show_alert=True)
        return

    set_user_state(call.from_user.id, "admin_replying_support", str(ticket_id))
    bot.answer_callback_query(call.id, "أرسل ردك الآن")
    bot.send_message(
        call.from_user.id,
        f"💬 أرسل الآن نص الرد أو صورة مع وصف لإرسالها للمشترك صاحب التذكرة #{ticket_id} (آيدي: <code>{ticket['user_id']}</code>):",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "btn_deposit_acc")
def handle_deposit_acc_button(call):
    """بدء طلب شحن رصيد في الحساب من رصيد البوت عند الضغط على زر شحن رصيد في الحساب 🔽."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return

    acc = get_active_ichancy_account(user.id)
    if not acc:
        set_user_state(user.id, None, None)
        bot.answer_callback_query(call.id, "يجب إنشاء حساب أولاً", show_alert=True)
        bot.send_message(
            chat_id,
            "لا يوجد لديك حساب ichancy مفعل بعد. يرجى إنشاء حساب أولاً من قسم ⚡ichancy ⚡.",
            reply_markup=ichancy_menu_keyboard(),
        )
        return

    ensure_user(user)
    set_user_state(user.id, "acc_deposit_waiting_amount", None)
    bot.answer_callback_query(call.id, "شحن رصيد في الحساب")
    send_custom_button_media_if_any(chat_id, "btn_deposit_acc")

    default_prompt = (
        "أدخل المبلغ المراد شحنه  👇\n\n"
        "يرجى الانتباه الى ضرورة إدخال الارقام باللغة الانكليزية فقط"
    )
    bot.send_message(
        chat_id,
        get_custom_button_text("btn_deposit_acc", default_prompt),
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "btn_withdraw_acc")
def handle_withdraw_acc_button(call):
    """بدء طلب سحب رصيد من الحساب إلى رصيد البوت عند الضغط على زر سحب رصيد من الحساب 🔼."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return

    acc = get_active_ichancy_account(user.id)
    if not acc:
        set_user_state(user.id, None, None)
        bot.answer_callback_query(call.id, "يجب إنشاء حساب أولاً", show_alert=True)
        bot.send_message(
            chat_id,
            "لا يوجد لديك حساب ichancy مفعل بعد. يرجى إنشاء حساب أولاً من قسم ⚡ichancy ⚡.",
            reply_markup=ichancy_menu_keyboard(),
        )
        return

    ensure_user(user)
    set_user_state(user.id, "acc_withdraw_waiting_amount", None)
    bot.answer_callback_query(call.id, "سحب رصيد من الحساب")
    send_custom_button_media_if_any(chat_id, "btn_withdraw_acc")

    default_prompt = (
        "أدخل المبلغ المراد سحبه  👇\n\n"
        "يرجى الانتباه الى ضرورة إدخال الارقام باللغة الانكليزية فقط\n"
        "اقل مبلغ للسحب SYP200"
    )
    bot.send_message(
        chat_id,
        get_custom_button_text("btn_withdraw_acc", default_prompt),
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith(("acc_tr_approve:", "acc_tr_reject:")))
def handle_admin_account_transfer_actions(call):
    """معالجة موافقة أو رفض طلب شحن أو سحب رصيد في الحساب من قِبل المشرف الرئيسي Ola276."""
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "هذا الإجراء مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return

    action, tr_id_str = call.data.split(":", 1)
    tr_id = int(tr_id_str)
    tr_row = get_account_transfer_request(tr_id)

    if not tr_row:
        bot.answer_callback_query(call.id, "الطلب غير موجود.", show_alert=True)
        return

    target_user_id = int(tr_row["user_id"])
    transfer_type = str(tr_row["transfer_type"])
    amount = float(tr_row["amount"])
    formatted_amount = format_amount(amount)

    if action == "acc_tr_approve":
        if transfer_type == "deposit_acc":
            status_code, resulting_balance = approve_account_deposit_and_deduct_bot_balance(tr_id)
            if status_code == "not_pending":
                bot.answer_callback_query(call.id, "تمت معالجة هذا الطلب مسبقاً.", show_alert=True)
                return
            if status_code == "insufficient_balance":
                bot.answer_callback_query(
                    call.id,
                    f"رصيد البوت غير كافٍ للخصم ({format_amount(resulting_balance)} SYP).",
                    show_alert=True,
                )
                return

            formatted_new_balance = format_amount(resulting_balance)
            bot.answer_callback_query(call.id, "تمت الموافقة وخصم الرصيد من البوت ✅")
            try:
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=None,
                )
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=(
                        call.message.html_text
                        + f"\n\n✅ <b>تمت الموافقة وخصم {formatted_amount}SYP من رصيد البوت</b>"
                        + f"\n💰 <b>رصيد البوت الجديد: {formatted_new_balance}SYP</b>"
                    ),
                )
            except Exception:
                pass

            bot.send_message(
                target_user_id,
                f"تم تحول مبلغ {formatted_amount}SYP بنجاح ✅\n"
                f"رصيد البوت الجديد {formatted_new_balance}SYP",
            )

        else:
            status_code, resulting_balance = approve_account_withdraw_and_add_bot_balance(tr_id)
            if status_code == "not_pending":
                bot.answer_callback_query(call.id, "تمت معالجة هذا الطلب مسبقاً.", show_alert=True)
                return

            formatted_new_balance = format_amount(resulting_balance)
            bot.answer_callback_query(call.id, "تمت الموافقة وإضافة الرصيد إلى البوت ✅")
            try:
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=None,
                )
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=(
                        call.message.html_text
                        + f"\n\n✅ <b>تمت الموافقة وإضافة {formatted_amount}SYP إلى رصيد البوت</b>"
                        + f"\n💰 <b>رصيد البوت الجديد: {formatted_new_balance}SYP</b>"
                    ),
                )
            except Exception:
                pass

            bot.send_message(
                target_user_id,
                f"تم معالجة طلب السحب بنجاح ✅\n"
                f"المبلغ المسحوب {formatted_amount}SYP\n"
                f"رصيد البوت الجديد {formatted_new_balance}SYP",
            )

    elif action == "acc_tr_reject":
        if tr_row["status"] != "pending":
            bot.answer_callback_query(call.id, "تمت معالجة هذا الطلب مسبقاً.", show_alert=True)
            return

        set_account_transfer_status(tr_id, "rejected")
        bot.answer_callback_query(call.id, "تم رفض الطلب ❌")
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.html_text + "\n\n❌ <b>تم رفض الطلب</b>",
            )
        except Exception:
            pass

        if transfer_type == "deposit_acc":
            bot.send_message(
                target_user_id,
                "يرجى المحاوله مره اخرى بعد قليل 🔴",
            )
        else:
            bot.send_message(
                target_user_id,
                "يرجى محاولة السحب بعد قليل 🔴",
            )


@bot.callback_query_handler(func=lambda call: call.data == "btn_withdraw_bot")
def handle_withdraw_bot_button(call):
    """عرض طرق السحب المتاحة من البوت عند الضغط على زر سحب رصيد من البوت ⬆️."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return

    ensure_user(user)
    set_user_state(user.id, None, None)
    bot.answer_callback_query(call.id, "طرق السحب")
    send_custom_button_media_if_any(chat_id, "btn_withdraw_bot")
    default_msg = "اختر طرق السحب المتاحه.👇"
    bot.send_message(
        chat_id,
        get_custom_button_text("btn_withdraw_bot", default_msg),
        reply_markup=bot_withdraw_methods_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "wdr_method_syriatel")
def handle_withdraw_syriatel_method(call):
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)
    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return
    ensure_user(user)
    set_user_state(user.id, "wdr_syriatel_waiting_phone", None)
    bot.answer_callback_query(call.id, "سريتيل كاش")
    bot.send_message(
        chat_id,
        "أدخل الرقم المراد التحويل اليه\n\n"
        "الحد الادنى للسحب هو: SYP 250.00\n"
        "الحد الاعلى للسحب هو: SYP 5,000,000.00",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "wdr_method_sham_syp")
def handle_withdraw_sham_syp_method(call):
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)
    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return
    ensure_user(user)
    set_user_state(user.id, "wdr_sham_syp_waiting_code", None)
    bot.answer_callback_query(call.id, "شام كاش سوري")
    bot.send_message(
        chat_id,
        "ادخل كود الشام كاش الخاص بك\n\n"
        "الحد الادنى للسحب هو: SYP 2,000.00",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "wdr_method_sham_usd")
def handle_withdraw_sham_usd_method(call):
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)
    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return
    ensure_user(user)
    set_user_state(user.id, "wdr_sham_usd_waiting_code", None)
    bot.answer_callback_query(call.id, "شام كاش دولار")
    bot.send_message(
        chat_id,
        "ادخل كود الشام كاش الخاص بك\n\n"
        "الحد الادنى للسحب هو: SYP 2,000.00",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "wdr_method_bemo")
def handle_disabled_withdraw_methods(call):
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)
    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return
    set_user_state(user.id, None, None)
    bot.answer_callback_query(call.id, "الخدمة متوقفه حاليا ⚙️")
    bot.send_message(
        chat_id,
        "الخدمة متوقفه حاليا ⚙️",
        reply_markup=bot_withdraw_methods_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith(("wdr_approve:", "wdr_reject:")))
def handle_admin_withdraw_actions(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "هذا الإجراء مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return

    action, w_id_str = call.data.split(":", 1)
    w_id = int(w_id_str)
    w_row = get_bot_withdraw_request(w_id)

    if not w_row:
        bot.answer_callback_query(call.id, "طلب السحب غير موجود.", show_alert=True)
        return

    target_user_id = int(w_row["user_id"])
    amount = float(w_row["amount"])
    method = str(w_row["method"])

    if action == "wdr_approve":
        status_code, resulting_balance = approve_withdraw_and_deduct_balance(w_id)
        if status_code == "not_pending":
            bot.answer_callback_query(call.id, "تمت معالجة هذا الطلب مسبقاً.", show_alert=True)
            return
        if status_code == "insufficient_balance":
            bot.answer_callback_query(
                call.id,
                f"رصيد المشترك غير كافٍ للخصم ({format_amount(resulting_balance)} SYP).",
                show_alert=True,
            )
            return

        bot.answer_callback_query(
            call.id,
            f"تمت الموافقة وخصم {format_amount(amount)} SYP من رصيد البوت ✅",
        )
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    call.message.html_text
                    + f"\n\n✅ <b>تمت الموافقة وخصم {format_amount(amount)} SYP من رصيد البوت</b>"
                    + f"\n💰 <b>رصيد البوت الجديد للمشترك: {format_amount(resulting_balance)} SYP</b>"
                ),
            )
        except Exception:
            pass

        if method == "شام كاش دولار 💲":
            bot.send_message(
                target_user_id,
                "تم الموافقه.على طلب السحب\n"
                "سيتم تحويل الاموال في اقرب وقت ممكن ✅",
            )
        else:
            bot.send_message(
                target_user_id,
                "تم الموافقه .على طلب السحب\n"
                "سيتم ارسال الاموال في اقرب وقت ممكن ✅",
            )

    elif action == "wdr_reject":
        if w_row["status"] != "pending":
            bot.answer_callback_query(call.id, "تمت معالجة هذا الطلب مسبقاً.", show_alert=True)
            return

        set_bot_withdraw_status(w_id, "rejected")
        bot.answer_callback_query(call.id, "تم رفض طلب السحب ❌")
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.html_text + "\n\n❌ <b>تم رفض الطلب</b>",
            )
        except Exception:
            pass

        if method == "شام كاش دولار 💲":
            bot.send_message(
                target_user_id,
                "يرجى المحاوله في وقت لاحق 🔴",
            )
        else:
            bot.send_message(
                target_user_id,
                "يرجى المحاوله بعد قليل وشكرا 🌸",
            )


@bot.callback_query_handler(func=lambda call: call.data == "btn_deposit_bot")
def handle_deposit_bot_button(call):
    """عرض طرق الشحن المتاحة إلى البوت عند الضغط على زر شحن رصيد الى البوت ⬇️."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return

    ensure_user(user)
    set_user_state(user.id, None, None)
    bot.answer_callback_query(call.id, "طرق الشحن")
    send_custom_button_media_if_any(chat_id, "btn_deposit_bot")
    default_msg = "اختر احد طرق الشحن المتاحه 👇"
    bot.send_message(
        chat_id,
        get_custom_button_text("btn_deposit_bot", default_msg),
        reply_markup=bot_deposit_methods_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "dep_method_syriatel")
def handle_syriatel_method(call):
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)
    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return
    ensure_user(user)
    set_user_state(user.id, "dep_syriatel_waiting_amount", None)
    bot.answer_callback_query(call.id, "سيرياتيل كاش")
    bot.send_message(
        chat_id,
        "📱 شحن عبر سيرياتيل كاش\n\n"
        "أرسل المبلغ الذي تريد تحويله.\n"
        "الحد الأدنى: 200 ليرة سورية جديدة.",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "dep_method_sham_syp")
def handle_sham_syp_method(call):
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)
    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return
    ensure_user(user)
    set_user_state(user.id, "dep_sham_syp_waiting_tx", None)
    bot.answer_callback_query(call.id, "شام كاش سوري")
    bot.send_message(
        chat_id,
        "قم بالتحويل الى الكود التالي\n\n"
        f"<code>{get_sham_cash_syp_code()}</code>\n"
        "ثم ادخل رقم العملية\n\n"
        "الحد الادنى للشحن: SYP 200.00\n"
        "يرجى الانتباه الى ان اي مبلغ اقل من الحد الادنى لن تتم معالجته ولا يمكن استرداده",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "dep_method_sham_usd")
def handle_sham_usd_method(call):
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)
    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return
    ensure_user(user)
    set_user_state(user.id, "dep_sham_usd_waiting_tx", None)
    bot.answer_callback_query(call.id, "شام كاش دولار")
    usd_rate = format_amount(get_sham_cash_usd_rate_syp())
    bot.send_message(
        chat_id,
        "قم بالتحويل الى الكود التالي\n\n"
        f"<code>{get_sham_cash_usd_code()}</code>\n\n"
        "ثم ادخل رقم العملية\n"
        f"كل 1 شام كاش 💲 (اوتو 💱) تعادل: SYP {usd_rate}.00",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "dep_method_bemo")
def handle_bemo_method(call):
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)
    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return
    set_user_state(user.id, None, None)
    bot.answer_callback_query(call.id, "الخدمه متوقفه حاليا ⚙️")
    bot.send_message(
        chat_id,
        "الخدمه متوقفه حاليا ⚙️",
        reply_markup=bot_deposit_methods_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith(("dep_approve:", "dep_reject:")))
def handle_admin_deposit_actions(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "هذا الإجراء مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return

    action, dep_id_str = call.data.split(":", 1)
    dep_id = int(dep_id_str)
    dep_row = get_bot_deposit_request(dep_id)

    if not dep_row:
        bot.answer_callback_query(call.id, "طلب الشحن غير موجود.", show_alert=True)
        return

    if dep_row["status"] != "pending":
        bot.answer_callback_query(call.id, "تمت معالجة هذا الطلب مسبقاً.", show_alert=True)
        return

    target_user_id = int(dep_row["user_id"])
    raw_amount = float(dep_row["amount"])
    method = str(dep_row["method"])
    usd_rate = get_sham_cash_usd_rate_syp()

    if method == "شام كاش دولار 💲":
        credit_syp = round(raw_amount * usd_rate, 2)
    else:
        credit_syp = round(raw_amount, 2)

    formatted_credit_syp = format_amount(credit_syp)

    if action == "dep_approve":
        set_bot_deposit_status(dep_id, "approved")
        new_balance = add_user_balance(target_user_id, credit_syp)
        formatted_new_balance = format_amount(new_balance)

        bot.answer_callback_query(call.id, "تمت الموافقة وإضافة الرصيد ✅")
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.html_text + "\n\n✅ <b>تمت الموافقة وإضافة الرصيد</b>",
            )
        except Exception:
            pass

        if method == "شام كاش دولار 💲":
            bot.send_message(
                target_user_id,
                f"تم اضافه مبلغ {formatted_credit_syp}SYP بنجاح ✅\n"
                f"رصيد البوت الجديد {formatted_new_balance}SYP",
            )
        elif method == "شام كاش سوري 💵":
            bot.send_message(
                target_user_id,
                f"تم شحن مبلغ {formatted_credit_syp}SYP بنجاح ✅\n"
                f"رصيد البوت الجديد {formatted_new_balance}SYP",
            )
        else:
            bot.send_message(
                target_user_id,
                f"تم اضافة مبلغ {formatted_credit_syp}SYP بنجاح ✅\n"
                f"رصيد البوت الجديد {formatted_new_balance}SYP",
            )

    elif action == "dep_reject":
        set_bot_deposit_status(dep_id, "rejected")
        bot.answer_callback_query(call.id, "تم رفض طلب الشحن ❌")
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None,
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.html_text + "\n\n❌ <b>تم رفض الطلب</b>",
            )
        except Exception:
            pass

        if method == "شام كاش دولار 💲":
            bot.send_message(
                target_user_id,
                "العمليه غير صحيحه .يرجى التأكد من المعلومات والمحاوله مره اخرى 🔴",
            )
        elif method == "شام كاش سوري 💵":
            bot.send_message(
                target_user_id,
                "العمليه غير صحيحه .يرجى التأكد من المعلومات واعادة المحاوله 🔴",
            )
        else:
            bot.send_message(
                target_user_id,
                "يرجى المحاوله في وقت لاحق",
            )


@bot.callback_query_handler(func=lambda call: call.data == "btn_ichancy")
def handle_ichancy_button(call):
    """فتح قائمة Ichancy عند الضغط على زر ⚡ichancy ⚡."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return

    set_user_state(user.id, None, None)
    bot.answer_callback_query(call.id, "Ichancy")
    send_custom_button_media_if_any(chat_id, "btn_ichancy")
    bot.send_message(
        chat_id,
        get_custom_button_text("btn_ichancy", "Ichancy"),
        reply_markup=ichancy_menu_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "ichancy_create")
def handle_ichancy_create(call):
    """بدء خطوة إدخال اسم الحساب أو منع التكرار إذا كان يملك حساباً مفعلاً."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return

    existing_acc = get_active_ichancy_account(user.id)
    if existing_acc:
        set_user_state(user.id, None, None)
        bot.answer_callback_query(call.id, "لديك حساب مفعل بالفعل", show_alert=True)
        bot.send_message(
            chat_id,
            "لايمكن انشاء حساب أخر لديك حساب مفعل 🌸\n\n"
            f"👤 اسم الحساب: <code>{existing_acc['acc_username']}</code>\n"
            f"🔑 كلمة المرور: <code>{existing_acc['acc_password']}</code>",
            reply_markup=ichancy_menu_keyboard(),
        )
        return

    set_user_state(user.id, "ichancy_waiting_username", None)
    bot.answer_callback_query(call.id, "أدخل الاسم")
    bot.send_message(
        chat_id,
        "أدخل الاسم بشرط ان لا يقل عن ثماني احرف انجليزيه صغيره وأحرف (بدون رموز )👇",
        reply_markup=cancel_to_main_keyboard(),
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith(("req_approve:", "req_reject:", "req_edit_user:", "req_edit_pass:"))
)
def handle_admin_request_actions(call):
    if not is_main_admin(call.from_user):
        bot.answer_callback_query(call.id, "هذا الإجراء مخصص للمشرف الرئيسي Ola276 فقط.", show_alert=True)
        return

    action, req_id_str = call.data.split(":", 1)
    req_id = int(req_id_str)
    req_row = get_account_request(req_id)

    if not req_row:
        bot.answer_callback_query(call.id, "الطلب غير موجود.", show_alert=True)
        return

    target_user_id = int(req_row["user_id"])

    if req_row["status"] != "pending" and action in {"req_approve", "req_reject"}:
        bot.answer_callback_query(call.id, "تمت معالجة هذا الطلب مسبقاً.", show_alert=True)
        return

    if action == "req_approve":
        set_request_status(req_id, "approved")
        save_active_ichancy_account(
            target_user_id,
            req_row["acc_username"],
            req_row["acc_password"],
        )
        set_user_state(target_user_id, None, None)

        bot.answer_callback_query(call.id, "تمت الموافقة وإرسال الحساب للمشترك ✅")
        updated_req = get_account_request(req_id)
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=build_admin_request_text(updated_req),
            )
        except Exception:
            pass

        bot.send_message(
            target_user_id,
            "✅ تم إنشاء وتفعيل حساب ichancy الخاص بك بنجاح:\n\n"
            f"🆔 آيدي المشترك: <code>{target_user_id}</code>\n"
            f"👤 اسم الحساب: <code>{updated_req['acc_username']}</code>\n"
            f"🔑 كلمة المرور: <code>{updated_req['acc_password']}</code>",
        )

    elif action == "req_reject":
        set_request_status(req_id, "rejected")
        set_user_state(target_user_id, None, None)

        bot.answer_callback_query(call.id, "تم رفض الطلب ❌")
        updated_req = get_account_request(req_id)
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=build_admin_request_text(updated_req),
            )
        except Exception:
            pass

        bot.send_message(
            target_user_id,
            "يرجى المحاوله في وقت لاحق",
        )

    elif action == "req_edit_user":
        set_user_state(call.from_user.id, "admin_editing_username", str(req_id))
        bot.answer_callback_query(call.id, "أرسل الاسم الجديد")
        bot.send_message(
            call.from_user.id,
            f"✏️ أرسل الاسم الجديد للطلب #{req_id} (8 أحرف إنجليزية صغيرة على الأقل وبدون رموز):",
        )

    elif action == "req_edit_pass":
        set_user_state(call.from_user.id, "admin_editing_password", str(req_id))
        bot.answer_callback_query(call.id, "أرسل كلمة المرور الجديدة")
        bot.send_message(
            call.from_user.id,
            f"🔑 أرسل كلمة المرور الجديدة للطلب #{req_id}:",
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("btn_"))
def handle_main_feature_buttons(call):
    """معالجة الضغط على بقية الأزرار الرئيسية مع دعم الرسالة والصور المخصصة."""
    user = call.from_user
    chat_id = call.message.chat.id
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if not is_user_subscribed(user.id):
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القناة أولاً.", show_alert=True)
        send_force_sub_message(chat_id, is_new_user=False)
        return

    button_titles = {
        "btn_offers": "العروض الحاليه 🎁",
        "btn_terms": "الشروط والاحكام 📝",
        "btn_lottery": "الياناصيب الاسبوعي💵",
    }
    title = button_titles.get(call.data, "خيار")
    bot.answer_callback_query(call.id, title)
    send_custom_button_media_if_any(chat_id, call.data)
    default_msg = f"تم اختيار: <b>{title}</b>"
    bot.send_message(
        chat_id,
        get_custom_button_text(call.data, default_msg),
    )


@bot.message_handler(content_types=["photo"])
def handle_photo_messages(message):
    """معالجة الصور المرسلة للوحة تحكم المشرف أو التواصل مع الدعم أو ردود المشرف Ola276."""
    user = message.from_user
    chat_id = message.chat.id
    caption = (message.caption or "").strip()
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    best_photo_id = message.photo[-1].file_id if message.photo else None
    state, temp_data = get_user_state(user.id)

    # حفظ صورة مخصصة لأي زر من لوحة تحكم المشرف Ola276
    if is_main_admin(user) and state == "adm_waiting_btn_photo" and temp_data and best_photo_id:
        btn_key = temp_data
        save_button_photo(btn_key, best_photo_id)
        if caption:
            save_button_message(btn_key, caption)
        set_user_state(user.id, None, None)
        btn_title = BUTTON_KEY_TO_TITLE.get(btn_key, btn_key)
        bot.send_message(
            chat_id,
            f"✅ تم حفظ الصورة للزر <b>{btn_title}</b> بنجاح."
            + ("\n✍️ وتم تحديث نص الرسالة المرفقة أيضاً." if caption else ""),
            reply_markup=admin_single_button_actions_keyboard(btn_key),
        )
        return

    if is_main_admin(user) and state == "admin_replying_support" and temp_data and best_photo_id:
        ticket_id = int(temp_data)
        ticket = get_support_ticket(ticket_id)
        set_user_state(user.id, None, None)
        if not ticket:
            bot.send_message(chat_id, "تذكرة الدعم غير موجودة.")
            return

        target_user_id = int(ticket["user_id"])
        reply_caption = "💬 <b>رد الدعم:</b>"
        if caption:
            reply_caption += f"\n{caption}"
        bot.send_photo(target_user_id, photo=best_photo_id, caption=reply_caption)
        mark_support_ticket_replied(ticket_id)
        bot.send_message(chat_id, f"✅ تم إرسال ردك بنجاح إلى المشترك صاحب التذكرة #{ticket_id}.")
        return

    if state == "support_waiting_message" and best_photo_id:
        if not is_user_subscribed(user.id):
            send_force_sub_message(chat_id, is_new_user=False)
            return

        ensure_user(user)
        set_user_state(user.id, None, None)
        ticket_id = create_support_ticket(
            user.id,
            "photo",
            content_text=caption or None,
            photo_file_id=best_photo_id,
        )
        bot.send_message(chat_id, "✅ تم إرسال رسالتك إلى فريق الدعم بنجاح، سنرد عليك في أقرب وقت.")
        send_support_ticket_to_ola276(ticket_id)
        return

    first_time = is_first_time_user(user.id)
    ensure_user(user)
    if first_time or not is_user_subscribed(user.id):
        send_force_sub_message(chat_id, is_new_user=first_time)


@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    """التعامل مع الرسائل النصية وحالات لوحة التحكم والدعم والسحب والشحن وإنشاء الحساب."""
    user = message.from_user
    chat_id = message.chat.id
    text = (message.text or "").strip()
    sync_ola276_identity(user)
    setup_bottom_menu(chat_id, user=user)

    if is_main_admin(user):
        flush_pending_requests_to_ola276()

    state, temp_data = get_user_state(user.id)

    # 0. حالات لوحة تحكم المشرف الرئيسي Ola276
    if is_main_admin(user) and state:
        if state == "adm_waiting_btn_msg" and temp_data:
            if not text:
                bot.send_message(chat_id, "❌ يرجى إرسال نص الرسالة.")
                return
            btn_key = temp_data
            save_button_message(btn_key, text)
            set_user_state(user.id, None, None)
            bot.send_message(
                chat_id,
                f"✅ تم حفظ الرسالة الجديدة للزر <b>{BUTTON_KEY_TO_TITLE.get(btn_key, btn_key)}</b>.",
                reply_markup=admin_single_button_actions_keyboard(btn_key),
            )
            return

        if state == "adm_waiting_user_query":
            target_row = find_user_by_query(text)
            if not target_row:
                bot.send_message(chat_id, "❌ لم يتم العثور على مشترك بهذا الآيدي أو المعرف. أعد المحاولة:")
                return
            set_user_state(user.id, None, None)
            t_id = int(target_row["user_id"])
            t_uname = f"@{target_row['username']}" if target_row["username"] else "غير متوفر"
            t_bal = format_amount(float(target_row["balance"]))
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton("➕ إضافة رصيد", callback_data=f"adm_bal_op:add:{t_id}"),
                InlineKeyboardButton("➖ خصم رصيد", callback_data=f"adm_bal_op:sub:{t_id}"),
            )
            kb.row(
                InlineKeyboardButton("🎯 تعيين رصيد", callback_data=f"adm_bal_op:set:{t_id}"),
                InlineKeyboardButton("⬅️ رجوع", callback_data="adm_open_panel"),
            )
            bot.send_message(
                chat_id,
                f"👤 <b>بيانات المشترك</b>\n\n"
                f"🆔 الآيدي: <code>{t_id}</code>\n"
                f"🔗 المعرف: {t_uname}\n"
                f"💰 الرصيد الحالي: <b>{t_bal} SYP</b>\n"
                f"📅 تاريخ التسجيل: <code>{target_row['created_at']}</code>",
                reply_markup=kb,
            )
            return

        if state.startswith("adm_bal_amount_") and temp_data:
            op_type = state.replace("adm_bal_amount_", "")
            target_id = int(temp_data)
            cleaned_num = text.replace(",", ".").strip()
            try:
                val = float(cleaned_num)
            except ValueError:
                bot.send_message(chat_id, "❌ أدخل رقماً صحيحاً.")
                return
            if val < 0:
                bot.send_message(chat_id, "❌ يجب أن يكون المبلغ 0 أو أكبر.")
                return
            row_before = get_user_row_by_id(target_id)
            cur_bal = float(row_before["balance"]) if row_before else 0.0
            if op_type == "add":
                new_bal = add_user_balance(target_id, val)
            elif op_type == "sub":
                new_bal = set_user_balance_exact(target_id, cur_bal - val)
            else:
                new_bal = set_user_balance_exact(target_id, val)
            set_user_state(user.id, None, None)
            bot.send_message(
                chat_id,
                f"✅ تم تحديث رصيد المشترك <code>{target_id}</code> إلى: <b>{format_amount(new_bal)} SYP</b>",
                reply_markup=admin_panel_keyboard(),
            )
            return

        if state == "adm_waiting_channel":
            clean_ch = text.strip()
            uname_ch = clean_ch if clean_ch.startswith("@") else f"@{clean_ch}"
            url_ch = f"https://t.me/{uname_ch.lstrip('@')}"
            set_setting("channel_username", uname_ch)
            set_setting("channel_url", url_ch)
            set_user_state(user.id, None, None)
            bot.send_message(
                chat_id,
                f"✅ تم تحديث قناة الاشتراك الإجباري إلى: <code>{uname_ch}</code>",
                reply_markup=admin_settings_keyboard(),
            )
            return

        if state == "adm_waiting_code_syr":
            set_setting("syriatel_code", text)
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, f"✅ تم تحديث كود سيرياتيل كاش إلى: <code>{text}</code>", reply_markup=admin_settings_keyboard())
            return

        if state == "adm_waiting_code_sham_syp":
            set_setting("sham_cash_syp_code", text)
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, f"✅ تم تحديث كود شام كاش السوري إلى: <code>{text}</code>", reply_markup=admin_settings_keyboard())
            return

        if state == "adm_waiting_code_sham_usd":
            set_setting("sham_cash_usd_code", text)
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, f"✅ تم تحديث كود شام كاش الدولار إلى: <code>{text}</code>", reply_markup=admin_settings_keyboard())
            return

        if state == "adm_waiting_rates":
            parts = text.replace(",", ".").split()
            if len(parts) != 3:
                bot.send_message(chat_id, "❌ أرسل 3 أرقام: سعر صرف الشحن، سعر صرف السحب، ونسبة العمولة %.")
                return
            try:
                dep_r = float(parts[0])
                wdr_r = float(parts[1])
                comm_pct = float(parts[2])
            except ValueError:
                bot.send_message(chat_id, "❌ يرجى إدخال أرقام صحيحة.")
                return
            set_setting("sham_cash_usd_rate_syp", str(dep_r))
            set_setting("withdraw_usd_rate_syp", str(wdr_r))
            set_setting("withdraw_commission_rate", str(comm_pct / 100.0))
            set_user_state(user.id, None, None)
            bot.send_message(
                chat_id,
                f"✅ تم تحديث الأسعار والعمولة: شحن USD = <b>{format_amount(dep_r)}</b> | سحب USD = <b>{format_amount(wdr_r)}</b> | عمولة = <b>{format_amount(comm_pct)}%</b>",
                reply_markup=admin_settings_keyboard(),
            )
            return

        if state == "adm_waiting_broadcast":
            set_user_state(user.id, None, None)
            with get_connection() as conn:
                all_users = conn.execute("SELECT user_id FROM users").fetchall()
            sent_ok = 0
            for u_row in all_users:
                try:
                    bot.send_message(int(u_row["user_id"]), text)
                    sent_ok += 1
                except Exception:
                    pass
            bot.send_message(
                chat_id,
                f"✅ تم إرسال الإذاعة إلى <b>{sent_ok}</b> من أصل <b>{len(all_users)}</b> مشترك.",
                reply_markup=admin_panel_keyboard(),
            )
            return

    # 1. معالجة رد المشرف الرئيسي Ola276 على رسالة الدعم
    if is_main_admin(user) and state == "admin_replying_support" and temp_data:
        ticket_id = int(temp_data)
        ticket = get_support_ticket(ticket_id)
        set_user_state(user.id, None, None)
        if not ticket:
            bot.send_message(chat_id, "تذكرة الدعم غير موجودة.")
            return
        if not text:
            bot.send_message(chat_id, "❌ يرجى إرسال نص الرد أو صورة.")
            return

        target_user_id = int(ticket["user_id"])
        bot.send_message(target_user_id, f"💬 <b>رد الدعم:</b>\n{text}")
        mark_support_ticket_replied(ticket_id)
        bot.send_message(chat_id, f"✅ تم إرسال ردك بنجاح إلى المشترك صاحب التذكرة #{ticket_id}.")
        return

    # 2. معالجة رسالة الدعم النصية القادمة من المشترك
    if state == "support_waiting_message":
        if not text:
            bot.send_message(
                chat_id,
                "💬 التواصل مع الدعم\n\n"
                "اكتب رسالتك أو أرسل صورة مع وصف وسنرد عليك في أقرب وقت:",
                reply_markup=support_cancel_keyboard(),
            )
            return

        set_user_state(user.id, None, None)
        ticket_id = create_support_ticket(user.id, "text", content_text=text, photo_file_id=None)
        bot.send_message(chat_id, "✅ تم إرسال رسالتك إلى فريق الدعم بنجاح، سنرد عليك في أقرب وقت.")
        send_support_ticket_to_ola276(ticket_id)
        return

    # 3. معالجة إدخال المشرف الرئيسي Ola276 لتعديل الاسم أو كلمة المرور في طلب معلق
    if is_main_admin(user) and state in {"admin_editing_username", "admin_editing_password"} and temp_data:
        req_id = int(temp_data)
        req_row = get_account_request(req_id)
        if not req_row:
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, "الطلب غير موجود.")
            return

        if state == "admin_editing_username":
            if not USERNAME_PATTERN.match(text):
                bot.send_message(
                    chat_id,
                    "❌ الاسم غير مطابق للشرط: يجب أن يكون 8 أحرف إنجليزية صغيرة على الأقل وأحرف فقط بدون رموز. أعد الإرسال:",
                )
                return
            update_request_username(req_id, text)
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, f"✅ تم تحديث اسم الحساب للطلب #{req_id} إلى: <code>{text}</code>")
            send_request_to_ola276(req_id)
            return

        if state == "admin_editing_password":
            if len(text) < 4:
                bot.send_message(chat_id, "❌ كلمة المرور قصيرة جداً، أرسل كلمة مرور صالحة:")
                return
            update_request_password(req_id, text)
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, f"✅ تم تحديث كلمة المرور للطلب #{req_id}.")
            send_request_to_ola276(req_id)
            return

    # 4. معالجة شحن رصيد في الحساب
    if state == "acc_deposit_waiting_amount":
        acc = get_active_ichancy_account(user.id)
        if not acc:
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, "لا يوجد لديك حساب ichancy مفعل بعد.", reply_markup=ichancy_menu_keyboard())
            return

        if not ENGLISH_NUMBER_PATTERN.match(text):
            bot.send_message(
                chat_id,
                "يرجى الانتباه الى ضرورة إدخال الارقام باللغة الانكليزية فقط\nأدخل المبلغ المراد شحنه  👇",
                reply_markup=cancel_to_main_keyboard(),
            )
            return

        amount = float(text)
        if amount < MIN_ACCOUNT_DEPOSIT:
            bot.send_message(
                chat_id,
                f"❌ الحد الأدنى لشحن الحساب هو SYP{format_amount(MIN_ACCOUNT_DEPOSIT)}.\nأدخل المبلغ المراد شحنه  👇",
                reply_markup=cancel_to_main_keyboard(),
            )
            return

        current_balance = ensure_user(user)
        if amount > current_balance:
            bot.send_message(
                chat_id,
                f"لاتملك رصيد كافي لعملية التحويل, رصيدك الحالي: {format_amount(current_balance)}SYP",
                reply_markup=cancel_to_main_keyboard(),
            )
            return

        set_user_state(user.id, None, None)
        tr_id = create_account_transfer_request(user.id, "deposit_acc", str(acc["acc_username"]), amount)
        bot.send_message(chat_id, "يتم معالجة الطلب .الأتصال بالمنصه...⏳")
        send_account_transfer_request_to_ola276(tr_id)
        return

    # 5. معالجة سحب رصيد من الحساب
    if state == "acc_withdraw_waiting_amount":
        acc = get_active_ichancy_account(user.id)
        if not acc:
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, "لا يوجد لديك حساب ichancy مفعل بعد.", reply_markup=ichancy_menu_keyboard())
            return

        if not ENGLISH_NUMBER_PATTERN.match(text):
            bot.send_message(
                chat_id,
                "يرجى الانتباه الى ضرورة إدخال الارقام باللغة الانكليزية فقط\nاقل مبلغ للسحب SYP200\nأدخل المبلغ المراد سحبه  👇",
                reply_markup=cancel_to_main_keyboard(),
            )
            return

        amount = float(text)
        if amount < MIN_ACCOUNT_WITHDRAW:
            bot.send_message(
                chat_id,
                "اقل مبلغ للسحب SYP200\nأدخل المبلغ المراد سحبه  👇",
                reply_markup=cancel_to_main_keyboard(),
            )
            return

        set_user_state(user.id, None, None)
        tr_id = create_account_transfer_request(user.id, "withdraw_acc", str(acc["acc_username"]), amount)
        bot.send_message(chat_id, "يتم معالجة طلب السحب ..الاتصال بالمنصه .....⏳")
        send_account_transfer_request_to_ola276(tr_id)
        return

    # 6. سحب رصيد البوت عبر شام كاش دولار
    if state == "wdr_sham_usd_waiting_code":
        if not text:
            bot.send_message(chat_id, "ادخل كود الشام كاش الخاص بك\n\nالحد الادنى للسحب هو: SYP 2,000.00", reply_markup=cancel_to_main_keyboard())
            return
        set_user_state(user.id, "wdr_sham_usd_waiting_amount", text)
        bot.send_message(chat_id, "أدخل المبلغ المراد سحبه 👇\nعلماً أن الحد الادنى للسحب هو: SYP 2,000.00", reply_markup=cancel_to_main_keyboard())
        return

    if state == "wdr_sham_usd_waiting_amount":
        current_balance = ensure_user(user)
        try:
            amount = float(text.replace(",", ".").strip())
        except ValueError:
            bot.send_message(chat_id, "❌ يرجى إدخال مبلغ صحيح بالأرقام.", reply_markup=cancel_to_main_keyboard())
            return
        if amount < MIN_WITHDRAW_SHAM_CASH:
            bot.send_message(chat_id, "❌ المبلغ أقل من الحد الأدنى للسحب (SYP 2,000.00).", reply_markup=cancel_to_main_keyboard())
            return
        if amount > current_balance:
            bot.send_message(chat_id, f"لاتملك رصيد كافي لعملية السحب, رصيدك الحالي: {format_amount(current_balance)}SYP", reply_markup=cancel_to_main_keyboard())
            return
        sham_code = temp_data or ""
        set_user_state(user.id, None, None)
        comm_rate = get_withdraw_commission_rate()
        wdr_usd_rate = get_withdraw_usd_rate_syp()
        commission_syp = round(amount * comm_rate, 2)
        net_syp = round(amount - commission_syp, 2)
        net_usd = round(net_syp / wdr_usd_rate, 2)
        w_id = create_bot_withdraw_request(user.id, "شام كاش دولار 💲", sham_code, amount, commission_syp, net_usd)
        bot.send_message(
            chat_id,
            f"طلب السحب رقم {w_id}\n"
            f"الرقم المرسل اليه : {sham_code}\n"
            f"المبلغ المسحوب كامل : {format_amount(amount)}SYP\n"
            f"عموله {int(round(comm_rate * 100))}٪ على مبلغ السحب : {format_amount(commission_syp)}SYP\n"
            f"كل {format_amount(wdr_usd_rate)}SYP. =1USD\n"
            f"صافي المبلغ بعد خصم العموله : {format_amount(net_usd)}USD",
        )
        send_withdraw_request_to_ola276(w_id)
        return

    # 7. سحب رصيد البوت عبر سريتيل كاش
    if state == "wdr_syriatel_waiting_phone":
        if not text:
            bot.send_message(chat_id, "أدخل الرقم المراد التحويل اليه", reply_markup=cancel_to_main_keyboard())
            return
        set_user_state(user.id, "wdr_syriatel_waiting_amount", text)
        bot.send_message(chat_id, "أدخل المبلغ المراد سحبه 👇\nالحد الادنى للسحب هو: SYP 250.00\nالحد الاعلى للسحب هو: SYP 5,000,000.00", reply_markup=cancel_to_main_keyboard())
        return

    if state == "wdr_syriatel_waiting_amount":
        current_balance = ensure_user(user)
        try:
            amount = float(text.replace(",", ".").strip())
        except ValueError:
            bot.send_message(chat_id, "❌ يرجى إدخال مبلغ صحيح بالأرقام.", reply_markup=cancel_to_main_keyboard())
            return
        if amount < MIN_WITHDRAW_SYRIATEL or amount > MAX_WITHDRAW_SYRIATEL:
            bot.send_message(chat_id, "❌ المبلغ خارج الحدود المسموحة للسحب.", reply_markup=cancel_to_main_keyboard())
            return
        if amount > current_balance:
            bot.send_message(chat_id, f"لاتملك رصيد كافي لعملية السحب, رصيدك الحالي: {format_amount(current_balance)}SYP", reply_markup=cancel_to_main_keyboard())
            return
        phone_number = temp_data or ""
        set_user_state(user.id, None, None)
        comm_rate = get_withdraw_commission_rate()
        commission = round(amount * comm_rate, 2)
        net_amount = round(amount - commission, 2)
        w_id = create_bot_withdraw_request(user.id, "سريتيل كاش 🪙", phone_number, amount, commission, net_amount)
        bot.send_message(
            chat_id,
            f"طلب السحب رقم {w_id}\n"
            f"الرقم المرسل اليه : {phone_number}\n"
            f"المبلغ المسحوب كامل : {format_amount(amount)}SYP\n"
            f"عموله {int(round(comm_rate * 100))}٪ على مبلغ السحب : {format_amount(commission)}SYP\n"
            f"صافي المبلغ بعد خصم العموله : {format_amount(net_amount)}SYP",
        )
        send_withdraw_request_to_ola276(w_id)
        return

    # 8. سحب رصيد البوت عبر شام كاش سوري
    if state == "wdr_sham_syp_waiting_code":
        if not text:
            bot.send_message(chat_id, "ادخل كود الشام كاش الخاص بك", reply_markup=cancel_to_main_keyboard())
            return
        set_user_state(user.id, "wdr_sham_syp_waiting_amount", text)
        bot.send_message(chat_id, "أدخل المبلغ المراد سحبه 👇\nالحد الادنى للسحب هو: SYP 2,000.00", reply_markup=cancel_to_main_keyboard())
        return

    if state == "wdr_sham_syp_waiting_amount":
        current_balance = ensure_user(user)
        try:
            amount = float(text.replace(",", ".").strip())
        except ValueError:
            bot.send_message(chat_id, "❌ يرجى إدخال مبلغ صحيح بالأرقام.", reply_markup=cancel_to_main_keyboard())
            return
        if amount < MIN_WITHDRAW_SHAM_CASH:
            bot.send_message(chat_id, "❌ المبلغ أقل من الحد الأدنى للسحب (SYP 2,000.00).", reply_markup=cancel_to_main_keyboard())
            return
        if amount > current_balance:
            bot.send_message(chat_id, f"لاتملك رصيد كافي لعملية السحب, رصيدك الحالي: {format_amount(current_balance)}SYP", reply_markup=cancel_to_main_keyboard())
            return
        sham_code = temp_data or ""
        set_user_state(user.id, None, None)
        comm_rate = get_withdraw_commission_rate()
        commission = round(amount * comm_rate, 2)
        net_amount = round(amount - commission, 2)
        w_id = create_bot_withdraw_request(user.id, "شام كاش سوري 💵", sham_code, amount, commission, net_amount)
        bot.send_message(
            chat_id,
            f"طلب السحب رقم {w_id}\n"
            f"الرقم المرسل اليه : {sham_code}\n"
            f"المبلغ المسحوب كامل : {format_amount(amount)}SYP\n"
            f"عموله {int(round(comm_rate * 100))}٪ على مبلغ السحب : {format_amount(commission)}SYP\n"
            f"صافي المبلغ بعد خصم العموله : {format_amount(net_amount)}SYP",
        )
        send_withdraw_request_to_ola276(w_id)
        return

    # 9. شحن رصيد البوت عبر شام كاش دولار
    if state == "dep_sham_usd_waiting_tx":
        if not text:
            bot.send_message(chat_id, "يرجى إدخال رقم العملية:", reply_markup=cancel_to_main_keyboard())
            return
        set_user_state(user.id, "dep_sham_usd_waiting_amount", text)
        bot.send_message(chat_id, "أدخل المبلغ المراد شحنه 👇", reply_markup=cancel_to_main_keyboard())
        return

    if state == "dep_sham_usd_waiting_amount":
        try:
            amount = float(text.replace(",", ".").strip())
        except ValueError:
            bot.send_message(chat_id, "❌ يرجى إدخال مبلغ صحيح بالأرقام.", reply_markup=cancel_to_main_keyboard())
            return
        if amount <= 0:
            bot.send_message(chat_id, "❌ يرجى إدخال مبلغ أكبر من صفر.", reply_markup=cancel_to_main_keyboard())
            return
        tx_number = temp_data or ""
        set_user_state(user.id, None, None)
        ensure_user(user)
        dep_id = create_bot_deposit_request(user.id, "شام كاش دولار 💲", amount, tx_number)
        bot.send_message(chat_id, "جار معالجة العملية يرجى الانتظار ⌛️")
        send_deposit_request_to_ola276(dep_id)
        return

    # 10. شحن رصيد البوت عبر شام كاش سوري
    if state == "dep_sham_syp_waiting_tx":
        if not text:
            bot.send_message(chat_id, "يرجى إدخال رقم العملية:", reply_markup=cancel_to_main_keyboard())
            return
        set_user_state(user.id, "dep_sham_syp_waiting_amount", text)
        bot.send_message(chat_id, "أدخل المبلغ المراد شحنه 👇", reply_markup=cancel_to_main_keyboard())
        return

    if state == "dep_sham_syp_waiting_amount":
        try:
            amount = float(text.replace(",", ".").strip())
        except ValueError:
            bot.send_message(chat_id, "❌ يرجى إدخال مبلغ صحيح بالأرقام.", reply_markup=cancel_to_main_keyboard())
            return
        if amount < MIN_SHAM_CASH_SYP_AMOUNT:
            bot.send_message(chat_id, "❌ المبلغ أقل من الحد الأدنى (SYP 200.00).", reply_markup=cancel_to_main_keyboard())
            return
        tx_number = temp_data or ""
        set_user_state(user.id, None, None)
        ensure_user(user)
        dep_id = create_bot_deposit_request(user.id, "شام كاش سوري 💵", amount, tx_number)
        bot.send_message(chat_id, "جار معالجة العملية يرجى الانتظار ⌛️")
        send_deposit_request_to_ola276(dep_id)
        return

    # 11. شحن رصيد البوت عبر سيرياتيل كاش
    if state == "dep_syriatel_waiting_amount":
        try:
            amount = float(text.replace(",", ".").strip())
        except ValueError:
            bot.send_message(chat_id, "❌ يرجى إدخال مبلغ صحيح بالأرقام (الحد الأدنى: 200 ليرة سورية جديدة):", reply_markup=cancel_to_main_keyboard())
            return
        if amount < MIN_SYRIATEL_AMOUNT:
            bot.send_message(chat_id, "❌ المبلغ أقل من الحد الأدنى (200 ليرة سورية جديدة).", reply_markup=cancel_to_main_keyboard())
            return
        amount_str = format_amount(amount)
        set_user_state(user.id, "dep_syriatel_waiting_tx", amount_str)
        bot.send_message(
            chat_id,
            "📱 شحن عبر سيرياتيل كاش\n\n"
            f"المبلغ المطلوب: {amount_str}SYP جديدة\n\n"
            "🔑 الكود السري:\n"
            f"<code>{get_syriatel_code()}</code>\n\n"
            "انتباه:حوّل المبلغ إلى هذا الكود بطريقة التحويل اليدوي.\n"
            "بعد التحويل أرسل رقم العملية هنا.",
            reply_markup=cancel_to_main_keyboard(),
        )
        return

    if state == "dep_syriatel_waiting_tx":
        if not text:
            bot.send_message(chat_id, "يرجى إرسال رقم العملية هنا:", reply_markup=cancel_to_main_keyboard())
            return
        amount = float(temp_data or MIN_SYRIATEL_AMOUNT)
        set_user_state(user.id, None, None)
        ensure_user(user)
        dep_id = create_bot_deposit_request(user.id, "سريتيل كاش 🪙", amount, text)
        bot.send_message(chat_id, "يتم معالجة الامر.... ⏳")
        send_deposit_request_to_ola276(dep_id)
        return

    # 12. إنشاء حساب ichancy
    if state == "ichancy_waiting_username":
        if get_active_ichancy_account(user.id):
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, "لايمكن انشاء حساب أخر لديك حساب مفعل 🌸", reply_markup=ichancy_menu_keyboard())
            return
        if not USERNAME_PATTERN.match(text):
            bot.send_message(
                chat_id,
                "أدخل الاسم بشرط ان لا يقل عن ثماني احرف انجليزيه صغيره وأحرف (بدون رموز )👇",
                reply_markup=cancel_to_main_keyboard(),
            )
            return
        set_user_state(user.id, "ichancy_waiting_password", text)
        bot.send_message(chat_id, "ادخل كلمة المرور لحسابك 👇", reply_markup=cancel_to_main_keyboard())
        return

    if state == "ichancy_waiting_password":
        if get_active_ichancy_account(user.id):
            set_user_state(user.id, None, None)
            bot.send_message(chat_id, "لايمكن انشاء حساب أخر لديك حساب مفعل 🌸", reply_markup=ichancy_menu_keyboard())
            return
        if len(text) < 4:
            bot.send_message(chat_id, "يرجى إدخال كلمة مرور صالحة (4 أحرف أو أرقام على الأقل):\nادخل كلمة المرور لحسابك 👇", reply_markup=cancel_to_main_keyboard())
            return
        acc_username = temp_data or ""
        acc_password = text
        set_user_state(user.id, None, None)
        req_id = create_account_request(user.id, acc_username, acc_password)
        bot.send_message(chat_id, "يتم إنشاء الحساب الاتصال بالخادم ⏳")
        send_request_to_ola276(req_id)
        return

    # 13. الأوامر النصية العامة والاحتفاظ بالتحقق الإجباري
    if text in {"أبدء", "ابدأ"}:
        send_start_response(chat_id, user, remove_reply_kb=False)
    elif text == "رصيدي":
        send_balance_response(chat_id, user)
    elif text in {"لوحة التحكم", "لوحة تحكم"} and is_main_admin(user):
        send_admin_panel(chat_id)
    else:
        first_time = is_first_time_user(user.id)
        ensure_user(user)
        if first_time or not is_user_subscribed(user.id):
            send_force_sub_message(chat_id, is_new_user=first_time)
        else:
            bot.send_message(
                chat_id,
                "اضغط على زر القائمة في الشريط السفلي لاختيار <b>أبدء</b> أو <b>رصيدي</b>.",
            )


def run_bot():
    """تهيئة قاعدة البيانات وتشغيل البوت."""
    init_db()
    bot_info = bot.get_me()
    print(f"Database ready at: {DB_PATH}")
    print(f"Force-sub channel: {get_channel_username()} ({get_channel_url()})")
    print(f"Sole Main Admin: @{ADMIN_USERNAME} (Chat ID: {get_ola276_chat_id()})")
    print(f"Bot running: @{bot_info.username} (ID: {bot_info.id})")
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)


if __name__ == "__main__":
    run_bot()
