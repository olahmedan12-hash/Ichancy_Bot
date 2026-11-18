import asyncio
import logging
import os
import re
from datetime import datetime, date
import aiosqlite
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

# مسارات الصور الافتراضية لوسائل الشحن
DEFAULT_SYRITEL_QR = "syr_qr.jpg"
DEFAULT_SHAM_SYP_QR = "sham_syp_qr.jpg"
DEFAULT_SHAM_USD_QR = "sham_usd_qr.jpg"

# تعريف البوت والـ Dispatcher
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher()

# حالات التفاعل (FSM States)
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


# === تهيئة قاعدة البيانات والجداول ===
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
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('welcome_message', '🤖 البوت الأفضل معك\\n\\nقبل استخدام بوت ichancy، يرجى قراءة الشروط التالية:\\n\\n🔹 نطاق الخدمة: البوت مخصّص فقط لـ إنشاء الحسابات والتعبئة والسحب الفوري داخل منصة ichancy.')")
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('active_offers_message', '🎁 **العروض النشطة حالياً:**\\n\\nلا توجد عروض نشطة في الوقت الحالي. تابعنا دائماً ليصلك كل جديد!')")
            
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
            await db_conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('msg_wit_sham_syp', ?)", (default_wit_sham_syp,))
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


# === نظام توزيع الطلبات بالترتيب بين المشرفين (Round-Robin) ===
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


async def log_financial(op_number: int, user_id: int, action_type: str, amount: float, currency: str = "SYP"):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO financial_logs (op_number, user_id, action_type, amount, currency) VALUES (?, ?, ?, ?, ?)",
            (op_number, user_id, action_type, amount, currency)
        )
        await db.commit()


async def register_user_if_new(user_id: int, username: str, referred_by: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            if not await cursor.fetchone():
                await db.execute(
                    "INSERT INTO users (user_id, username, referred_by) VALUES (?, ?, ?)",
                    (user_id, username, referred_by if referred_by != user_id else None)
                )
                await db.execute("INSERT INTO wallets (user_id, balance) VALUES (?, 0.0)", (user_id,))
                await db.commit()


async def get_user_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM wallets WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0.0


async def verify_subscription(bot_obj: Bot, user_id: int) -> bool:
    channel = await fetch_setting("channel_username")
    try:
        member = await bot_obj.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


def get_next_payout_date() -> str:
    today = date.today()
    day = today.day
    if day <= 10:
        target = date(today.year, today.month, 10)
    elif day <= 20:
        target = date(today.year, today.month, 20)
    else:
        if today.month == 12:
            target = date(today.year + 1, 1, 10)
        else:
            target = date(today.year, today.month + 1, 10)
    return target.strftime("%Y-%m-%d 00:00 (الساعة 12 ليلاً)")


# === لوحة التحكم الرئيسية للمشتركين ===
def get_dashboard_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ichancy⚡ إنشاء حساب", callback_data="menu_ichancy_create")],
        [
            InlineKeyboardButton(text="شحن رصيد في البوت ⬇️", callback_data="bot_deposit"),
            InlineKeyboardButton(text="سحب رصيد من البوت ⬆️", callback_data="bot_withdraw")
        ],
        [
            InlineKeyboardButton(text="شحن رصيد في الحساب 🔽", callback_data="acc_deposit"),
            InlineKeyboardButton(text="سحب رصيد من الحساب 🔼", callback_data="acc_withdraw")
        ],
        [InlineKeyboardButton(text="السجلات 🗃️", callback_data="bot_records")],
        [InlineKeyboardButton(text="التواصل مع الدعم 📩", callback_data="bot_support")],
        [InlineKeyboardButton(text="الإحالات 👪", callback_data="bot_referrals")],
        [InlineKeyboardButton(text="العروض النشطه 🎁", callback_data="bot_offers")],
        [InlineKeyboardButton(text="استرداد آخر طلب سحب ♻️", callback_data="restore_withdraw")]
    ])


# === لوحة تحكم المشرف الرئيسية (Admin Panel) ===
def get_admin_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 إرسال رسالة وصورة للجميع", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="⚙️ تحديد نسبة عمولة السحب (%)", callback_data="adm_set_commission")],
        [InlineKeyboardButton(text="🔄 حالة توزيع الطلبات بين المشرفين", callback_data="adm_dispatch_status")],
        [InlineKeyboardButton(text="🔍 البحث عن معاملة برقمها التسلسلي", callback_data="adm_search_op_prompt")],
        [InlineKeyboardButton(text="✏️ تعديل رسالة الترحيب والشروط", callback_data="adm_edit_welcome")],
        [InlineKeyboardButton(text="🎁 تعديل رسالة العروض النشطة", callback_data="adm_edit_offers")],
        [
            InlineKeyboardButton(text="📝 تعديل رسائل وصور شحن البوت", callback_data="adm_edit_dep_menu"),
        ],
        [
            InlineKeyboardButton(text="📝 تعديل رسائل سحب البوت", callback_data="adm_edit_wit_menu"),
        ],
        [
            InlineKeyboardButton(text="👥 إدارة المشرفين الثانويين", callback_data="adm_manage_secondary"),
        ],
        [
            InlineKeyboardButton(text="✏️ تغيير اسم البوت", callback_data="adm_change_name"),
            InlineKeyboardButton(text="🖼️ تغيير صورة البوت", callback_data="adm_change_photo")
        ],
        [InlineKeyboardButton(text="⚙️ حالة البوت (تشغيل / إيقاف)", callback_data="adm_toggle_bot")],
        [
            InlineKeyboardButton(text="📥 سجل شحن البوت", callback_data="adm_log_bot_dep"),
            InlineKeyboardButton(text="📤 سجل سحب البوت", callback_data="adm_log_bot_wit")
        ],
        [
            InlineKeyboardButton(text="📊 إحصائيات البوت واليوم", callback_data="adm_stats"),
            InlineKeyboardButton(text="📅 سجل شهري مخصص", callback_data="adm_monthly_log")
        ],
        [InlineKeyboardButton(text="👤 إدارة المشتركين (حذف / تعديل رصيد)", callback_data="adm_manage_users")],
        [InlineKeyboardButton(text="🔄 تحديث اللوحة", callback_data="adm_refresh")]
    ])


def get_bot_deposit_methods_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="سريتيل كاش 🪙", callback_data="dep_syritel")],
        [InlineKeyboardButton(text="شام كاش سوري 💵", callback_data="dep_sham_syp")],
        [InlineKeyboardButton(text="شام كاش دولار 💲", callback_data="dep_sham_usd")],
        [InlineKeyboardButton(text="رجوع ♻️", callback_data="back_to_dashboard")]
    ])


def get_bot_withdraw_methods_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="سيريتل كاش 🪙", callback_data="wit_syritel")],
        [InlineKeyboardButton(text="شام كاش سوري 💵", callback_data="wit_sham_syp")],
        [InlineKeyboardButton(text="شام كاش دولار 💲", callback_data="wit_sham_usd")],
        [InlineKeyboardButton(text="رجوع ♻️", callback_data="back_to_dashboard")]
    ])


# === أمر لوحة تحكم المشرف /admin ===
@dp.message(Command("admin"))
async def cmd_admin_panel(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if not await is_admin(user_id):
        await message.answer("❌ هذا الأمر خاص بالمشرفين فقط.")
        return

    await message.answer(
        "👑 أهلاً بك في لوحة تحكم المشرف:\n\nاختر أحد الأقسام أدناه للتحكم بالبوت 👇",
        reply_markup=get_admin_panel_keyboard()
    )


@dp.callback_query(F.data == "adm_refresh")
async def cb_adm_refresh(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    try:
        await callback.message.edit_text(
            "👑 أهلاً بك في لوحة تحكم المشرف:\n\nاختر أحد الأقسام أدناه للتحكم بالبوت 👇",
            reply_markup=get_admin_panel_keyboard()
        )
    except Exception:
        pass
    await callback.answer("تم تحديث اللوحة بنجاح.")


# ========================================================
# === عرض حالة توزيع الطلبات بين المشرفين ===
# ========================================================
@dp.callback_query(F.data == "adm_dispatch_status")
async def cb_adm_dispatch_status(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return

    admins = await get_all_admins()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = 'admin_dispatch_index'") as cur:
            row = await cur.fetchone()
            curr_idx = int(row[0]) if row else 0

    text = f"🔄 **حالة توزيع الطلبات بين المشرفين (بالدور):**\n\n"
    text += f"👥 إجمالي المشرفين في الخدمة: {len(admins)}\n"
    for idx, adm in enumerate(admins):
        marker = " ⬅️ (الطلب القادم سيُرسل له)" if idx == curr_idx else ""
        text += f"• المشرف {idx+1} (`{adm}`){marker}\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع للوحة 🔙", callback_data="adm_refresh")]])
    try:
        await callback.message.edit_text(text, reply_markup=back_kb)
    except Exception:
        pass
    await callback.answer()


# ========================================================
# === قسم تحديد نسبة عمولة السحب من قبل المشرف ===
# ========================================================
@dp.callback_query(F.data == "adm_set_commission")
async def cb_adm_set_commission(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    
    current_comm = await fetch_setting("withdraw_commission")
    await state.set_state(AdminCommissionStates.waiting_for_commission_value)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع للوحة 🔙", callback_data="adm_refresh")]])
    
    try:
        await callback.message.edit_text(
            f"⚙️ **تحديد نسبة عمولة السحب:**\n\n"
            f"النسبة الحالية المفعلة: `{current_comm}%`\n\n"
            f"أرسل الآن النسبة الجديدة المطلوبة (أرقام صحيحة من `1` إلى `50`، أو أرسل `0` لإلغاء العمولة):",
            reply_markup=back_kb
        )
    except Exception:
        pass
    await callback.answer()


@dp.message(AdminCommissionStates.waiting_for_commission_value)
async def process_admin_commission_value(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    
    if not message.text:
        await message.answer("❌ يرجى إرسال قيمة صالحة:")
        return
        
    try:
        comm_val = int(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال أرقام صحيحة فقط (من 1 إلى 50):")
        return

    if not (0 <= comm_val <= 50):
        await message.answer("❌ عذراً، يجب أن تكون نسبة العمولة محددة بين `0%` و `50%` فقط. حاول مجدداً:")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.cursor() as cursor:
            await cursor.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('withdraw_commission', ?)", (str(comm_val),))
        await db.commit()

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="لوحة التحكم الرئيسية 🔙", callback_data="adm_refresh")]])
    await message.answer(f"✅ تم تحديث نسبة عمولة السحب بنجاح لتصبح: `{comm_val}%`", reply_markup=back_kb)
    await state.clear()


