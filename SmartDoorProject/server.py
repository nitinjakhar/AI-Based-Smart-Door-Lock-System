import cv2
import face_recognition
import os
import requests
import numpy as np
import time

ESP32_URL = "http://10.199.43.169/capture"

# ===============================
# Load Known Faces
# ===============================

known_face_encodings = []
known_face_names = []

path = "known_faces"

for file in os.listdir(path):
    image_path = os.path.join(path, file)
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)

    if len(encodings) > 0:
        known_face_encodings.append(encodings[0])
        known_face_names.append(os.path.splitext(file)[0])
        print(f"{file} loaded successfully")
    else:
        print(f"No face found in {file}")

print("Known faces loaded.\n")

# ===============================
# Main Loop
# ===============================

while True:
    try:
        response = requests.get(ESP32_URL, timeout=5)

        img_array = np.array(bytearray(response.content), dtype=np.uint8)
        frame = cv2.imdecode(img_array, -1)

        if frame is None:
            print("Frame decode failed")
            continue

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

            top, right, bottom, left = face_location

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("Smart Door Camera", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    except Exception as e:
        print("Connection error:", e)
        time.sleep(1)
        continue

cv2.destroyAllWindows()
