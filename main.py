import telebot
from telebot import types
from rembg import remove
from PIL import Image
import logging
import os
import tempfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ------------------- 1. Environment Variable -------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ------------------- 2. In-memory storage -------------------
user_choice = {}

# ------------------- 3. Dummy Web Server for Health Check (Koyeb/Render) -------------------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    server.serve_forever()

# Start dummy server in background thread
threading.Thread(target=run_health_server, daemon=True).start()

# ------------------- 4. Telegram Bot Handlers -------------------
@bot.message_handler(commands=["start"])
def start_handler(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("အဖြူရောင် ⬜", "အမည်းရောင် ⬛")
    bot.send_message(message.chat.id, "အရင်ဆုံး နောက်ခံအရောင်ရွေးပါ။", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["အဖြူရောင် ⬜", "အမည်းရောင် ⬛"])
def choose_background(message):
    user_choice[message.chat.id] = message.text
    bot.reply_to(message, f"{message.text} ကိုရွေးချယ်ပြီးပါပြီ။\nအခု ဓာတ်ပုံတစ်ပုံပို့ပေးပါ။")

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    chat_id = message.chat.id
    if chat_id not in user_choice:
        bot.reply_to(message, "ကျေးဇူးပြုပြီး အရင်ဆုံး နောက်ခံအရောင်ရွေးပါ။")
        return

    bot.reply_to(message, "ဓာတ်ပုံကို လုပ်ဆောင်နေပါပြီ... ⏳")

    try:
        # Download photo
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)

        # Save temporary input file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_in:
            temp_in.write(downloaded)
            temp_in_path = temp_in.name

        # Remove background
        with open(temp_in_path, "rb") as f:
            input_img = Image.open(f)
            output_img = remove(input_img)   # RGBA with transparent background

        # Create solid background
        if "အဖြူ" in user_choice[chat_id]:
            bg = Image.new('RGBA', output_img.size, (255, 255, 255, 255))
        else:
            bg = Image.new('RGBA', output_img.size, (0, 0, 0, 255))

        # Composite
        result = Image.alpha_composite(bg, output_img)

        # Save result
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_out:
            result.save(temp_out.name)
            temp_out_path = temp_out.name

        # Send back
        with open(temp_out_path, "rb") as f:
            bot.send_photo(chat_id, f)

        # Cleanup
        os.unlink(temp_in_path)
        os.unlink(temp_out_path)

    except Exception as e:
        logging.error(f"Error: {e}")
        bot.reply_to(message, "ပုံကို လုပ်ဆောင်ရာတွင် အမှားရှိသွားပါသည်။ နောက်တစ်ခါ ထပ်ကြိုးစားပါ။")

# ------------------- 5. Start Bot -------------------
if __name__ == "__main__":
    print("Bot started...")
    bot.polling(none_stop=True)