# ========================================================
# === قسم البحث برقم العملية للمشرفين ===
# ========================================================
@dp.callback_query(F.data == "adm_search_op_prompt")
async def cb_adm_search_op_prompt(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    
    await state.set_state(AdminSearchOpStates.waiting_for_op_number)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع للوحة 🔙", callback_data="adm_refresh")]])
    
    try:
        await callback.message.edit_text(
            "🔍 **البحث عن معاملة مالية:**\n\nأرسل الآن رقم العملية التسلسلي (مثلاً: `12` أو `150`) للبحث عن تفاصيلها:",
            reply_markup=back_kb
        )
    except Exception:
        pass
    await callback.answer()


@dp.message(AdminSearchOpStates.waiting_for_op_number)
async def process_admin_search_op_number(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    
    if not message.text:
        await message.answer("❌ يرجى إرسال رقم عملية صالح:")
        return
        
    try:
        op_num = int(message.text.strip().replace("#", ""))
    except ValueError:
        await message.answer("❌ يرجى إدخال أرقام صحيحة فقط لرقم العملية:")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT op_number, user_id, action_type, amount, currency, created_at FROM financial_logs WHERE op_number = ?",
            (op_num,)
        ) as cur:
            row = await cur.fetchone()

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="لوحة التحكم الرئيسية 🔙", callback_data="adm_refresh")]])

    if not row:
        await message.answer(
            f"❌ عذراً، لم يتم العثور على أي معاملة مالية تحمل الرقم `#{op_num}`.",
            reply_markup=back_kb
        )
    else:
        op_number, target_uid, action_type, amount, currency, created_at = row
        act_name = "شحن البوت / إيداع" if "deposit" in action_type else "سحب من البوت"
        
        result_text = (
            f"✅ **تم العثور على تفاصيل المعاملة بنجاح:**\n\n"
            f"🔢 رقم العملية: `#{op_number}`\n"
            f"👤 أيدي المشترك: `{target_uid}`\n"
            f"📋 نوع المعاملة: {act_name}\n"
            f"💵 القيمة: {amount} {currency}\n"
            f"📅 تاريخ التسجيل: {created_at}"
        )
        await message.answer(result_text, reply_markup=back_kb)
        
    await state.clear()


