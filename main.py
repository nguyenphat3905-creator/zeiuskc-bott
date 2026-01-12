import telebot
from telebot import types
import random
import string
import requests
import json
import os
import urllib.parse
import time
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
API_TOKEN = '8253854117:AAGW3fnvJGcHqRS1ahTFmB6sNtwdJTaQe50'
ADMIN_ID = 8481206726 
LINK4M_API = '66334c6e06854a07b62bbd8d' 
LAYMA_TOKEN = 'a3b8987dff9f812f7619296cabf79703'
DATA_FILE = ".zeus_internal_db.dat" 
DIEM_THUONG = 0.5 

bot = telebot.TeleBot(API_TOKEN)
session = requests.Session()

# --- QUẢN LÝ DỮ LIỆU ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            try: 
                data = json.load(f)
                if "users" not in data: data["users"] = {}
                if "blacklist" not in data: data["blacklist"] = []
                return data
            except: pass
    return {"users": {}, "blacklist": []}

def save_data():
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

db = load_data()
user_data = db["users"]
blacklist = db["blacklist"]
pending_tokens = {} 
last_click_time = {}

# --- HÀM KIỂM TRA & RESET ---
def check_and_reset_tasks(uid):
    if uid not in user_data: return
    user = user_data[uid]
    now = datetime.now()
    
    if 'last_reset' not in user:
        user['last_reset'] = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        save_data()
        return

    last_reset_dt = datetime.strptime(user['last_reset'], "%Y-%m-%d %H:%M:%S")
    if now - last_reset_dt >= timedelta(hours=24):
        user['link4m_count'] = 0
        user['layma_count'] = 0
        save_data()

# --- HÀM RÚT GỌN LINK ---
def get_short_link(url, provider):
    try:
        encoded_url = urllib.parse.quote(url)
        if provider == "layma":
            api_url = f"https://api.layma.net/api/admin/shortlink/quicklink?tokenUser={LAYMA_TOKEN}&format=text&url={encoded_url}"
            res = session.get(api_url, timeout=10)
            return res.text.strip() if "layma.net" in res.text else url
        else:
            api_url = f"https://link4m.co/api-shorten/v2?api={LINK4M_API}&url={encoded_url}"
            res = session.get(api_url, timeout=10).json()
            return res.get('shortenedUrl', url)
    except:
        return url

# --- GIAO DIỆN MENU ---
def main_menu():
    m = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add("🚀 Kiếm Kim Cương", "👤 Tài Khoản",
          "💳 Rút Thưởng", "🏆 Bảng Xếp Hạng",
          "📌 Thông Tin", "📚 Hướng Dẫn",
          "☎️ Hỗ Trợ", "📩 Chia sẻ bot")
    m.add("🎯 Nhiệm vụ Đặc biệt")
    return m

