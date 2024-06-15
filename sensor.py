import paho.mqtt.client as mqtt
import threading
import time
import random
import signal
import sys

BROKER = 'localhost'
PORT = 1883
TOPIC_TEMPERATURE = 'sensor/temperature'
TOPIC_HUMIDITY = 'sensor/humidity'
TOPIC_LIGHT = 'sensor/light'
TOPIC_RAIN = 'sensor/rain'
ACTUATOR_TOPIC = 'actuator/control'

# Khởi tạo các giá trị môi trường ban đầu
environment = {
    "temperature": 25.0,
    "humidity": 50.0,
    "light": 600,
    "rain": False,
    "min_temp": 15.0,
    "max_temp": 35.0,
    "min_humidity": 30.0,
    "max_humidity": 70.0,
    "min_light": 0,
    "max_light": 1000
}

# Biến để kiểm soát vòng lặp
running = True

def publish(client, topic, message):
    client.publish(topic, message)
    print(f"Published {message} to topic {topic}")

def simulate_environment():
    global environment, running
    while running:
        # Lấy giờ hiện tại
        current_hour = time.localtime().tm_hour

        # Giả lập sự thay đổi của nhiệt độ và độ ẩm dựa trên yêu cầu từ điều khiển
        if environment["rain"]:
            environment["temperature"] -= random.uniform(0.1, 0.5)
            environment["humidity"] += random.uniform(1, 3)
        else:
            environment["temperature"] += random.uniform(0.1, 0.5)
            environment["humidity"] -= random.uniform(0.5, 1.5)

        # Giới hạn giá trị nhiệt độ và độ ẩm theo yêu cầu từ điều khiển
        environment["temperature"] = max(environment["min_temp"], min(environment["max_temp"], environment["temperature"]))
        environment["humidity"] = max(environment["min_humidity"], min(environment["max_humidity"], environment["humidity"]))

        # Giả lập cường độ ánh sáng dựa trên giờ trong ngày
        if 6 <= current_hour <= 18:
            environment["light"] = random.uniform(environment["min_light"], environment["max_light"])  # Ban ngày
        else:
            environment["light"] = random.uniform(environment["min_light"], environment["max_light"])  # Ban đêm

        # Giả lập tình trạng mưa
        environment["rain"] = random.choice([True, False])

        # Cập nhật MQTT
        client.publish(TOPIC_TEMPERATURE, environment["temperature"])
        client.publish(TOPIC_HUMIDITY, environment["humidity"])
        client.publish(TOPIC_LIGHT, environment["light"])
        client.publish(TOPIC_RAIN, str(environment["rain"]))

        time.sleep(10)  # Cập nhật môi trường mỗi 10 giây

def temperature_sensor(client):
    global running
    while running:
        publish(client, TOPIC_TEMPERATURE, environment["temperature"])
        time.sleep(10)

def humidity_sensor(client):
    global running
    while running:
        publish(client, TOPIC_HUMIDITY, environment["humidity"])
        time.sleep(10)

def light_sensor(client):
    global running
    while running:
        publish(client, TOPIC_LIGHT, environment["light"])
        time.sleep(10)

def rain_sensor(client):
    global running
    while running:
        publish(client, TOPIC_RAIN, environment["rain"])
        time.sleep(10)

def signal_handler(sig, frame):
    global running
    print('Stopping...')
    running = False

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(ACTUATOR_TOPIC)

def on_message(client, userdata, msg):
    global environment
    try:
        payload = msg.payload.decode()
        print(f"Received message '{payload}' on topic '{msg.topic}'")
        if msg.topic == ACTUATOR_TOPIC:
            command, value = payload.split(":")
            if command == "SET_TEMP":
                min_temp, max_temp = map(float, value.split("-"))
                environment["min_temp"] = min_temp
                environment["max_temp"] = max_temp
                print(f"Set temperature range to {min_temp}-{max_temp}")
            elif command == "SET_HUMIDITY":
                min_humidity, max_humidity = map(float, value.split("-"))
                environment["min_humidity"] = min_humidity
                environment["max_humidity"] = max_humidity
                print(f"Set humidity range to {min_humidity}-{max_humidity}")
            elif command == "SET_LIGHT":
                min_light, max_light = map(float, value.split("-"))
                environment["min_light"] = min_light
                environment["max_light"] = max_light
                print(f"Set light range to {min_light}-{max_light}")
            else:
                print(f"Unknown command {command}")
    except ValueError as e:
        print(f"Error decoding message: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

client.loop_start()

# Đăng ký xử lý tín hiệu Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

# Khởi tạo thread để giả lập môi trường
environment_thread = threading.Thread(target=simulate_environment)
environment_thread.start()

# Khởi tạo các thread cảm biến
threads = [
    threading.Thread(target=temperature_sensor, args=(client,)),
    threading.Thread(target=humidity_sensor, args=(client,)),
    threading.Thread(target=light_sensor, args=(client,)),
    threading.Thread(target=rain_sensor, args=(client,))
]

for thread in threads:
    thread.start()

# Chờ các thread dừng lại
for thread in threads:
    thread.join()

environment_thread.join()
print('Stopped.')