# ========================================================
# === قسم إدارة المشرفين الثانويين ===
# ========================================================
@dp.callback_query(F.data == "adm_manage_secondary")
async def cb_adm_manage_secondary(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if user_id != ADMIN_ID:
        await callback.answer("❌ عذراً، هذه الصلاحية مخصصة للمشرف الأساسي فقط!", show_alert=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT admin_id FROM secondary_admins") as cur:
            rows = await cur.fetchall()

    secondary_list = [r[0] for r in rows]
    
    text = "👥 **إدارة المشرفين الثانويين:**\n\n"
    text += f"الحد الأقصى المسموح به: 3 مشرفين ثانويين\n"
    text += f"المشرفين الثانويين الحاليين ({len(secondary_list)}/3):\n"
    
    if not secondary_list:
        text += "• لا يوجد مشرفين ثانويين معينين حالياً.\n"
    else:
        for idx, sec_id in enumerate(secondary_list, 1):
            text += f"{idx}. الآيدي: `{sec_id}`\n"

    kb_buttons = []
    if len(secondary_list) < 3:
        kb_buttons.append([InlineKeyboardButton(text="➕ إضافة مشرف ثانوي", callback_data="adm_add_sec_prompt")])
    
    if secondary_list:
        kb_buttons.append([InlineKeyboardButton(text="🗑️ حذف مشرف ثانوي", callback_data="adm_del_sec_list")])

    kb_buttons.append([InlineKeyboardButton(text="رجوع لوحة المشرف 🔙", callback_data="adm_refresh")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()


@dp.callback_query(F.data == "adm_add_sec_prompt")
async def cb_adm_add_sec_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM secondary_admins") as cur:
            count = (await cur.fetchone())[0]
            if count >= 3:
                await callback.answer("❌ لقد وصلت للحد الأقصى (3 مشرفين ثانويين)!", show_alert=True)
                return

    await state.set_state(AdminAddSecondaryStates.waiting_for_admin_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_manage_secondary")]])
    await callback.message.edit_text(
        "➕ **إضافة مشرف ثانوي جديد:**\n\nأرسل الآن (أيدي User ID) الخاص بالشخص الذي تريد تعيينه مشرفاً ثانوياً:",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(AdminAddSecondaryStates.waiting_for_admin_id)
async def process_add_secondary_admin(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.text:
        await message.answer("❌ يرجى إرسال أيدي صالح:")
        return
    try:
        new_sec_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال أرقام صحيحة فقط للأيدي:")
        return

    if new_sec_id == ADMIN_ID:
        await message.answer("❌ هذا هو أيدي المشرف الأساسي بالفعل!")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM secondary_admins") as cur:
            count = (await cur.fetchone())[0]
            if count >= 3:
                await message.answer("❌ عذراً، تم الوصول للحد الأقصى (3 مشرفين ثانويين).")
                await state.clear()
                return

        async with db.execute("INSERT OR IGNORE INTO secondary_admins (admin_id) VALUES (?)", (new_sec_id,)) as cursor:
            pass
        await db.commit()

    try:
        await bot.send_message(new_sec_id, "🎉 تهانينا! تم تعيينك مشرفاً ثانوياً جديداً في البوت. يمكنك الآن استخدام أمر /admin للوصول للوحة التحكم.")
    except Exception:
        pass

    await message.answer(f"✅ تم إضافة المشرف الثانوي (آيدي: `{new_sec_id}`) بنجاح!", reply_markup=get_admin_panel_keyboard())
    await state.clear()


@dp.callback_query(F.data == "adm_del_sec_list")
async def cb_adm_del_sec_list(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT admin_id FROM secondary_admins") as cur:
            rows = await cur.fetchall()

    if not rows:
        await callback.answer("لا يوجد مشرفين ثانويين للحذف.", show_alert=True)
        return

    kb_buttons = []
    for r in rows:
        s_id = r[0]
        kb_buttons.append([InlineKeyboardButton(text=f"🗑️ حذف المشرف ({s_id})", callback_data=f"adm_rm_sec_{s_id}")])

    kb_buttons.append([InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_manage_secondary")])
    await callback.message.edit_text("🗑️ **اختر المشرف الثانوي المراد إزالته:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await callback.answer()


@dp.callback_query(F.data.startswith("adm_rm_sec_"))
async def cb_adm_rm_sec(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    try:
        sec_id = int(callback.data.split("_")[3])
    except Exception:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM secondary_admins WHERE admin_id = ?", (sec_id,))
        await db.commit()

    try:
        await bot.send_message(sec_id, "⚠️ تم إزالتك من قائمة المشرفين الثانويين في البوت.")
    except Exception:
        pass

    await callback.answer(f"✅ تم حذف المشرف الثانوي ({sec_id}) بنجاح.", show_alert=True)
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT admin_id FROM secondary_admins") as cur:
            rows = await cur.fetchall()

    if not rows:
        await callback.message.edit_text("👥 لا يوجد مشرفين ثانويين حالياً.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_manage_secondary")]]))
        return

    kb_buttons = []
    for r in rows:
        s_id = r[0]
        kb_buttons.append([InlineKeyboardButton(text=f"🗑️ حذف المشرف ({s_id})", callback_data=f"adm_rm_sec_{s_id}")])
    kb_buttons.append([InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_manage_secondary")])
    await callback.message.edit_text("🗑️ **اختر المشرف الثانوي المراد إزالته:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))


# ========================================================
# === قائمة إدارة رسائل سحب البوت ===
# ========================================================
@dp.callback_query(F.data == "adm_edit_wit_menu")
async def cb_adm_edit_wit_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="تعديل نص سحب سيريتل كاش 🪙", callback_data="edit_msg_wit_syr")],
        [InlineKeyboardButton(text="تعديل نص سحب شام كاش سوري 💵", callback_data="edit_msg_wit_sham_syp")],
        [InlineKeyboardButton(text="تعديل نص سحب شام كاش دولار 💲", callback_data="edit_msg_wit_sham_usd")],
        [InlineKeyboardButton(text="رجوع لوحة المشرف 🔙", callback_data="adm_refresh")]
    ])
    await callback.message.edit_text("📝 **اختر وسيلة السحب التي تريد تعديل رسالتها:**", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.in_({"edit_msg_wit_syr", "edit_msg_wit_sham_syp", "edit_msg_wit_sham_usd"}))
async def cb_select_wit_msg_to_edit(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    key_map = {
        "edit_msg_wit_syr": "msg_wit_syritel",
        "edit_msg_wit_sham_syp": "msg_wit_sham_syp",
        "edit_msg_wit_sham_usd": "msg_wit_sham_usd"
    }
    setting_key = key_map.get(callback.data)
    await state.update_data(editing_wit_key=setting_key)
    await state.set_state(AdminEditWithdrawMsgStates.waiting_for_text)

    current_text = await fetch_setting(setting_key)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_edit_wit_menu")]])
    
    await callback.message.edit_text(
        f"✏️ **تعديل نص رسالة السحب الحالي:**\n\n{current_text}\n\nأرسل النص الجديد الآن:",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(AdminEditWithdrawMsgStates.waiting_for_text)
async def process_edited_wit_msg_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    if not message.text:
        await message.answer("❌ يرجى إرسال نص صالح:")
        return

    data = await state.get_data()
    key = data.get("editing_wit_key")
    new_text = message.text.strip()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, new_text))
        await db.commit()

    await message.answer("✅ تم تحديث نص رسالة السحب بنجاح!", reply_markup=get_admin_panel_keyboard())
    await state.clear()


# ========================================================
# === قائمة إدارة رسائل وصور شحن البوت ===
# ========================================================
@dp.callback_query(F.data == "adm_edit_dep_menu")
async def cb_adm_edit_dep_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="تعديل نص سيريتل كاش 🪙", callback_data="edit_msg_syritel")],
        [InlineKeyboardButton(text="🖼️ تغيير صورة سيريتل كاش", callback_data="edit_img_syritel")],
        [InlineKeyboardButton(text="تعديل نص شام كاش سوري 💵", callback_data="edit_msg_sham_syp")],
        [InlineKeyboardButton(text="🖼️ تغيير صورة شام كاش سوري", callback_data="edit_img_sham_syp")],
        [InlineKeyboardButton(text="تعديل نص شام كاش دولار 💲", callback_data="edit_msg_sham_usd")],
        [InlineKeyboardButton(text="🖼️ تغيير صورة شام كاش دولار", callback_data="edit_img_sham_usd")],
        [InlineKeyboardButton(text="رجوع لوحة المشرف 🔙", callback_data="adm_refresh")]
    ])
    await callback.message.edit_text("📝 **اختر ما تريد تعديله لعمليات شحن البوت:**", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.in_({"edit_msg_syritel", "edit_msg_sham_syp", "edit_msg_sham_usd"}))
async def cb_select_msg_to_edit(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    key_map = {
        "edit_msg_syritel": "msg_dep_syritel",
        "edit_msg_sham_syp": "msg_dep_sham_syp",
        "edit_msg_sham_usd": "msg_dep_sham_usd"
    }
    setting_key = key_map.get(callback.data)
    await state.update_data(editing_key=setting_key)
    await state.set_state(AdminEditMsgStates.waiting_for_text)

    current_text = await fetch_setting(setting_key)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_edit_dep_menu")]])
    
    await callback.message.edit_text(
        f"✏️ **تعديل نص الرسالة الحالي:**\n\n{current_text}\n\nأرسل النص الجديد الآن:",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(AdminEditMsgStates.waiting_for_text)
async def process_edited_msg_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    if not message.text:
        await message.answer("❌ يرجى إرسال نص صالح:")
        return

    data = await state.get_data()
    key = data.get("editing_key")
    new_text = message.text.strip()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, new_text))
        await db.commit()

    await message.answer("✅ تم تحديث نص رسالة الشحن بنجاح!", reply_markup=get_admin_panel_keyboard())
    await state.clear()


@dp.callback_query(F.data.in_({"edit_img_syritel", "edit_img_sham_syp", "edit_img_sham_usd"}))
async def cb_select_img_to_edit(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    img_map = {
        "edit_img_syritel": DEFAULT_SYRITEL_QR,
        "edit_img_sham_syp": DEFAULT_SHAM_SYP_QR,
        "edit_img_sham_usd": DEFAULT_SHAM_USD_QR
    }
    target_path = img_map.get(callback.data)
    await state.update_data(target_img_path=target_path)
    await state.set_state(AdminEditDepositPhotoStates.waiting_for_photo)

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_edit_dep_menu")]])
    await callback.message.edit_text(
        "🖼️ **تغيير صورة شحن الحساب:**\n\nأرسل الآن الصورة الجديدة (أو الباركود) ليتم اعتمادها فوراً مع رسالة الشحن:",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(AdminEditDepositPhotoStates.waiting_for_photo, F.photo)
async def process_new_deposit_photo(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    data = await state.get_data()
    path = data.get("target_img_path", DEFAULT_SHAM_SYP_QR)
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        with open(path, "wb") as f:
            f.write(downloaded_file.read())

        await message.answer("✅ تم تحديث صورة وسيلة الشحن بنجاح وتطبيقها للمشتركين!", reply_markup=get_admin_panel_keyboard())
    except Exception as e:
        await message.answer(f"❌ حدث خطأ أثناء حفظ الصورة: {e}", reply_markup=get_admin_panel_keyboard())
    await state.clear()


@dp.message(AdminEditDepositPhotoStates.waiting_for_photo)
async def process_new_deposit_photo_invalid(message: types.Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    await message.answer("❌ يرجى إرسال صورة صحيحة:")


# ========================================================
# === تعديل اسم البوت وصورة البوت ===
# ========================================================
@dp.callback_query(F.data == "adm_change_name")
async def cb_adm_change_name(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    await state.set_state(AdminBotNameStates.waiting_for_name)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_refresh")]])
    await callback.message.edit_text(
        "✏️ **تغيير اسم البوت:**\n\nأرسل الآن الاسم الجديد الذي تريد عرضه للبوت:",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(AdminBotNameStates.waiting_for_name)
async def process_new_bot_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    if not message.text:
        await message.answer("❌ يرجى إرسال اسم صالح:")
        return
    new_name = message.text.strip()
    try:
        await bot.set_my_name(new_name)
        await message.answer(f"✅ تم تغيير اسم البوت بنجاح إلى:\n`{new_name}`", reply_markup=get_admin_panel_keyboard())
    except Exception as e:
        await message.answer(f"❌ حدث خطأ أثناء تغيير اسم البوت عبر تيليجرام:\n{e}", reply_markup=get_admin_panel_keyboard())
    await state.clear()


@dp.callback_query(F.data == "adm_change_photo")
async def cb_adm_change_photo(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    await state.set_state(AdminBotPhotoStates.waiting_for_photo)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_refresh")]])
    await callback.message.edit_text(
        "🖼️ **تغيير الصورة الشخصية للبوت:**\n\nأرسل الآن الصورة الجديدة لتحديث الرمز:",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(AdminBotPhotoStates.waiting_for_photo, F.photo)
async def process_new_bot_photo(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        with open("bot_avatar.jpg", "wb") as f:
            f.write(downloaded_file.read())
        await message.answer("✅ تم استقبال وصور البوت بنجاح وحفظها محلياً!", reply_markup=get_admin_panel_keyboard())
    except Exception as e:
        await message.answer(f"❌ حدث خطأ أثناء حفظ الصورة: {e}", reply_markup=get_admin_panel_keyboard())
    await state.clear()


@dp.message(AdminBotPhotoStates.waiting_for_photo)
async def process_new_bot_photo_invalid(message: types.Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    await message.answer("❌ يرجى إرسال صورة صحيحة:")


# ========================================================
# === زر العروض النشطة للمشتركين ===
# ========================================================
@dp.callback_query(F.data == "bot_offers")
async def cb_bot_offers(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    offers_text = await fetch_setting("active_offers_message")
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع للوحة 🔙", callback_data="back_to_dashboard")]])
    try:
        await callback.message.edit_text(offers_text, reply_markup=back_kb)
    except Exception:
        await callback.message.answer(offers_text, reply_markup=back_kb)
    await callback.answer()


# ========================================================
# === زر استرداد آخر طلب سحب للمشترك (مع إعادة الإجمالي) ===
# ========================================================
@dp.callback_query(F.data == "restore_withdraw")
async def cb_restore_withdraw(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, amount, admin_msg_id FROM pending_bot_withdraws WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()

    if not row:
        await callback.answer("❌ ليس لديك أي طلب سحب معلق ليتم استرداده.", show_alert=True)
        return

    wit_id, amount, admin_msg_id = row

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE wallets SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.execute("DELETE FROM pending_bot_withdraws WHERE user_id = ?", (user_id,))
        await db.commit()

    if admin_msg_id:
        try:
            admins = await get_all_admins()
            for adm_id in admins:
                try:
                    await bot.delete_message(chat_id=adm_id, message_id=admin_msg_id)
                except Exception:
                    pass
        except Exception:
            pass

    new_balance = await get_user_balance(user_id)
    await callback.answer(f"✅ تم إلغاء طلب السحب واسترداد مبلغ {amount} SYP إلى رصيدك بالكامل بنجاح!", show_alert=True)
    
    try:
        await callback.message.edit_text(
            f"♻️ **تم استرداد طلب السحب بنجاح:**\n\n"
            f"🔢 رقم عملية السحب الملغاة: `#{wit_id}`\n"
            f"💵 المبلغ المسترد بالكامل: `{amount}` SYP\n"
            f"💳 رصيدك الحالي في البوت: `{new_balance}` SYP",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="القائمة الرئيسية 🏠", callback_data="back_to_dashboard")]])
        )
    except Exception:
        pass


# ========================================================
# === تعديل رسالة العروض النشطة ===
# ========================================================
@dp.callback_query(F.data == "adm_edit_offers")
async def cb_adm_edit_offers(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    current_text = await fetch_setting("active_offers_message")
    await state.set_state(AdminOffersStates.waiting_for_text)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_refresh")]])
    await callback.message.edit_text(
        f"🎁 **تعديل رسالة العروض النشطة:**\n\n"
        f"النص الحالي:\n{current_text}\n\n"
        f"أرسل النص الجديد الآن لتحديثه:",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(AdminOffersStates.waiting_for_text)
async def process_new_offers_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    if not message.text:
        await message.answer("❌ يرجى إرسال نص صالح:")
        return
    new_text = message.text.strip()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('active_offers_message', ?)", (new_text,))
        await db.commit()

    await message.answer("✅ تم تحديث رسالة العروض النشطة بنجاح!", reply_markup=get_admin_panel_keyboard())
    await state.clear()


# ========================================================
# === قسم السجلات الخاصة بالمشترك ===
# ========================================================
@dp.callback_query(F.data == "bot_records")
async def cb_bot_records(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT op_number, action_type, amount, currency, created_at FROM financial_logs WHERE user_id = ? ORDER BY id DESC LIMIT 20",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()

    text = "🗃️ **سجل عمليات السحب والإيداع الخاصة بك:**\n\n"
    if not rows:
        text += "لا توجد أي عمليات مالية مسجلة لحسابك حتى الآن."
    else:
        for r in rows:
            op_num = r[0] or 1
            act_name = "إيداع للبوت" if "deposit" in r[1] else "سحب من البوت"
            text += f"🔹 رقم العملية: `#{op_num}` | النوع: {act_name} | القيمة: {r[2]} {r[3]} | التاريخ: {r[4]}\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع للوحة 🔙", callback_data="back_to_dashboard")]])
    try:
        await callback.message.edit_text(text, reply_markup=back_kb)
    except Exception:
        await callback.message.answer(text, reply_markup=back_kb)
    await callback.answer()


# ========================================================
# === قسم التواصل مع الدعم ===
# ========================================================
@dp.callback_query(F.data == "bot_support")
async def cb_bot_support(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_message)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="back_to_dashboard")]])
    await callback.message.edit_text(
        "اكتب هنا او ارسل صوره سيتم ارسال رسالتك الى الاداره والرد في اقرب وقت ممكن 📩",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(SupportStates.waiting_for_message)
async def process_support_message(message: types.Message, state: FSMContext):
    user = message.from_user
    bot_balance = await get_user_balance(user.id)

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ رد على المشترك", callback_data=f"support_reply_{user.id}")]
    ])

    support_caption = (
        f"📩 **رسالة دعم جديدة من مشترك:**\n\n"
        f"👤 المشترك: @{user.username or 'بدون'} ({user.id})\n"
        f"💳 رصيد المشترك الحالي في البوت: {bot_balance} SYP\n\n"
        f"💬 النص: {message.text or message.caption or 'مرفق صورة'}"
    )

    try:
        if message.photo:
            await notify_next_admin(photo=message.photo[-1].file_id, text=support_caption, reply_markup=admin_kb)
        else:
            await notify_next_admin(text=support_caption, reply_markup=admin_kb)
        
        await message.answer("✅ تم إرسال رسالتك إلى الإدارة بنجاح وسيتم الرد عليك في أقرب وقت ممكن.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="القائمة الرئيسية 🏠", callback_data="back_to_dashboard")]]))
    except Exception:
        await message.answer("❌ حدث خطأ أثناء إرسال الرسالة للإدارة. حاول مجدداً.")

    await state.clear()


# ========================================================
# === قسم الإحالات ===
# ========================================================
@dp.callback_query(F.data == "bot_referrals")
async def cb_bot_referrals(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as cur:
            ref_count = (await cur.fetchone())[0]

    payout_date = get_next_payout_date()

    referral_text = (
        "نظام احالات \n\n"
        "يقدّم لك فرصة لدخل إضافي كل 10 أيام .\n"
        "كن وكيلاً معنا بأبسط طريقة\n"
        "إحصل على نسبة ثابتة لكل عمليات الشحن والتعبئة القادمة عن طريق رابط احالتك ضمن البوت \n"
        ".....\n"
        "1-عند الدخول الى البوت قم بنسخ رابط الاحالة الخاص بك عن طريق الضغط على خيار رابط الاحالة الخاص بي\n"
        "2- عندما تقوم بنشر رابط احالتك ويقوم أحد بالتسجيل عن طريقة سنبدأ بحساب نسبة ثابتة لجميع عمليات السحب والتعبئة عن طريقك . \n"
        "3-يمكن الاطلاع على عدد الاحالات التي قامت بالتسجيل من خلال الرابط الخاص بك عن طريق الضغط على خيار عدد الاحالات الخاصة بك خلال المسابقة الحالية \n"
        "4- يتم حساب الارباح عند وجود 3 إحالات نشطة او أكثر\n"
        "ماذا تنتظر...! \n"
        "توزيع النسب كل 10 أيام\n\n"
        f"عدد الاحالات التابعة لك: {ref_count}\n\n"
        f"رابط الإحالة الخاص بك:\n{ref_link}\n\n"
        f"الموعد القادم لتوزيع الاحالات:\n{payout_date}"
    )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="back_to_dashboard")]])
    try:
        await callback.message.edit_text(referral_text, reply_markup=back_kb)
    except Exception:
        await callback.message.answer(referral_text, reply_markup=back_kb)
    await callback.answer()


# ========================================================
# === 1. زر إرسال رسالة وصورة للجميع (Broadcast مُحسن لـ 20k) ===
# ========================================================
@dp.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    await state.set_state(AdminBroadcastStates.waiting_for_content)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع للوحة المشرف 🔙", callback_data="adm_refresh")]])
    await callback.message.edit_text(
        "📢 إذاعة عامة للمشتركين (مُحسنة لـ 20 ألف مشترك):\n\nأرسل الآن الرسالة أو الصورة ليتم بثها تدريجياً وبشكل آمن:",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(AdminBroadcastStates.waiting_for_content)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            users = [row[0] for row in await cur.fetchall()]

    sent_count = 0
    fail_count = 0
    total_users = len(users)

    status_msg = await message.answer(f"⏳ جاري بدء الإذاعة لـ {total_users} مشترك بشكل آمن ومنتظم...")

    for index, uid in enumerate(users):
        try:
            if message.photo:
                await bot.send_photo(chat_id=uid, photo=message.photo[-1].file_id, caption=message.caption or "")
            else:
                await bot.send_message(chat_id=uid, text=message.text)
            sent_count += 1
        except Exception:
            fail_count += 1
        
        await asyncio.sleep(0.05)

        if index > 0 and index % 500 == 0:
            try:
                await status_msg.edit_text(f"⏳ جاري الإذاعة... تم إرسالها إلى ({index} / {total_users}) مشترك.")
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ تمت الإذاعة العامة بنجاح تام!\n\n"
        f"👥 إجمالي المستهدفين: {total_users}\n"
        f"📨 عدد المستلمين بنجاح: {sent_count}\n"
        f"❌ عدد الحسابات الوهمية أو المحظورة للبوت: {fail_count}"
    )
    await state.clear()


# ========================================================
# === 2. زر تعديل رسالة الترحيب والشروط ===
# ========================================================
@dp.callback_query(F.data == "adm_edit_welcome")
async def cb_adm_edit_welcome(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    current_text = await fetch_setting("welcome_message")
    await state.set_state(AdminWelcomeStates.waiting_for_text)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_refresh")]])
    await callback.message.edit_text(
        f"✏️ تعديل رسالة الترحيب الحالية:\n\nالنص الحالي:\n{current_text}\n\nأرسل النص الجديد الآن لتبديله:",
        reply_markup=back_kb
    )
    await callback.answer()


@dp.message(AdminWelcomeStates.waiting_for_text)
async def process_new_welcome_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    if not message.text:
        await message.answer("❌ يرجى إرسال نص صالح:")
        return
    new_text = message.text.strip()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('welcome_message', ?)", (new_text,))
        await db.commit()

    await message.answer("✅ تم تحديث رسالة الترحيب بنجاح!", reply_markup=get_admin_panel_keyboard())
    await state.clear()


# ========================================================
# === 3. زر التحكم بحالة البوت ===
# ========================================================
@dp.callback_query(F.data == "adm_toggle_bot")
async def cb_adm_toggle_bot(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    current_status = await fetch_setting("bot_status")
    new_status = "stopped" if current_status == "active" else "active"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('bot_status', ?)", (new_status,))
        await db.commit()

    status_text = "🟢 البوت يعمل الآن بشكل طبيعي." if new_status == "active" else "🔴 تم إيقاف استقبال طلبات البوت مؤقتاً."
    await callback.answer(status_text, show_alert=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=get_admin_panel_keyboard())
    except Exception:
        pass


# ========================================================
# === 4. سجلات العمليات والإحصائيات ===
# ========================================================
@dp.callback_query(F.data.in_({"adm_log_bot_dep", "adm_log_bot_wit"}))
async def cb_adm_financial_logs(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    action_filter = "bot_deposit" if callback.data == "adm_log_bot_dep" else "bot_withdraw"
    title = "📥 سجل عمليات شحن البوت" if action_filter == "bot_deposit" else "📤 سجل عمليات سحب البوت"

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT op_number, user_id, amount, currency, created_at FROM financial_logs WHERE action_type = ? ORDER BY id DESC LIMIT 15",
            (action_filter,)
        ) as cur:
            rows = await cur.fetchall()

    log_text = f"📋 {title} (آخر 15 عملية):\n\n"
    if not rows:
        log_text += "لا توجد سجلات مالية حتى الآن."
    else:
        for r in rows:
            op_num = r[0] or 1
            log_text += f"🔢 رقم العملية: `#{op_num}` | المشترك: `{r[1]}` | 💵 القيمة: {r[2]} {r[3]} | 📅 التاريخ: {r[4]}\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع للوحة التحكم 🔙", callback_data="adm_refresh")]])
    try:
        await callback.message.edit_text(log_text, reply_markup=back_kb)
    except Exception:
        await callback.message.answer(log_text, reply_markup=back_kb)
    await callback.answer()


@dp.callback_query(F.data == "adm_stats")
async def cb_adm_stats(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    today_str = str(date.today())

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]

        async with db.execute("SELECT SUM(amount) FROM financial_logs WHERE action_type = 'bot_deposit' AND created_at = ?", (today_str,)) as cur:
            row = await cur.fetchone()
            today_dep = row[0] if row and row[0] else 0.0

        async with db.execute("SELECT SUM(amount) FROM financial_logs WHERE action_type = 'bot_withdraw' AND created_at = ?", (today_str,)) as cur:
            row = await cur.fetchone()
            today_wit = row[0] if row and row[0] else 0.0

    stats_text = (
        f"📊 إحصائيات البوت الشاملة:\n\n"
        f"👥 إجمالي عدد اللاعبين المشتركين: {total_users} مشترِك\n\n"
        f"📅 إحصائيات اليوم ({today_str}):\n"
        f"📥 إجمالي الإيداعات اليومية: {today_dep} SYP\n"
        f"📤 إجمالي السحوبات اليومية: {today_wit} SYP"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_refresh")]])
    try:
        await callback.message.edit_text(stats_text, reply_markup=back_kb)
    except Exception:
        await callback.message.answer(stats_text, reply_markup=back_kb)
    await callback.answer()


@dp.callback_query(F.data == "adm_monthly_log")
async def cb_adm_monthly_log(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    await state.set_state(AdminDailyStatsStates.waiting_for_date)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_refresh")]])
    try:
        await callback.message.edit_text(
            "📅 السجل الشهري المخصص:\n\nأدخل التاريخ بالصيغة التالية (السنة-الشهر-اليوم) مثال: 2026-11-16 لعرض تفاصيل الإيداع والسحب لذلك اليوم:",
            reply_markup=back_kb
        )
    except Exception:
        pass
    await callback.answer()


@dp.message(AdminDailyStatsStates.waiting_for_date)
async def process_monthly_log_date(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    if not message.text:
        await message.answer("❌ يرجى إدخال تاريخ صالح:")
        return
    target_date = message.text.strip()

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT action_type, SUM(amount), currency FROM financial_logs WHERE created_at = ? GROUP BY action_type, currency", (target_date,)) as cur:
            rows = await cur.fetchall()

    result_text = f"📅 تقرير يوم: {target_date}\n\n"
    if not rows:
        result_text += "لا توجد أي تحويلات مالية مسجلة في هذا التاريخ."
    else:
        for r in rows:
            act_name = "شحن البوت / إيداع" if r[0] == "bot_deposit" else "سحب البوت"
            result_text += f"🔹 {act_name}: {r[1]} {r[2]}\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="لوحة التحكم الرئيسية 🔙", callback_data="adm_refresh")]])
    await message.answer(result_text, reply_markup=back_kb)
    await state.clear()


# ========================================================
# === 5. زر إدارة المشتركين ===
# ========================================================
@dp.callback_query(F.data == "adm_manage_users")
async def cb_adm_manage_users(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return
    await state.set_state(AdminManageUserStates.waiting_for_user_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع 🔙", callback_data="adm_refresh")]])
    try:
        await callback.message.edit_text(
            "👤 إدارة المشتركين:\n\nأدخل أيدي (User ID) المشترك المراد التحكم به:",
            reply_markup=back_kb
        )
    except Exception:
        pass
    await callback.answer()


@dp.message(AdminManageUserStates.waiting_for_user_id)
async def process_manage_user_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return
    if not message.text:
        await message.answer("❌ يرجى إدخال أيدي صحيح:")
        return
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال أيدي صحيح (أرقام فقط):")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM wallets WHERE user_id = ?", (target_id,)) as cur:
            w_row = await cur.fetchone()
        async with db.execute("SELECT ichancy_username, ichancy_password FROM ichancy_accounts WHERE user_id = ?", (target_id,)) as cur:
            acc_row = await cur.fetchone()

    if not w_row:
        await message.answer("❌ عذراً، هذا المستخدم غير مسجل في قاعدة بيانات البوت.")
        await state.clear()
        return

    balance = w_row[0]
    acc_info = f"اسم المستخدم: {acc_row[0]}" if acc_row else "لا يملك حساب ichancy مفعّل"

    await state.update_data(target_user_id=target_id)

    manage_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 تعديل رصيد المشترك في البوت", callback_data=f"adm_set_bal_{target_id}")],
        [InlineKeyboardButton(text="🗑️ حذف حساب المنصة المرتبط", callback_data=f"adm_del_acc_{target_id}")],
        [InlineKeyboardButton(text="❌ حذف المشترك نهائياً من البوت", callback_data=f"adm_del_usr_{target_id}")],
        [InlineKeyboardButton(text="رجوع للوحة التحكم 🔙", callback_data="adm_refresh")]
    ])

    await message.answer(
        f"👤 معلومات المشترك ({target_id}):\n\n💳 رصيد البوت الحالي: {balance} SYP\n🏷️ حساب المنصة: {acc_info}\n\nاختر الإجراء المطلوب تنفيذه:",
        reply_markup=manage_kb
    )


@dp.callback_query(F.data.startswith("adm_set_bal_"))
async def cb_adm_set_balance_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[3])
    await state.update_data(target_user_id=uid)
    await state.set_state(AdminManageUserStates.waiting_for_new_balance)
    await callback.message.answer(f"أدخل المبلغ الجديد لرصيد المشترك ({uid}):")
    await callback.answer()


@dp.message(AdminManageUserStates.waiting_for_new_balance)
async def process_new_user_balance(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if not message.text:
        await message.answer("❌ يرجى إدخال مبلغ صحيح:")
        return
    try:
        new_bal = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح:")
        return

    data = await state.get_data()
    uid = data.get("target_user_id")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE wallets SET balance = ? WHERE user_id = ?", (new_bal, uid))
        await db.commit()

    await message.answer(f"✅ تم تحديث رصيد المشترك ({uid}) ليصبح: {new_bal} SYP", reply_markup=get_admin_panel_keyboard())
    await state.clear()


@dp.callback_query(F.data.startswith("adm_del_acc_"))
async def cb_adm_delete_account(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[3])
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM ichancy_accounts WHERE user_id = ?", (uid,))
        await db.commit()
    await callback.answer(f"✅ تم حذف حساب المنصة للمشترك {uid} بنجاح.", show_alert=True)


@dp.callback_query(F.data.startswith("adm_del_usr_"))
async def cb_adm_delete_user(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[3])
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM wallets WHERE user_id = ?", (uid,))
        await db.execute("DELETE FROM ichancy_accounts WHERE user_id = ?", (uid,))
        await db.commit()
    await callback.answer(f"✅ تم حذف المشترك {uid} من البوت نهائياً.", show_alert=True)


# ========================================================
# === سحب رصيد من الحساب 🔼 ===
# ========================================================
@dp.callback_query(F.data == "acc_withdraw")
async def cb_acc_withdraw_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT ichancy_username FROM ichancy_accounts WHERE user_id = ?", (user_id,)) as cur:
            if not await cur.fetchone():
                await callback.answer("❌ يجب عليك إنشاء حساب ichancy أولاً.", show_alert=True)
                return

        async with db.execute("SELECT amount FROM pending_acc_withdraws WHERE user_id = ?", (user_id,)) as cur:
            if await cur.fetchone():
                await callback.answer("⚠️ لديك طلب سحب رصيد من الحساب قيد المراجعة لدى الإدارة بالفعل!", show_alert=True)
                return

    await state.set_state(AccountWithdrawStates.waiting_for_amount)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع ♻️", callback_data="back_to_dashboard")]])
    
    text = "ادخل المبلغ المراد سحبه من حسابك 👇"
    try:
        await callback.message.edit_text(text, reply_markup=back_kb)
    except Exception:
        pass
    await callback.answer()


@dp.message(AccountWithdrawStates.waiting_for_amount)
async def process_acc_withdraw_amount(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال مبلغ صالح:")
        return
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للمبلغ المراد سحبه:")
        return

    if amount < 200.0:
        await message.answer("❌ الحد الأدنى لسحب رصيد الحساب هو 200 SYP. يرجى إدخال مبلغ صالح:")
        return

    user = message.from_user
    bot_balance = await get_user_balance(user.id)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO pending_acc_withdraws (user_id, amount) VALUES (?, ?)",
            (user.id, amount)
        )
        await db.commit()

    await message.answer("جاري السحب والاتصال بالخوادم .⏳")

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة", callback_data=f"aw_yes_{user.id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"aw_no_{user.id}")
        ]
    ])

    await notify_next_admin(
        f"📥 طلب سحب رصيد من الحساب (إلى رصيد البوت):\n\n"
        f"👤 المشترك: @{user.username or 'بدون'} ({user.id})\n"
        f"💵 المبلغ المراد سحبه من حساب اللاعب: {amount} SYP\n"
        f"💳 رصيد المشترك الحالي في البوت: {bot_balance} SYP",
        reply_markup=admin_kb
    )

    await state.clear()