# --- LỆNH /START ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    if user_id in blacklist: return
    
    if user_id not in user_data:
        user_data[user_id] = {
            'username': message.from_user.first_name or "Người dùng", 
            'uid_game': 'Chưa đặt', 'points': 0.0, 
            'total_earned': 0.0,
            'link4m_count': 0, 'layma_count': 0,
            'last_reset': (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        }
        save_data()

    check_and_reset_tasks(user_id)

    args = message.text.split()
    if len(args) > 1:
        token = args[1]
        if token in pending_tokens:
            info = pending_tokens[token]
            if info['id'] == user_id:
                # ANTI-CHEAT: Kiểm tra thời gian (dưới 15s là bypass)
                elapsed = time.time() - info['start_time']
                if elapsed < 15:
                    bot.send_message(user_id, "⚠️ **Thao tác quá nhanh!** Vui lòng không dùng tool bypass.")
                    return

                provider = info['provider']
                u = user_data[user_id]
                u[f"{provider}_count"] = u.get(f"{provider}_count", 0) + 1
                u['points'] = round(u.get('points', 0) + DIEM_THUONG, 1)
                u['total_earned'] = round(u.get('total_earned', 0) + DIEM_THUONG, 1)
                u['last_reset'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                save_data()
                del pending_tokens[token]
                bot.send_message(user_id, f"✅ Chúc mừng! Bạn nhận được +{DIEM_THUONG} Kim Cương!", reply_markup=main_menu())
                return

    bot.send_message(user_id, "🌟 **ZEUS BOT - KIM CƯƠNG MIỄN PHÍ**", reply_markup=main_menu())

# --- XỬ LÝ MENU CHÍNH ---
@bot.message_handler(func=lambda m: True)
def handle_menu(message):
    uid = str(message.chat.id)
    if uid not in user_data or uid in blacklist: return
    check_and_reset_tasks(uid)
    user = user_data[uid]

    if message.text == "🚀 Kiếm Kim Cương":
        total_done = user.get('link4m_count', 0) + user.get('layma_count', 0)
        l4m = user.get('link4m_count', 0)
        layma = user.get('layma_count', 0)
        text = (f"🎯 **CHỌN NHÀ CUNG CẤP**\n────────────────────\n"
                f"📊 Nhiệm vụ hôm nay: {total_done}/3\n\n"
                f"Chọn nhà cung cấp bạn muốn làm nhiệm vụ:")
        m = types.InlineKeyboardMarkup()
        m.add(types.InlineKeyboardButton(f"LINK4M ({l4m}/2)", callback_data="task_link4m"),
              types.InlineKeyboardButton(f"LAYMA ({layma}/1)", callback_data="task_layma"))
        bot.send_message(uid, text, reply_markup=m, parse_mode="Markdown")

    elif message.text == "👤 Tài Khoản":
        total_done = user.get('link4m_count', 0) + user.get('layma_count', 0)
        text = (f"👤 **Hồ Sơ Cá Nhân**\n📝 Biệt danh: {user['username']}\n"
                f"🆔 Game UID: `{user['uid_game']}`\n💰 Số dư: {user['points']:.1f} KC\n"
                f"📊 Tổng kiếm: {user.get('total_earned', 0.0):.1f} KC\n"
                f"🎯 Nhiệm vụ hôm nay: {total_done}/3")
        bot.send_message(uid, text, parse_mode="Markdown")

    elif message.text == "🏆 Bảng Xếp Hạng":
        top_30 = sorted(user_data.items(), key=lambda x: x[1].get('points', 0), reverse=True)[:30]
        text = "🏆 **TOP 30 ĐẠI GIA KIM CƯƠNG**\n\n"
        for i, (tid, info) in enumerate(top_30, 1):
            text += f"{i}. {info['username']} - {info['points']:.1f} KC\n"
        bot.send_message(uid, text, parse_mode="Markdown")

    elif message.text == "💳 Rút Thưởng":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(types.InlineKeyboardButton("💎 Gói 25.0 Kim Cương", callback_data="withdraw_25"),
              types.InlineKeyboardButton("💎 Gói 51.0 Kim Cương", callback_data="withdraw_51"),
              types.InlineKeyboardButton("💎 Gói 113.0 Kim Cương", callback_data="withdraw_113"))
        bot.send_message(uid, f"💳 Số dư: {user['points']:.1f} KC\nChọn gói muốn rút:", reply_markup=m)

    elif message.text == "📚 Hướng Dẫn":
        huong_dan_text = (f"📚 **HƯỚNG DẪN NHẬN KIM CƯƠNG**\n"
                          f"──────────────────────\n"
                          f"1️⃣ Bấm nút bên dưới\n"
                          f"2️⃣ Vượt link rút gọn nhà cung cấp tương ứng\n"
                          f"3️⃣ Sau đó để trang sẽ tự chuyển tới bot hoặc bấm \"Tiếp Tục Truy Cập Telegram?\" và bạn nhận kim cương\n\n"
                          f"⚠️ **LƯU Ý QUAN TRỌNG:**\n"
                          f"❌ Không dùng VPN/Proxy khi vượt link\n"
                          f"❌ Không dùng công cụ/tool bypass link\n"
                          f"❌ Hệ thống tự động kiểm tra, nếu vi phạm sẽ khóa tài khoản vĩnh viễn.")
        bot.send_message(uid, huong_dan_text, parse_mode="Markdown")

# --- XỬ LÝ CALLBACK ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = str(call.message.chat.id)
    
    # Anti-Spam
    if int(uid) != ADMIN_ID:
        now = time.time()
        if uid in last_click_time and now - last_click_time[uid] < 1.2:
            bot.answer_callback_query(call.id, "⚠️ Đừng ấn quá nhanh!")
            return
        last_click_time[uid] = now

    check_and_reset_tasks(uid)
    user = user_data.get(uid)

    if call.data.startswith("task_"):
        for tk, info in pending_tokens.items():
            if info['id'] == uid:
                text_warn = ("⚠️ **Bạn đang có một nhiệm vụ chưa hoàn thành!**\n\n"
                             "Hệ thống chỉ cho phép làm từng nhiệm vụ một. "
                             "Nếu link bị lỗi, hãy nhấn nút dưới đây để hủy và nhận lại.")
                m_warn = types.InlineKeyboardMarkup()
                m_warn.add(types.InlineKeyboardButton("❌ Hủy nhiệm vụ hiện tại", callback_data="clear_task"))
                bot.edit_message_text(text_warn, uid, call.message.message_id, reply_markup=m_warn, parse_mode="Markdown")
                return

        provider = call.data.split("_")[1]
        limit = 2 if provider == "link4m" else 1
        current = user.get(f"{provider}_count", 0)

        if current >= limit:
            last_dt = datetime.strptime(user['last_reset'], "%Y-%m-%d %H:%M:%S")
            next_reset = last_dt + timedelta(hours=24)
            bot.answer_callback_query(call.id, f"❌ Hết lượt {provider.upper()}!\nQuay lại lúc: {next_reset.strftime('%H:%M %d/%m')}", show_alert=True)
            return

        tk = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        pending_tokens[tk] = {'id': uid, 'provider': provider, 'start_time': time.time()}
        short_url = get_short_link(f"https://t.me/ZeiusKCbot?start={tk}", provider)
        
        provider_name = provider.upper()
        task_no = "1/2" if provider == "link4m" else "2/2"
        
        task_text = (f"🎯 **NHIỆM VỤ Số {task_no}**\n"
                     f"──────────────────────\n"
                     f"🢂 Nhà cung cấp: {provider_name}\n"
                     f"📊 Đã dùng {provider_name}: {current}/{limit}\n"
                     f"💰 Phần thưởng: {DIEM_THUONG} 💎\n"
                     f"──────────────────────\n"
                     f"📋 **HƯỚNG DẪN:**\n"
                     f"1️⃣ Bấm nút bên dưới\n"
                     f"2️⃣ Vượt link rút gọn {provider_name}\n"
                     f"3️⃣ Sau đó để trang sẽ tự chuyển tới bot hoặc bấm \"Tiếp Tục Truy Cập Telegram?\" và bạn nhận kim cương\n\n"
                     f"──────────────────────\n"
                     f"⚠️ **LƯU Ý:**\n"
                     f"❌ Không dùng VPN/Proxy\n"
                     f"❌ Không dùng tool bypass\n"
                     f"❌ Bot có thể check và nếu vi phạm sẽ ban lập tức")
        
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(types.InlineKeyboardButton("🔗 BẮT ĐẦU NHIỆM VỤ", url=short_url),
              types.InlineKeyboardButton("❌ HỦY NHIỆM VỤ", callback_data="clear_task"))
        bot.edit_message_text(task_text, uid, call.message.message_id, reply_markup=m, parse_mode="Markdown")

    elif call.data == "clear_task":
        tokens_to_del = [tk for tk, info in pending_tokens.items() if info['id'] == uid]
        for tk in tokens_to_del: del pending_tokens[tk]
        bot.edit_message_text("♻️ **Đã dọn dẹp nhiệm vụ cũ!**\nGiờ bạn có thể chọn nhà cung cấp để nhận nhiệm vụ mới.", uid, call.message.message_id, reply_markup=None, parse_mode="Markdown")

    elif call.data.startswith("withdraw_"):
        amt = float(call.data.split("_")[1])
        if user['points'] >= amt:
            user['points'] = round(user['points'] - amt, 1)
            save_data()
            bot.send_message(uid, f"✅ Đơn rút {amt} KC đang xử lý.")
            
            m_adm = types.InlineKeyboardMarkup()
            m_adm.add(types.InlineKeyboardButton("✅ Duyệt", callback_data=f"adm_done_{uid}_{amt}"),
                      types.InlineKeyboardButton("❌ Ban", callback_data=f"adm_ban_{uid}_{amt}"))
            bot.send_message(ADMIN_ID, f"🔔 **ĐƠN RÚT MỚI**\n👤 User: {user['username']}\n🆔 ID: `{uid}`\n💎 Gói: {amt} KC", reply_markup=m_adm, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ Không đủ số dư!", show_alert=True)

    elif call.data.startswith("adm_"):
        if int(uid) != ADMIN_ID: return
        data_parts = call.data.split("_")
        action, target_uid, amount = data_parts[1], data_parts[2], data_parts[3]

        if action == "done":
            bot.send_message(target_uid, f"✅ **Thông báo:** Đơn rút {amount} KC đã được phê duyệt!")
            bot.edit_message_text(f"{call.message.text}\n\n✅ **ĐÃ DUYỆT**", ADMIN_ID, call.message.message_id, reply_markup=None)
        elif action == "ban":
            if target_uid not in blacklist: blacklist.append(str(target_uid))
            save_data()
            bot.send_message(target_uid, "❌ Bạn đã bị ban do vi phạm.")
            bot.edit_message_text(f"{call.message.text}\n\n❌ **ĐÃ BAN**", ADMIN_ID, call.message.message_id, reply_markup=None)

if __name__ == "__main__":
    bot.polling(none_stop=True)
