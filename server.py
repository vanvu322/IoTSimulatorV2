from flask import Flask, jsonify, request, render_template
import paho.mqtt.client as mqtt
import sqlite3
import os
import threading
import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def ensure_mqtt_connection():
    if not client.is_connected():
        try:
            client.reconnect()
            logger.info("Reconnected to MQTT broker")
        except Exception as e:
            logger.error(f"Failed to reconnect to MQTT broker: {str(e)}")

try:
    client.connect(BROKER, PORT, 60)
    client.loop_start()
except Exception as e:
    logger.error(f"Failed to connect to MQTT broker: {str(e)}")

@app.route("/control/<control_type>", methods=["POST"])
def control_actuator(control_type):
    ensure_mqtt_connection()
    
    if control_type == "temperature":
        min_val = request.form.get('minTemp')
        max_val = request.form.get('maxTemp')
        command = f"SET_TEMP:{min_val}-{max_val}"
    elif control_type == "light":
        min_val = request.form.get('minLight')
        max_val = request.form.get('maxLight')
        command = f"SET_LIGHT:{min_val}-{max_val}"
    elif control_type == "humidity":
        min_val = request.form.get('minHumidity')
        max_val = request.form.get('maxHumidity')
        command = f"SET_HUMIDITY:{min_val}-{max_val}"
    else:
        return jsonify({"success": False, "error": "Invalid control type"})

    try:
        result = client.publish(ACTUATOR_TOPIC, command)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Successfully sent {control_type} control message: {command}")
            return jsonify({"success": True})
        else:
            logger.error(f"Failed to send {control_type} control message. Error code: {result.rc}")
            return jsonify({"success": False, "error": f"MQTT publish error: {result.rc}"})
    except Exception as e:
        logger.exception(f"An error occurred while sending {control_type} control message")
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