@dp.callback_query(F.data.startswith("aw_yes_") | F.data.startswith("aw_no_"))
async def admin_acc_withdraw_decision(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_admin(callback.from_user.id):
        return
    data_parts = callback.data.split("_")
    if len(data_parts) >= 3:
        action = data_parts[1]
        uid = int(data_parts[2])
    else:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT amount FROM pending_acc_withdraws WHERE user_id = ?", (uid,)) as cur:
            row = await cur.fetchone()
        
        await db.execute("DELETE FROM pending_acc_withdraws WHERE user_id = ?", (uid,))
        await db.commit()

    if action == "yes":
        if row:
            amount = row[0]
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("INSERT OR IGNORE INTO wallets (user_id, balance) VALUES (?, 0.0)", (uid,))
                await db.execute("UPDATE wallets SET balance = balance + ? WHERE user_id = ?", (amount, uid))
                await db.commit()

            await log_financial(1, uid, "bot_deposit", amount, "SYP")
            new_balance = await get_user_balance(uid)

            try:
                await bot.send_message(
                    uid,
                    f"تم شحن حسابك بنجاح✅\n\nالمبلغ المشحون: {amount} SYP\nرصيد البوت الجديد: {new_balance} SYP"
                )
            except Exception:
                pass
            try:
                await callback.message.edit_text(callback.message.text + "\n\n✅ تمت الموافقة وإضافة المبلغ إلى رصيد البوت للمشترك.")
            except Exception:
                pass
        else:
            await callback.answer("❌ البيانات غير موجودة أو تم التعامل معها مسبقاً.", show_alert=True)
    else:
        try:
            await bot.send_message(uid, "تم رفض المعالجة لعدم توفر رصيد كافي 🔴")
        except Exception:
            pass
        try:
            await callback.message.edit_text(callback.message.text + "\n\n❌ تم رفض الطلب من قبل الإدارة.")
        except Exception:
            pass

    await callback.answer()


# ========================================================
# === سحب رصيد من البوت ⬆️ (مع احتساب واقتطاع العمولة تلقائياً) ===
# ========================================================
@dp.callback_query(F.data == "bot_withdraw")
async def cb_bot_withdraw_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    balance = await get_user_balance(user_id)

    if balance <= 0:
        await callback.answer("❌ عذراً، رصيدك الحالي في البوت فارغ (0 SYP) ولا يمكنك إجراء عملية سحب.", show_alert=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM pending_bot_withdraws WHERE user_id = ?", (user_id,)) as cur:
            if await cur.fetchone():
                await callback.answer("⚠️ لديك طلب سحب معلق بالفعل! يمكنك إلغاؤه عبر زر 'استرداد آخر طلب سحب'.", show_alert=True)
                return

    await callback.message.edit_text(
        "اختر احد طرق السحب المتاحه 👇",
        reply_markup=get_bot_withdraw_methods_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.in_({"wit_syritel", "wit_sham_syp", "wit_sham_usd"}))
async def cb_withdraw_method_selected(callback: types.CallbackQuery, state: FSMContext):
    method_map = {
        "wit_syritel": "سيريتل كاش 🪙",
        "wit_sham_syp": "شام كاش سوري 💵",
        "wit_sham_usd": "شام كاش دولار 💲"
    }
    key_setting_map = {
        "wit_syritel": "msg_wit_syritel",
        "wit_sham_syp": "msg_wit_sham_syp",
        "wit_sham_usd": "msg_wit_sham_usd"
    }
    selected_method = method_map.get(callback.data)
    setting_key = key_setting_map.get(callback.data)
    
    await state.update_data(withdraw_method=selected_method)
    await state.set_state(BotWithdrawStates.waiting_for_amount)

    user_id = callback.from_user.id
    balance = await get_user_balance(user_id)

    custom_msg = await fetch_setting(setting_key)
    comm_rate = float(await fetch_setting("withdraw_commission") or 0)

    text = (
        f"{custom_msg}\n\n"
        f"💳 رصيدك المتاح: {balance} SYP\n"
        f"⚠️ نسبة عمولة السحب الحالية: {comm_rate}%\n\n"
        f"أدخل المبلغ المراد سحبه 👇"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع ♻️", callback_data="bot_withdraw")]])
    try:
        await callback.message.edit_text(text, reply_markup=back_kb)
    except Exception:
        pass
    await callback.answer()


@dp.message(BotWithdrawStates.waiting_for_amount)
async def process_withdraw_amount(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال مبلغ صالح:")
        return
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للمبلغ المراد سحبه:")
        return

    user_id = message.from_user.id
    balance = await get_user_balance(user_id)

    if amount <= 0:
        await message.answer("❌ يجب أن يكون المبلغ أكبر من صفر:")
        return

    if amount > balance:
        await message.answer(f"❌ عذراً، المبلغ المطلوب ({amount}) أكبر من رصيدك الحالي ({balance} SYP). أدخل مبلغاً مناسباً:")
        return

    await state.update_data(withdraw_amount=amount)
    await state.set_state(BotWithdrawStates.waiting_for_details)
    await message.answer("📝 أدخل معلومات وحساب الاستلام (مثل رقم الحساب أو رقم الهاتف):")


@dp.message(BotWithdrawStates.waiting_for_details)
async def process_withdraw_details(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال تفاصيل صالحة:")
        return
    details = message.text.strip()
    data = await state.get_data()
    amount = data.get("withdraw_amount")
    method = data.get("withdraw_method")
    user = message.from_user
    bot_balance = await get_user_balance(user.id)

    comm_rate = float(await fetch_setting("withdraw_commission") or 0)
    commission = (amount * comm_rate) / 100.0
    net_amount = amount - commission

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE wallets SET balance = balance - ? WHERE user_id = ?", (amount, user.id))
        
        cursor = await db.execute(
            "INSERT INTO pending_bot_withdraws (user_id, method, amount, commission, net_amount, details) VALUES (?, ?, ?, ?, ?, ?)",
            (user.id, method, amount, commission, net_amount, details)
        )
        wit_id = cursor.lastrowid
        await db.commit()

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة", callback_data=f"bw_yes_{wit_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"bw_no_{wit_id}")
        ]
    ])

    admin_text = (
        f"📤 **طلب سحب رصيد بوت جديد (#`{wit_id}`):**\n\n"
        f"👤 صاحب الطلب: @{user.username or 'بدون'} (`{user.id}`)\n"
        f"💳 طريقة السحب: {method}\n"
        f"💵 المبلغ المطلوب (الإجمالي): {amount} SYP\n"
        f"📊 نسبة العمولة: {comm_rate}%\n"
        f"✂️ قيمة العمولة المقتطعة: {commission} SYP\n"
        f"💰 المبلغ الصافي (للمشترك): **{net_amount} SYP**\n"
        f"💳 رصيد المشترك الحالي في البوت بعد الخصم: {bot_balance - amount} SYP\n"
        f"📋 معلومات الحساب: {details}"
    )

    _, sent_msg = await notify_next_admin(text=admin_text, reply_markup=admin_kb)

    if sent_msg:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE pending_bot_withdraws SET admin_msg_id = ? WHERE id = ?", (sent_msg.message_id, wit_id))
            await db.commit()

    await message.answer(f"⏳ جاري معالجة طلب السحب برقم `#{wit_id}` وإرساله للإدارة.\n\n📊 نسبة العمولة المطبقة: {comm_rate}%\n✂️ قيمة العمولة: {commission} SYP\n💰 الصافي الذي ستستلمه: {net_amount} SYP")
    await state.clear()


@dp.callback_query(F.data.startswith("bw_yes_") | F.data.startswith("bw_no_"))
async def admin_bot_withdraw_decision(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_admin(callback.from_user.id):
        return
    data_parts = callback.data.split("_")
    if len(data_parts) >= 3:
        action = data_parts[1]
        wit_id = int(data_parts[2])
    else:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, method, amount, commission, net_amount, details FROM pending_bot_withdraws WHERE id = ?", (wit_id,)) as cur:
            row = await cur.fetchone()
        
        await db.execute("DELETE FROM pending_bot_withdraws WHERE id = ?", (wit_id,))
        await db.commit()

    if action == "yes":
        if row:
            uid, method, amount, commission, net_amount, details = row
            await log_financial(wit_id, uid, "bot_withdraw", net_amount, "SYP")
            new_balance = await get_user_balance(uid)

            try:
                await bot.send_message(
                    uid,
                    f"تم تنفيذ طلب سحب الرصيد رقم `#{wit_id}` بنجاح ✅\n\n"
                    f"💳 الطريقة: {method}\n"
                    f"💵 المبلغ الإجمالي: {amount} SYP\n"
                    f"✂️ عمولة البوت: {commission} SYP\n"
                    f"💰 المبلغ الصافي المستلم: **{net_amount} SYP**\n"
                    f"💳 رصيد البوت المتبقي لديك: {new_balance} SYP"
                )
            except Exception:
                pass
            try:
                await callback.message.edit_text(callback.message.text + f"\n\n✅ تمت الموافقة على السحب رقم `#{wit_id}` وإرسال الصافي للمشترك.")
            except Exception:
                pass
        else:
            await callback.answer("❌ البيانات غير موجودة أو تم التعامل معها مسبقاً.", show_alert=True)
    else:
        if row:
            uid, amount = row[0], row[2]
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE wallets SET balance = balance + ? WHERE user_id = ?", (amount, uid))
                await db.commit()

            try:
                await bot.send_message(
                    uid,
                    f"❌ عذراً، تم رفض طلب سحب الرصيد رقم `#{wit_id}` من قبل الإدارة وإعادة المبلغ الإجمالي ({amount} SYP) إلى رصيدك بالكامل."
                )
            except Exception:
                pass
        try:
            await callback.message.edit_text(callback.message.text + f"\n\n❌ تم رفض طلب السحب رقم `#{wit_id}` وإعادة المبلغ بالكامل للمشترك.")
        except Exception:
            pass

    await callback.answer()


# ========================================================
# === شحن الحساب والبوت والإنشاء ===
# ========================================================
@dp.callback_query(F.data == "acc_deposit")
async def cb_acc_deposit_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT ichancy_username FROM ichancy_accounts WHERE user_id = ?", (user_id,)) as cur:
            if not await cur.fetchone():
                await callback.answer("❌ يجب عليك إنشاء حساب ichancy أولاً قبل محاولة الشحن إليه.", show_alert=True)
                return

        async with db.execute("SELECT amount FROM pending_acc_deposits WHERE user_id = ?", (user_id,)) as cur:
            if await cur.fetchone():
                await callback.answer("⚠️ لديك طلب شحن حساب قيد المراجعة لدى الإدارة بالفعل!", show_alert=True)
                return

    await state.set_state(AccountDepositStates.waiting_for_amount)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع ♻️", callback_data="back_to_dashboard")]])
    
    text = "ادخل المبلغ المراد شحنه في حسابك 👇"
    try:
        await callback.message.edit_text(text, reply_markup=back_kb)
    except Exception:
        pass
    await callback.answer()


@dp.message(AccountDepositStates.waiting_for_amount)
async def process_acc_deposit_amount(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال مبلغ صالح:")
        return
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للمبلغ المراد شحنه:")
        return

    if amount < 200.0:
        await message.answer("❌ الحد الأدنى لشحن الحساب هو 200 SYP. يرجى إدخال مبلغ صالح:")
        return

    user = message.from_user
    bot_balance = await get_user_balance(user.id)

    if amount > bot_balance:
        await message.answer("تم رفض المعالجة لعدم توفر رصيد كافي 🔴")
        await state.clear()
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO pending_acc_deposits (user_id, amount) VALUES (?, ?)",
            (user.id, amount)
        )
        await db.commit()

    await message.answer("جاري التحويل والاتصال بالخوادم .⏳")

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة", callback_data=f"ad_yes_{user.id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"ad_no_{user.id}")
        ]
    ])

    await notify_next_admin(
        f"📥 طلب شحن رصيد الحساب:\n\n"
        f"👤 المشترك: @{user.username or 'بدون'} ({user.id})\n"
        f"💵 المبلغ المراد تحويله لحساب اللاعب: {amount} SYP\n"
        f"💳 رصيد المشترك الحالي في البوت: {bot_balance} SYP",
        reply_markup=admin_kb
    )

    await state.clear()


