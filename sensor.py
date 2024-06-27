import paho.mqtt.client as mqtt
import threading
import time
import random
import signal
import sys

BROKER = 'localhost'
PORT = 1883
TOPICS = {
    'temperature': 'sensor/temperature',
    'humidity': 'sensor/humidity',
    'light': 'sensor/light',
    'rain': 'sensor/rain'
}
ACTUATOR_TOPIC = 'actuator/control'

# Giá trị môi trường ban đầu
environment = {
    "temperature": 25.0,
    "humidity": 50.0,
    "light": 600,
    "rain": 0,
    "min_temp": 15.0,
    "max_temp": 35.0,
    "min_humidity": 30.0,
    "max_humidity": 70.0,
    "min_light": 0,
    "max_light": 1000
}

# Biến điều khiển vòng lặp chính
running = True

def publish(client, topic, message):
    client.publish(topic, message)
    print(f"Đã gửi {message} đến topic {topic}")

def simulate_environment(client):
    global environment, running
    while running:
        current_hour = time.localtime().tm_hour

        if environment["rain"]:
            environment["temperature"] -= random.uniform(0.1, 0.5)
            environment["humidity"] += random.uniform(1, 3)
        else:
            environment["temperature"] += random.uniform(0.1, 0.5)
            environment["humidity"] -= random.uniform(0.5, 1.5)

        environment["temperature"] = max(environment["min_temp"], min(environment["max_temp"], environment["temperature"]))
        environment["humidity"] = max(environment["min_humidity"], min(environment["max_humidity"], environment["humidity"]))

        if 6 <= current_hour <= 18:
            environment["light"] = random.uniform(environment["min_light"], environment["max_light"])
        else:
            environment["light"] = random.uniform(environment["min_light"], environment["max_light"])

        environment["rain"] = random.choice([1, 0])

        for key, topic in TOPICS.items():
            if key == 'rain':
                publish(client, topic, str(environment[key]))
            else:
                publish(client, topic, environment[key])

        time.sleep(10)

def signal_handler(sig, frame):
    global running
    print('Đang dừng...')
    running = False

def on_connect(client, userdata, flags, rc):
    print(f"Đã kết nối với mã kết quả {rc}")
    client.subscribe(ACTUATOR_TOPIC)

def on_message(client, userdata, msg):
    global environment
    try:
        payload = msg.payload.decode()
        print(f"Nhận tin nhắn '{payload}' trên topic '{msg.topic}'")
        if msg.topic == ACTUATOR_TOPIC:
            command, value = payload.split(":")
            if command == "SET_TEMP":
                min_temp, max_temp = map(float, value.split("-"))
                environment["min_temp"] = min_temp
                environment["max_temp"] = max_temp
                print(f"Đã đặt khoảng nhiệt độ từ {min_temp}-{max_temp}")
            elif command == "SET_HUMIDITY":
                min_humidity, max_humidity = map(float, value.split("-"))
                environment["min_humidity"] = min_humidity
                environment["max_humidity"] = max_humidity
                print(f"Đã đặt khoảng độ ẩm từ {min_humidity}-{max_humidity}")
            elif command == "SET_LIGHT":
                min_light, max_light = map(float, value.split("-"))
                environment["min_light"] = min_light
                environment["max_light"] = max_light
                print(f"Đã đặt khoảng ánh sáng từ {min_light}-{max_light}")
            else:
                print(f"Lệnh không xác định {command}")
    except ValueError as e:
        print(f"Lỗi khi giải mã tin nhắn: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

client.loop_start()

signal.signal(signal.SIGINT, signal_handler)

environment_thread = threading.Thread(target=simulate_environment, args=(client,))
environment_thread.start()

try:
    while running:
        time.sleep(1)
except KeyboardInterrupt:
    print("Bị ngắt, đang dừng...")
    running = False

environment_thread.join()
print('Đã dừng.')
