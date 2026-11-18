import asyncio
import logging
import os
import re
from datetime import datetime, date
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, BotCommandScopeChat
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# === الإعدادات الأساسية والثوابت ===
TOKEN = "8465308599:AAGCNbkydQq8dztMUl-CBTCvSiC53D_vmMs"
DB_NAME = "ichancy_advanced_bot_v27.db"
ADMIN_ID = 8562347616  # آيدي المسؤول الأساسي

DEFAULT_SYRITEL_QR = "syr_qr.jpg"
DEFAULT_SHAM_SYP_QR = "sham_syp_qr.jpg"
DEFAULT_SHAM_USD_QR = "sham_usd_qr.jpg"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher()

class AccountCreationStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()

class AdminEditStates(StatesGroup):
    editing_username = State()
    editing_password = State()

class BotSyritelDepositStates(StatesGroup):
    waiting_for_trx_id = State()
    waiting_for_amount = State()

class BotShamSypDepositStates(StatesGroup):
    waiting_for_trx_id = State()
    waiting_for_amount = State()

class BotShamUsdDepositStates(StatesGroup):
    waiting_for_trx_id = State()
    waiting_for_amount = State()

class BotWithdrawStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_details = State()

class AccountDepositStates(StatesGroup):
    waiting_for_amount = State()

class AccountWithdrawStates(StatesGroup):
    waiting_for_amount = State()

class AdminBroadcastStates(StatesGroup):
    waiting_for_content = State()

class AdminWelcomeStates(StatesGroup):
    waiting_for_text = State()

class AdminOffersStates(StatesGroup):
    waiting_for_text = State()

class AdminBotNameStates(StatesGroup):
    waiting_for_name = State()

class AdminBotPhotoStates(StatesGroup):
    waiting_for_photo = State()

class AdminEditMsgStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()

class AdminEditDepositPhotoStates(StatesGroup):
    waiting_for_photo = State()

class AdminEditWithdrawMsgStates(StatesGroup):
    waiting_for_text = State()

class AdminManageUserStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_new_balance = State()

class AdminDailyStatsStates(StatesGroup):
    waiting_for_date = State()

class SupportStates(StatesGroup):
    waiting_for_message = State()

class AdminAddSecondaryStates(StatesGroup):
    waiting_for_admin_id = State()

class AdminSearchOpStates(StatesGroup):
    waiting_for_op_number = State()

class AdminCommissionStates(StatesGroup):
    waiting_for_commission_value = State()