@dp.callback_query(F.data.startswith("ad_yes_") | F.data.startswith("ad_no_"))
async def admin_acc_deposit_decision(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_admin(callback.from_user.id):
        return
    data_parts = callback.data.split("_")
    if len(data_parts) >= 3:
        action = data_parts[1]
        uid = int(data_parts[2])
    else:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT amount FROM pending_acc_deposits WHERE user_id = ?", (uid,)) as cur:
            row = await cur.fetchone()
        
        await db.execute("DELETE FROM pending_acc_deposits WHERE user_id = ?", (uid,))
        await db.commit()

    if action == "yes":
        if row:
            amount = row[0]
            current_balance = await get_user_balance(uid)

            if amount > current_balance:
                try:
                    await bot.send_message(uid, "تم رفض المعالجة لعدم توفر رصيد كافي 🔴")
                except Exception:
                    pass
                try:
                    await callback.message.edit_text(callback.message.text + "\n\n❌ تم رفض الطلب: رصيد المشترك غير كافٍ.")
                except Exception:
                    pass
                await callback.answer("❌ رصيد المشترك غير كافٍ!", show_alert=True)
                return

            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE wallets SET balance = balance - ? WHERE user_id = ?", (amount, uid))
                await db.commit()

            new_balance = await get_user_balance(uid)

            try:
                await bot.send_message(
                    uid,
                    f"تم شحن حسابك بنجاح✅\n\nالمبلغ المشحون: {amount} SYP\nرصيد البوت الجديد: {new_balance} SYP"
                )
            except Exception:
                pass
            try:
                await callback.message.edit_text(callback.message.text + "\n\n✅ تمت الموافقة وخصم المبلغ من رصيد البوت وشحن الحساب.")
            except Exception:
                pass
        else:
            await callback.answer("❌ البيانات غير موجودة أو تم التعامل معها مسبقاً.", show_alert=True)
    else:
        try:
            await bot.send_message(uid, "تم رفض المعالجة لعدم توفر رصيد كافي 🔴")
        except Exception:
            pass
        try:
            await callback.message.edit_text(callback.message.text + "\n\n❌ تم رفض المعالجة من قبل الإدارة.")
        except Exception:
            pass

    await callback.answer()


@dp.callback_query(F.data == "bot_deposit")
async def cb_bot_deposit_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.message.answer(
        "💳 أختر احد طرق الشحن المتاحه:",
        reply_markup=get_bot_deposit_methods_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_dashboard")
async def cb_back_to_dashboard(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    balance = await get_user_balance(user.id)
    text = (
        f"🤖 لوحة تحكم الخدمات:\n\n"
        f"💳 الرصيد الحالي: {balance} SYP\n"
        f"🆔 أيدي حسابك: {user.id}"
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(text, reply_markup=get_dashboard_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "dep_syritel")
async def cb_syritel_deposit_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotSyritelDepositStates.waiting_for_trx_id)
    caption_text = await fetch_setting("msg_dep_syritel")
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع ♻️", callback_data="bot_deposit")]])

    try:
        await callback.message.delete()
        if os.path.exists(DEFAULT_SYRITEL_QR):
            photo = FSInputFile(DEFAULT_SYRITEL_QR)
            await callback.message.answer_photo(photo=photo, caption=caption_text, reply_markup=back_kb)
        else:
            await callback.message.answer(caption_text, reply_markup=back_kb)
    except Exception:
        pass
    await callback.answer()


@dp.message(BotSyritelDepositStates.waiting_for_trx_id)
async def process_syritel_trx_id(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال رقم العملية كـ نص:")
        return
    trx_id = message.text.strip()
    await state.update_data(trx_id=trx_id)
    await state.set_state(BotSyritelDepositStates.waiting_for_amount)
    await message.answer("ادخل المبلغ المراد شحنه 👇")


@dp.message(BotSyritelDepositStates.waiting_for_amount)
async def process_syritel_amount(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال مبلغ صالح:")
        return
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للمبلغ المراد شحنه:")
        return

    if amount < 200.0:
        await message.answer("❌ الحد الأدنى للشحن هو SYP 200.00. يرجى إدخال مبلغ صالح:")
        return

    data = await state.get_data()
    trx_id = data.get("trx_id")
    user = message.from_user

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO pending_bot_deposits (user_id, method, trx_id, amount) VALUES (?, ?, ?, ?)",
            (user.id, "syritel", trx_id, amount)
        )
        dep_id = cursor.lastrowid
        await db.commit()

    await message.answer(f"جاري معالجة العملية رقم `#{dep_id}` .انتظر قليلا ⏳")

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة", callback_data=f"bd_yes_{dep_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"bd_no_{dep_id}")
        ]
    ])

    await notify_next_admin(
        f"📥 **طلب شحن رصيد بوت جديد (سيريتل كاش) (#`{dep_id}`):**\n\n"
        f"👤 المشترك: @{user.username or 'بدون'} (`{user.id}`)\n"
        f"💳 رقم عملية التحويل: {trx_id}\n"
        f"💵 المبلغ المدخل: {amount} SYP",
        reply_markup=admin_kb
    )

    await state.clear()


@dp.callback_query(F.data == "dep_sham_syp")
async def cb_sham_syp_deposit_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotShamSypDepositStates.waiting_for_trx_id)
    caption_text = await fetch_setting("msg_dep_sham_syp")
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع ♻️", callback_data="bot_deposit")]])

    try:
        await callback.message.delete()
        if os.path.exists(DEFAULT_SHAM_SYP_QR):
            photo = FSInputFile(DEFAULT_SHAM_SYP_QR)
            await callback.message.answer_photo(photo=photo, caption=caption_text, reply_markup=back_kb)
        else:
            await callback.message.answer(caption_text, reply_markup=back_kb)
    except Exception:
        pass
    await callback.answer()


