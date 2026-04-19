import obd
import time
import requests

BACKEND = "http://127.0.0.1:5000/engine-data"

def start():
    try:
        connection = obd.OBD(fast=False)

        if not connection.is_connected():
            print("❌ OBD not connected")
            return

        print("✅ OBD Connected")

        while True:
            try:
                rpm = connection.query(obd.commands.RPM)
                speed = connection.query(obd.commands.SPEED)
                temp = connection.query(obd.commands.COOLANT_TEMP)

                payload = {
                    "rpm": float(rpm.value.magnitude) if rpm.value else 0,
                    "speed": float(speed.value.magnitude) if speed.value else 0,
                    "temperature": float(temp.value.magnitude) if temp.value else 0,
                    "engine_load": 0
                }

                print("📡 Sending:", payload)
                requests.post(BACKEND, json=payload, timeout=2)

            except Exception as e:
                print("Error:", e)

            time.sleep(2)

    except Exception as e:
        print("❌ OBD INIT ERROR:", e)