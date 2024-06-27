from flask import Flask, jsonify, request, render_template
import paho.mqtt.client as mqtt
import sqlite3
import os
import threading
import datetime

BROKER = "localhost"
PORT = 1883
TOPICS = {
    'temperature': 'sensor/temperature',
    'humidity': 'sensor/humidity',
    'light': 'sensor/light',
    'rain': 'sensor/rain'
}
ACTUATOR_TOPIC = 'actuator/control'

app = Flask(__name__)

# Kiểm tra tệp cơ sở dữ liệu đã tồn tại chưa
db_exists = os.path.exists("iot.db")

# Kết nối và tạo cơ sở dữ liệu nếu chưa tồn tại
conn = sqlite3.connect("iot.db", check_same_thread=False)
c = conn.cursor()

if not db_exists:
    c.execute(
        """CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                temperature REAL,
                humidity REAL,
                light REAL,
                rain INTEGER
        )"""
    )
    conn.commit()

# Biến tạm thời để lưu trữ dữ liệu từ sensor
temp_data = None
humidity_data = None
light_data = None
rain_data = None
timestamp_data = None

insert_lock = threading.Lock()

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe([(TOPICS[topic], 0) for topic in TOPICS])

def on_message(client, userdata, msg):
    global temp_data, humidity_data, light_data, rain_data, timestamp_data

    try:
        if timestamp_data is None:
            timestamp_data = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        payload = msg.payload.decode()
        
        if msg.topic == TOPICS['temperature']:
            temp_data = round(float(payload), 2)
        elif msg.topic == TOPICS['humidity']:
            humidity_data = round(float(payload), 2)
        elif msg.topic == TOPICS['light']:
            light_data = round(float(payload), 2)
        elif msg.topic == TOPICS['rain']:
            rain_data = int(payload)

        if all(data is not None for data in [temp_data, humidity_data, light_data, rain_data]):
            with insert_lock:
                c.execute("INSERT INTO sensor_data (timestamp, temperature, humidity, light, rain) VALUES (?, ?, ?, ?, ?)",
                        (timestamp_data, temp_data, humidity_data, light_data, rain_data))
                conn.commit()

            # Đặt lại các biến tạm thời và timestamp
            temp_data = None
            humidity_data = None
            light_data = None
            rain_data = None
            timestamp_data = None
            
            print("Inserted data into database.")
    except ValueError as e:
        print(f"Error decoding message: {e}")
    except sqlite3.ProgrammingError as e:
        print(f"Database error: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

client.loop_start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/control")
def control():
    return render_template("control.html")

@app.route("/data/<sensor_type>", methods=["GET"])
def get_sensor_data(sensor_type):
    column_map = {
        "temperature": "temperature",
        "humidity": "humidity",
        "light": "light",
        "rain": "rain"
    }
    
    if sensor_type in column_map:
        column_name = column_map[sensor_type]
        c.execute(f"SELECT timestamp, {column_name} FROM sensor_data ORDER BY timestamp DESC LIMIT 1")
        data = c.fetchone()
        if data:
            result = {"timestamp": data[0], sensor_type: data[1]}
        else:
            result = {"error": "No data found"}
    else:
        result = {"error": "Invalid sensor type"}
    
    return jsonify(result)

@app.route("/data", methods=["GET"])
def get_all_sensor_data():
    c.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC")
    data = c.fetchall()
    return jsonify(data)

@app.route("/control/temperature", methods=["POST"])
def control_temperature():
    data = request.json
    min_temp = data.get("minTemp")
    max_temp = data.get("maxTemp")
    client.publish(ACTUATOR_TOPIC, f"SET_TEMP:{min_temp}-{max_temp}")
    return jsonify({"status": "success", "minTemp": min_temp, "maxTemp": max_temp})

@app.route("/control/light", methods=["POST"])
def control_light():
    data = request.json
    min_light = data.get("minLight")
    max_light = data.get("maxLight")
    client.publish(ACTUATOR_TOPIC, f"SET_LIGHT:{min_light}-{max_light}")
    return jsonify({"status": "success", "minLight": min_light, "maxLight": max_light})

@app.route("/control/humidity", methods=["POST"])
def control_humidity():
    data = request.json
    min_humidity = data.get("minHumidity")
    max_humidity = data.get("maxHumidity")
    client.publish(ACTUATOR_TOPIC, f"SET_HUMIDITY:{min_humidity}-{max_humidity}")
    return jsonify({"status": "success", "minHumidity": min_humidity, "maxHumidity": max_humidity})

if __name__ == "__main__":
    app.run(debug=True)