@dp.message(BotShamSypDepositStates.waiting_for_trx_id)
async def process_sham_syp_trx_id(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال رقم العملية كـ نص:")
        return
    trx_id = message.text.strip()
    await state.update_data(trx_id=trx_id)
    await state.set_state(BotShamSypDepositStates.waiting_for_amount)
    await message.answer("ادخل المبلغ المراد شحنه .👇")


@dp.message(BotShamSypDepositStates.waiting_for_amount)
async def process_sham_syp_amount(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال مبلغ صالح:")
        return
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للمبلغ المراد شحنه:")
        return

    if amount < 200.0:
        await message.answer("❌ الحد الأدنى للشحن هو SYP 200.00. يرجى إدخال مبلغ صالح:")
        return

    data = await state.get_data()
    trx_id = data.get("trx_id")
    user = message.from_user

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO pending_bot_deposits (user_id, method, trx_id, amount) VALUES (?, ?, ?, ?)",
            (user.id, "sham_syp", trx_id, amount)
        )
        dep_id = cursor.lastrowid
        await db.commit()

    await message.answer(f"جاري معالجة العملية رقم `#{dep_id}` .انتظر قليلا ⏳")

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة", callback_data=f"bd_yes_{dep_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"bd_no_{dep_id}")
        ]
    ])

    await notify_next_admin(
        f"📥 **طلب شحن رصيد بوت جديد (شام كاش سوري) (#`{dep_id}`):**\n\n"
        f"👤 المشترك: @{user.username or 'بدون'} (`{user.id}`)\n"
        f"💳 رقم عملية التحويل: {trx_id}\n"
        f"💵 المبلغ المدخل: {amount} SYP",
        reply_markup=admin_kb
    )

    await state.clear()