async def init_database():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                referred_by INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_agreements (
                user_id INTEGER PRIMARY KEY,
                agreed INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ichancy_accounts (
                user_id INTEGER PRIMARY KEY,
                ichancy_username TEXT,
                ichancy_password TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_acc_requests (
                user_id INTEGER PRIMARY KEY,
                acc_username TEXT,
                acc_password TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_bot_deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                method TEXT,
                trx_id TEXT,
                amount REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_bot_withdraws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                method TEXT,
                amount REAL,
                commission REAL,
                net_amount REAL,
                details TEXT,
                admin_msg_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_acc_deposits (
                user_id INTEGER PRIMARY KEY,
                amount REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_acc_withdraws (
                user_id INTEGER PRIMARY KEY,
                amount REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS financial_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                op_number INTEGER,
                user_id INTEGER,
                action_type TEXT,
                amount REAL,
                currency TEXT,
                created_at DATE DEFAULT (date('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS secondary_admins (
                admin_id INTEGER PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        
        async with aiosqlite.connect(DB_NAME) as db_conn:
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('channel_username', '@ichancynor')")
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('bot_status', 'active')")
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('withdraw_commission', '0')")
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('admin_dispatch_index', '0')")
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('welcome_message', '🤖 البوت الأفضل معك\n\nقبل استخدام بوت ichancy، يرجى قراءة الشروط التالية:\n\n🔹 نطاق الخدمة: البوت مخصّص فقط لـ إنشاء الحسابات والتعبئة والسحب الفوري داخل منصة ichancy.')")
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('active_offers_message', '🎁 **العروض النشطة حالياً:**\n\nلا توجد عروض نشطة في الوقت الحالي. تابعنا دائماً ليصلك كل جديد!')")
            
            default_syritel = "قم بالتحويل الى أحد الارقام بطريقة التحويل اليدوي\n\n0933380467\n\nثم أدخل رقم العملية\n\nالحد الادنى للشحن: SYP 200.00\nيرجى الانتباه الى ان اي مبلغ اقل من الحد الادنى لن تتم معالجته ولا يمكن استرداده"
            default_sham_syp = "658544223c0e72faa9776f6a22cbfeba\n\nالحد الادنى للشحن: SYP 200.00\nيرجى الانتباه الى ان اي مبلغ اقل من الحد الادنى لن تتم معالجته ولا يمكن استرداده"
            default_sham_usd = "658544223c0e72faa9776f6a22cbfeba\n\nالحد الادنى للشحن: USD 1.00\nيرجى الانتباه الى ان اي مبلغ اقل من الحد الادنى لن تتم معالجته ولا يمكن استرداده"
            
            default_wit_syritel = "⬆️ سحب رصيد عبر (سيريتل كاش 🪙):\n\nأدخل معلومات حساب الاستلام ورقم الهاتف مع المبلغ المطلوب."
            default_wit_sham_syp = "⬆️ سحب رصيد عبر (شام كاش سوري 💵):\n\nأدخل معلومات حساب الاستلام أو المعرف الخاص بك."
            default_wit_sham_usd = "⬆️ سحب رصيد عبر (شام كاش دولار 💲):\n\nأدخل تفاصيل محفظة الدولار الخاصة بك."

            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('msg_dep_syritel', ?)", (default_syritel,))
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('msg_dep_sham_syp', ?)", (default_sham_syp,))
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('msg_dep_sham_usd', ?)", (default_sham_usd,))
            
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('msg_wit_syritel', ?)", (default_wit_syritel,))
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('msg_wit_sham_syp', ?)", (default_sham_syp,))
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('msg_wit_sham_usd', ?)", (default_wit_sham_usd,))
            await db_conn.commit()


async def fetch_setting(key: str) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""


async def is_admin(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT admin_id FROM secondary_admins WHERE admin_id = ?", (user_id,)) as cur:
            return await cur.fetchone() is not None


async def get_all_admins() -> list:
    admins = [ADMIN_ID]
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT admin_id FROM secondary_admins") as cur:
            rows = await cur.fetchall()
            for r in rows:
                admins.append(r[0])
    return admins


async def notify_next_admin(text: str, reply_markup=None, photo=None):
    admins = await get_all_admins()
    if not admins:
        return None

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = 'admin_dispatch_index'") as cur:
            row = await cur.fetchone()
            current_idx = int(row[0]) if row else 0

        if current_idx >= len(admins):
            current_idx = 0

        target_admin_id = admins[current_idx]
        next_idx = (current_idx + 1) % len(admins)
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('admin_dispatch_index', ?)", (str(next_idx),))
        await db.commit()

    try:
        if photo:
            sent_msg = await bot.send_photo(chat_id=target_admin_id, photo=photo, caption=text, reply_markup=reply_markup)
        else:
            sent_msg = await bot.send_message(chat_id=target_admin_id, text=text, reply_markup=reply_markup)
        return target_admin_id, sent_msg
    except Exception:
        return target_admin_id, None


@dp.message(Command("admin"))
async def cmd_admin_panel(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if not await is_admin(user_id):
        await message.answer("❌ هذا الأمر خاص بالمشرفين فقط.")
        return

    await message.answer(
        "👑 أهلاً بك في لوحة تحكم المشرف:\n\nاختر أحد الأقسام أدناه للتحكم بالبوت 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ حالة البوت", callback_data="adm_refresh")]
        ])
    )


# Web server for 24/7 uptime
async def handle_ping(request):
    return web.Response(text="Bot is running 24/7 successfully!")

app = web.Application()
app.router.add_get("/", handle_ping)

async def web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server is running on port {port}")


async def main():
    logging.basicConfig(level=logging.INFO)
    await init_database()
    
    async asyncio.create_task(web_server())
    
    print("🤖 جاري تشغيل البوت بنجاح مع سيرفر الويب لتفادي الخمول...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
