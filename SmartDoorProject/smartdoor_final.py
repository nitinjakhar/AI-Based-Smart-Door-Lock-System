import cv2
import face_recognition
import os
import requests
import numpy as np
import serial
import time

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackQueryHandler

# ================= SETTINGS =================

TELEGRAM_TOKEN = "8750881311:AAEr_IbOZuPyatot28t7c1R9FT_ZAcbEjyY"
CHAT_ID = "5437471744"

ESP32_IP = "http://10.199.43.169"
COM_PORT = "COM6"

# ================= ARDUINO CONNECT =================

arduino = serial.Serial(COM_PORT, 9600, timeout=1)
time.sleep(2)

# ================= TELEGRAM BOT =================

bot = Bot(token=TELEGRAM_TOKEN)

# ================= FACE DATABASE =================

known_face_encodings = []
known_face_names = []

path = "known_faces"

for file in os.listdir(path):
    image = face_recognition.load_image_file(f"{path}/{file}")
    encoding = face_recognition.face_encodings(image)[0]

    known_face_encodings.append(encoding)
    known_face_names.append(os.path.splitext(file)[0])

print("Known faces loaded")

# ================= ALERT CONTROL =================

last_alert_time = 0

def send_unknown_alert(frame):

    global last_alert_time

    if time.time() - last_alert_time < 10:
        return

    cv2.imwrite("unknown.jpg", frame)

    keyboard = [
        [
            InlineKeyboardButton("🔓 Open", callback_data="open"),
            InlineKeyboardButton("🔒 Lock", callback_data="lock")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_photo(
        chat_id=CHAT_ID,
        photo=open("unknown.jpg", "rb"),
        caption="⚠ Unknown Person Detected!",
        reply_markup=reply_markup
    )

    last_alert_time = time.time()

# ================= TELEGRAM BUTTON HANDLER =================

def button(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "open":
        arduino.write(b'1')
        query.edit_message_caption("Door Opened 🔓")

    elif query.data == "lock":
        arduino.write(b'0')
        query.edit_message_caption("Door Locked 🔒")

# ================= TELEGRAM BOT START =================

updater = Updater(TELEGRAM_TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CallbackQueryHandler(button))

updater.start_polling()

# ================= MAIN LOOP =================

print("Smart Door System Running...")

while True:

    try:
        response = requests.get(f"{ESP32_IP}/capture", timeout=5)

        img_array = np.array(bytearray(response.content), dtype=np.uint8)
        frame = cv2.imdecode(img_array, -1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        faces = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, faces)

        for face_encoding, face_location in zip(encodings, faces):

            matches = face_recognition.compare_faces(
                known_face_encodings,
                face_encoding
            )

            name = "Unknown"

            if True in matches:
                match_index = matches.index(True)
                name = known_face_names[match_index]

                # Known face → Auto unlock
                if name.lower() == "nitin":
                    arduino.write(b'1')
                    time.sleep(5)

            else:
                send_unknown_alert(frame)

            top, right, bottom, left = face_location

            cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)

            cv2.putText(frame, name, (left, top-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        cv2.imshow("Smart Door Lock", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    except Exception as e:
        print("Connection Error:", e)
        time.sleep(1)

cv2.destroyAllWindows()