@dp.callback_query(F.data == "dep_sham_usd")
async def cb_sham_usd_deposit_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotShamUsdDepositStates.waiting_for_trx_id)
    caption_text = await fetch_setting("msg_dep_sham_usd")
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="رجوع ♻️", callback_data="bot_deposit")]])

    try:
        await callback.message.delete()
        if os.path.exists(DEFAULT_SHAM_USD_QR):
            photo = FSInputFile(DEFAULT_SHAM_USD_QR)
            await callback.message.answer_photo(photo=photo, caption=caption_text, reply_markup=back_kb)
        else:
            await callback.message.answer(caption_text, reply_markup=back_kb)
    except Exception:
        pass
    await callback.answer()


@dp.message(BotShamUsdDepositStates.waiting_for_trx_id)
async def process_sham_usd_trx_id(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال رقم العملية كـ نص:")
        return
    trx_id = message.text.strip()
    await state.update_data(trx_id=trx_id)
    await state.set_state(BotShamUsdDepositStates.waiting_for_amount)
    await message.answer("ادخل المبلغ المراد شحنه .👇")


@dp.message(BotShamUsdDepositStates.waiting_for_amount)
async def process_sham_usd_amount(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال مبلغ صالح:")
        return
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للمبلغ المراد شحنه:")
        return

    if amount < 1.0:
        await message.answer("❌ الحد الأدنى للشحن هو USD 1.00. يرجى إدخال مبلغ صالح:")
        return

    data = await state.get_data()
    trx_id = data.get("trx_id")
    user = message.from_user

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO pending_bot_deposits (user_id, method, trx_id, amount) VALUES (?, ?, ?, ?)",
            (user.id, "sham_usd", trx_id, amount)
        )
        dep_id = cursor.lastrowid
        await db.commit()

    await message.answer(f"جاري معالجة العملية رقم `#{dep_id}` .انتظر قليلا ⏳")

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة", callback_data=f"bd_yes_{dep_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"bd_no_{dep_id}")
        ]
    ])

    await notify_next_admin(
        f"📥 **طلب شحن رصيد بوت جديد (شام كاش دولار) (#`{dep_id}`):**\n\n"
        f"👤 المشترك: @{user.username or 'بدون'} (`{user.id}`)\n"
        f"💳 رقم عملية التحويل: {trx_id}\n"
        f"💵 المبلغ المدخل: {amount} USD",
        reply_markup=admin_kb
    )

    await state.clear()


@dp.callback_query(F.data.startswith("bd_yes_") | F.data.startswith("bd_no_"))
async def admin_bot_deposit_decision(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_admin(callback.from_user.id):
        return
    data_parts = callback.data.split("_")
    if len(data_parts) >= 3:
        action = data_parts[1]
        dep_id = int(data_parts[2])
    else:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, method, trx_id, amount FROM pending_bot_deposits WHERE id = ?", (dep_id,)) as cur:
            row = await cur.fetchone()
        
        await db.execute("DELETE FROM pending_bot_deposits WHERE id = ?", (dep_id,))
        await db.commit()

    if action == "yes":
        if row:
            uid, method, trx_id, amount = row
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("INSERT OR IGNORE INTO wallets (user_id, balance) VALUES (?, 0.0)", (uid,))
                await db.execute("UPDATE wallets SET balance = balance + ? WHERE user_id = ?", (amount, uid))
                await db.commit()

            await log_financial(dep_id, uid, "bot_deposit", amount, "USD" if method == "sham_usd" else "SYP")
            new_balance = await get_user_balance(uid)

            try:
                currency_label = "USD" if method == "sham_usd" else "SYP"
                await bot.send_message(
                    uid,
                    f"تم شحن الرصيد الى البوت بنجاح برقم `#{dep_id}` ✅\n\n💵 المبلغ المشحون: {amount} {currency_label}\n💳 رصيد البوت الجديد: {new_balance} SYP"
                )
            except Exception:
                pass
            try:
                await callback.message.edit_text(callback.message.text + f"\n\n✅ تمت الموافقة على الإيداع رقم `#{dep_id}` وإضافة الرصيد بنجاح.")
            except Exception:
                pass
        else:
            await callback.answer("❌ البيانات غير موجودة أو تم التعامل معها مسبقاً.", show_alert=True)
    else:
        if row:
            uid = row[0]
            try:
                await bot.send_message(
                    uid,
                    f"معلومات التحويل لعملية الإيداع رقم `#{dep_id}` غير صحيحة. تأكد من المعلومات وقم بإرسال الطلب مرة أخرى .🔴"
                )
            except Exception:
                pass
        try:
            await callback.message.edit_text(callback.message.text + f"\n\n❌ تم رفض طلب الإيداع رقم `#{dep_id}`.")
        except Exception:
            pass

    await callback.answer()


# ========================================================
# === إدارة إنشاء الحسابات ===
# ========================================================
@dp.callback_query(F.data == "menu_ichancy_create")
async def cb_create_account_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT ichancy_username, ichancy_password FROM ichancy_accounts WHERE user_id = ?", (user_id,)) as cur:
            acc_row = await cur.fetchone()
            if acc_row:
                acc_usr, acc_pwd = acc_row
                await callback.message.answer(
                    f"⚠️ أنت تملك حساب في البوت .\n\n👤 أسم المستخدم : {acc_usr}\n🔑 كلمة المرور : {acc_pwd}"
                )
                await callback.answer("لديك حساب مسبق بالفعل!", show_alert=True)
                return

        async with db.execute("SELECT acc_username FROM pending_acc_requests WHERE user_id = ?", (user_id,)) as cur:
            if await cur.fetchone():
                await callback.answer("⚠️ لديك طلب إنشاء حساب قيد المراجعة لدى الإدارة بالفعل!", show_alert=True)
                return

    await state.set_state(AccountCreationStates.waiting_for_username)
    await callback.message.edit_text(
        "👤 إنشاء حساب ichancy جديد:\n\nالرجاء إدخال اسم من 8 أحرف إنجليزية على الأقل وأرقام.\n⚠️ بشرط ألا يحوي على رموز أو مسافات."
    )
    await callback.answer()


@dp.message(AccountCreationStates.waiting_for_username)
async def process_account_username(message: types.Message, state: FSMContext):
    # منع قبول الأوامر أو أزرار القائمة أثناء انتظار اسم المستخدم
    if message.text and message.text.startswith("/"):
        await message.answer("❌ لا يمكنك استخدام الأوامر أثناء عملية إنشاء الحساب.\n\nيرجى كتابة اسم المستخدم المطلوب (أحرف إنجليزية وأرقام، وبدون مسافات أو رموز):")
        return

    username_input = message.text.strip() if message.text else ""

    # التحقق من أن اسم المستخدم يتكون من 8 أحرف إنجليزية وأرقام على الأقل بدون رموز
    if not re.match(r"^[A-Za-z0-9]{8,}$", username_input):
        await message.answer(
            "❌ اسم المستخدم غير صالح!\n"
            "يجب أن يكون من 8 أحرف إنجليزية وأرقام على الأقل وبدون أي رموز أو مسافات. حاول مجدداً:"
        )
        return

    # حفظ الاسم والانتقال لحالة كلمة المرور
    await state.update_data(acc_username=username_input)
    await state.set_state(AccountCreationStates.waiting_for_password)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 إلغاء", callback_data="main_menu")]])
    await message.answer(
        "🔑 أدخل كلمة مرور مناسبة (أحرف إنجليزية وأرقام، بدون رموز):",
        reply_markup=markup
    )
    if not message.text:
        await message.answer("❌ يرجى إدخال اسم مستخدم كـ نص:")
        return
    text = message.text.strip()
    
    if not re.match(r"^[A-Za-z0-9]{8,}$", text):
        await message.answer("❌ اسم المستخدم غير صالح!\nيجب أن يكون من 8 أحرف إنجليزية وأرقام على الأقل وبدون أي رموز أو مسافات. حاول مجدداً:")
        return

    await state.update_data(acc_username=text)
    await state.set_state(AccountCreationStates.waiting_for_password)
    await message.answer("🔑 أدخل كلمة مرور مناسبة (أحرف إنجليزية وأرقام، بدون رموز):")


@dp.message(AccountCreationStates.waiting_for_password)
async def process_account_password(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ يرجى إدخال كلمة المرور كـ نص:")
        return
    text = message.text.strip()
    
    if not re.match(r"^[A-Za-z0-9]{6,}$", text):
        await message.answer("❌ كلمة المرور غير صالحة!\nيجب أن تتكون من أحرف إنجليزية وأرقام فقط وبدون رموز (6 محاور أو أكثر). حاول مجدداً:")
        return

    data = await state.get_data()
    acc_username = data.get("acc_username")
    acc_password = text
    user = message.from_user

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO pending_acc_requests (user_id, acc_username, acc_password) VALUES (?, ?, ?)",
            (user.id, acc_username, acc_password)
        )
        await db.commit()

    await message.answer("يتم إنشاء حساب جديد .يرجى الانتظار ⏳")

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة وإرسال", callback_data=f"acc_yes_{user.id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"acc_no_{user.id}")
        ],
        [
            InlineKeyboardButton(text="✏️ تعديل الاسم", callback_data=f"edit_acc_usr_{user.id}"),
            InlineKeyboardButton(text="🔑 تعديل كلمة المرور", callback_data=f"edit_acc_pwd_{user.id}")
        ]
    ])

    await notify_next_admin(
        f"📥 طلب إنشاء حساب ichancy جديد:\n\n"
        f"👤 صاحب الحساب: @{user.username or 'بدون'} ({user.id})\n"
        f"🏷️ اسم المستخدم المقترح: {acc_username}\n"
        f"🔑 كلمة المرور المقترحة: {acc_password}",
        reply_markup=admin_kb
    )

    await state.clear()


@dp.callback_query(F.data.startswith("acc_yes_") | F.data.startswith("acc_no_"))
async def admin_acc_decision(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    if len(parts) >= 3:
        action, uid = parts[1], int(parts[2])
    else:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT acc_username, acc_password FROM pending_acc_requests WHERE user_id = ?", (uid,)) as cur:
            row = await cur.fetchone()
        
        await db.execute("DELETE FROM pending_acc_requests WHERE user_id = ?", (uid,))
        await db.commit()

    if action == "yes":
        if row:
            u_name, u_pwd = row
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("INSERT OR REPLACE INTO ichancy_accounts (user_id, ichancy_username, ichancy_password) VALUES (?, ?, ?)", (uid, u_name, u_pwd))
                await db.commit()

            try:
                await bot.send_message(
                    uid,
                    f"🎉 تم قبول وتفعيل حسابك بنجاح!\n\n👤 أسم المستخدم: {u_name}\n🔑 كلمة المرور : {u_pwd}"
                )
            except Exception:
                pass
            try:
                await callback.message.edit_text(callback.message.text + "\n\n✅ تمت الموافقة وإرسال البيانات للمستخدم.")
            except Exception:
                pass
        else:
            await callback.answer("❌ البيانات غير موجودة أو تم التعامل معها مسبقاً.", show_alert=True)
    else:
        try:
            await bot.send_message(uid, "❌ عذراً، تم رفض طلب إنشاء حساب ichancy الخاص بك من قبل الإدارة.")
        except Exception:
            pass
        try:
            await callback.message.edit_text(callback.message.text + "\n\n❌ تم رفض الطلب.")
        except Exception:
            pass

    await callback.answer()


@dp.callback_query(F.data.startswith("edit_acc_usr_") | F.data.startswith("edit_acc_pwd_"))
async def admin_start_edit_field(callback: types.CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    parts = callback.data.split("_")
    if len(parts) >= 4:
        field_type = parts[2]
        uid = int(parts[3])
    else:
        return

    await state.set_state(AdminEditStates.editing_username if field_type == "usr" else AdminEditStates.editing_password)
    await state.update_data(target_uid=uid, msg_id=callback.message.message_id)
    
    field_name = "اسم المستخدم الجديد" if field_type == "usr" else "كلمة المرور الجديدة"
    await callback.message.answer(f"✍️ أرسل {field_name} للمستخدم ({uid}):")
    await callback.answer()


@dp.message(AdminEditStates.editing_username)
async def admin_save_edited_username(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if not message.text:
        await message.answer("❌ يرجى إرسال نص صالح:")
        return
    new_value = message.text.strip()
    data = await state.get_data()
    uid = data.get("target_uid")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE pending_acc_requests SET acc_username = ? WHERE user_id = ?", (new_value, uid))
        await db.commit()
        
        async with db.execute("SELECT acc_username, acc_password FROM pending_acc_requests WHERE user_id = ?", (uid,)) as cur:
            row = await cur.fetchone()

    if row:
        u_name, u_pwd = row
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ موافقة وإرسال", callback_data=f"acc_yes_{uid}"),
                InlineKeyboardButton(text="❌ رفض", callback_data=f"acc_no_{uid}")
            ],
            [
                InlineKeyboardButton(text="✏️ تعديل الاسم", callback_data=f"edit_acc_usr_{uid}"),
                InlineKeyboardButton(text="🔑 تعديل كلمة المرور", callback_data=f"edit_acc_pwd_{uid}")
            ]
        ])
        await message.answer(
            f"✅ تم تحديث اسم المستخدم بنجاح! الطلب المحدث:\n\n👤 صاحب الحساب: ({uid})\n🏷️ اسم المستخدم: {u_name}\n🔑 كلمة المرور: {u_pwd}",
            reply_markup=admin_kb
        )
    else:
        await message.answer("❌ عذراً، لم يتم العثور على الطلب المعلق.")

    await state.clear()


@dp.message(AdminEditStates.editing_password)
async def admin_save_edited_password(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    if not message.text:
        await message.answer("❌ يرجى إرسال نص صالح:")
        return
    new_value = message.text.strip()
    data = await state.get_data()
    uid = data.get("target_uid")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE pending_acc_requests SET acc_password = ? WHERE user_id = ?", (new_value, uid))
        await db.commit()
        
        async with db.execute("SELECT acc_username, acc_password FROM pending_acc_requests WHERE user_id = ?", (uid,)) as cur:
            row = await cur.fetchone()

    if row:
        u_name, u_pwd = row
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ موافقة وإرسال", callback_data=f"acc_yes_{uid}"),
                InlineKeyboardButton(text="❌ رفض", callback_data=f"acc_no_{uid}")
            ],
            [
                InlineKeyboardButton(text="✏️ تعديل الاسم", callback_data=f"edit_acc_usr_{uid}"),
                InlineKeyboardButton(text="🔑 تعديل كلمة المرور", callback_data=f"edit_acc_pwd_{uid}")
            ]
        ])
        await message.answer(
            f"✅ تم تحديث كلمة المرور بنجاح! الطلب المحدث:\n\n👤 صاحب الحساب: ({uid})\n🏷️ اسم المستخدم: {u_name}\n🔑 كلمة المرور: {u_pwd}",
            reply_markup=admin_kb
        )
    else:
        await message.answer("❌ عذراً، لم يتم العثور على الطلب المعلق.")

    await state.clear()


# ========================================================
# === التشغيل الأساسي للبوت ===
# ========================================================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    bot_status = await fetch_setting("bot_status")
    if bot_status == "stopped" and not await is_admin(message.from_user.id):
        await message.answer("🔴 عذراً، البوت متوقف حالياً للصيانة من قبل الإدارة.")
        return

    user = message.from_user
    username = user.username or "NoUsername"
    
    args = message.text.split() if message.text else []
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1].replace("ref_", ""))
        except ValueError:
            pass

    await register_user_if_new(user.id, username, referred_by)
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT agreed FROM user_agreements WHERE user_id = ?", (user.id,)) as cursor:
            row = await cursor.fetchone()
            has_agreed = row[0] if row else 0

    if not has_agreed:
        welcome_text = await fetch_setting("welcome_message")
        terms_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ أوافق على الشروط والأحكام", callback_data="agree_terms")],
            [InlineKeyboardButton(text="📢 الانضمام لقناة البوت", url="https://t.me/ichancynor")]
        ])
        await message.answer(welcome_text, reply_markup=terms_kb)
        return

    if not await verify_subscription(bot, user.id):
        channel = await fetch_setting("channel_username")
        sub_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 انضم للقناة الآن", url=f"https://t.me/{channel.replace('@', '')}")],
            [InlineKeyboardButton(text="🔄 تحقق من الاشتراك", callback_data="go_main")]
        ])
        await message.answer(f"⚠️ عذراً، يجب عليك الاشتراك في قناتنا الرسمية ({channel}) أولاً لتشغيل البوت.", reply_markup=sub_kb)
        return

    await message.answer(
        "🌸 أهلاً بك. تم تفعيل حسابك بنجاح.\nيمكنك استخدام الأزرار أدناه للتحكم الكامل بالخدمات."
    )


@dp.callback_query(F.data == "agree_terms")
async def cb_agree_terms(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO user_agreements (user_id, agreed) VALUES (?, 1)", (user_id,))
        await db.commit()
        
    await callback.message.edit_text(
        "✅ تمت الموافقة على الشروط والأحكام بنجاح!\n\nالخطوة التالية:\nيرجى التأكد من انضمامك إلى قناتنا الرسمية (`@ichancynor`) ثم اضغط على زر التحقق أدناه.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 قناة البوت", url="https://t.me/ichancynor")],
            [InlineKeyboardButton(text="✅ تحقق من الاشتراك والبدء", callback_data="go_main")]
        ])
    )
    await callback.answer("شكراً لموافقتك على الشروط!", show_alert=True)


@dp.callback_query(F.data == "go_main")
async def cb_go_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    if not await verify_subscription(bot, user.id):
        await callback.answer("عذراً، لم تقم بالاشتراك بالقناة بعد!", show_alert=True)
        return

    balance = await get_user_balance(user.id)
    text = (
        f"🤖 لوحة تحكم الخدمات:\n\n"
        f"💳 الرصيد الحالي: {balance} SYP\n"
        f"🆔 أيدي حسابك: {user.id}"
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(text, reply_markup=get_dashboard_keyboard())
    await callback.answer()


@dp.message(Command("run_bot"))
async def cmd_run_bot(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    if not await verify_subscription(bot, user.id):
        await message.answer("⚠️ عذراً، يجب الاشتراك في قناة البوت أولاً.")
        return

    balance = await get_user_balance(user.id)
    text = (
        f"🤖 لوحة تحكم الخدمات:\n\n"
        f"💳 الرصيد الحالي: {balance} SYP\n"
        f"🆔 أيدي حسابك: {user.id}"
    )
    await message.answer(text, reply_markup=get_dashboard_keyboard())


async def main():
    logging.basicConfig(level=logging.INFO)
    await init_database()
    
    await bot.set_my_commands([
        BotCommand(command="run_bot", description="🚀 القائمة الرئيسية")
    ])
    
    try:
        await bot.set_my_commands(
            commands=[
                BotCommand(command="run_bot", description="🚀 القائمة الرئيسية"),
                BotCommand(command="admin", description="👑 لوحة تحكم المشرف")
            ],
            scope=BotCommandScopeChat(chat_id=ADMIN_ID)
        )
    except Exception as e:
        logging.warning(f"Could not set admin scope commands: {e}")
    
    print("🤖 جاري تشغيل البوت بنجاح مع تفعيل نظام توزيع الطلبات بالدور وعمولة السحب...")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
