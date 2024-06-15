from flask import Flask, jsonify, request, render_template
import paho.mqtt.client as mqtt
import sqlite3
import os

BROKER = "localhost"
PORT = 1883
TOPIC_TEMPERATURE = "sensor/temperature"
TOPIC_HUMIDITY = "sensor/humidity"
TOPIC_LIGHT = "sensor/light"
TOPIC_RAIN = "sensor/rain"

app = Flask(__name__)

# Kiểm tra sự tồn tại của tệp cơ sở dữ liệu
db_exists = os.path.exists("iot.db")

# Kết nối và tạo cơ sở dữ liệu nếu chưa tồn tại
conn = sqlite3.connect("iot.db", check_same_thread=False)
c = conn.cursor()

if not db_exists:
     c.execute(
          """CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_type TEXT,
                    value REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"""
     )
     conn.commit()


# Sensor Data
sensor_data = {"temperature": None,
               "humidity": None, "light": None, "rain": None}


# MQTT Callback Functions
def on_connect(client, userdata, flags, rc):
     print(f"Connected with result code {rc}")
     client.subscribe(
          [(TOPIC_TEMPERATURE, 0), (TOPIC_HUMIDITY, 0),
          (TOPIC_LIGHT, 0), (TOPIC_RAIN, 0)]
     )


# MQTT Callback Functions
def on_message(client, userdata, msg):
     global sensor_data
     try:
          payload = msg.payload.decode()
          if msg.topic == TOPIC_TEMPERATURE:
               new_temperature = float(payload)
               if (
                    new_temperature != sensor_data["temperature"]
               ):  # Check for duplicate data
                    sensor_data["temperature"] = new_temperature
                    c.execute(
                    "INSERT INTO sensor_data (sensor_type, value) VALUES (?, ?)",
                    ("temperature", new_temperature),
                    )
          elif msg.topic == TOPIC_HUMIDITY:
               new_humidity = float(payload)
               # Check for duplicate data
               if new_humidity != sensor_data["humidity"]:
                    sensor_data["humidity"] = new_humidity
                    c.execute(
                    "INSERT INTO sensor_data (sensor_type, value) VALUES (?, ?)",
                    ("humidity", new_humidity),
                    )
          elif msg.topic == TOPIC_LIGHT:
               new_light = float(payload)
               if new_light != sensor_data["light"]:  # Check for duplicate data
                    sensor_data["light"] = new_light
                    c.execute(
                    "INSERT INTO sensor_data (sensor_type, value) VALUES (?, ?)",
                    ("light", new_light),
                    )
          elif msg.topic == TOPIC_RAIN:
               new_rain = payload == "True"
               if new_rain != sensor_data["rain"]:  # Check for duplicate data
                    sensor_data["rain"] = new_rain
                    c.execute(
                    "INSERT INTO sensor_data (sensor_type, value) VALUES (?, ?)",
                    ("rain", float(new_rain)),
                    )

          conn.commit()  # Commit once after processing all messages

          print(f"Received {payload} from topic {msg.topic}")
     except ValueError as e:
          print(f"Error decoding message: {e}")


# Khởi tạo MQTT client
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
     c.execute(
          "SELECT * FROM sensor_data WHERE sensor_type=? ORDER BY timestamp DESC LIMIT 1",
          (sensor_type,),
     )     
     data = c.fetchone()
     return jsonify(data)


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
     client.publish("actuator/control", f"SET_TEMP:{min_temp}-{max_temp}")
     return jsonify({"status": "success", "minTemp": min_temp, "maxTemp": max_temp})


@app.route("/control/light", methods=["POST"])
def control_light():
     data = request.json
     min_light = data.get("minLight")
     max_light = data.get("maxLight")
     client.publish("actuator/control", f"SET_LIGHT:{min_light}-{max_light}")
     return jsonify({"status": "success", "minLight": min_light, "maxLight": max_light})


@app.route("/control/humidity", methods=["POST"])
def control_humidity():
     data = request.json
     min_humidity = data.get("minHumidity")
     max_humidity = data.get("maxHumidity")
     client.publish("actuator/control",
                    f"SET_HUMIDITY:{min_humidity}-{max_humidity}")
     return jsonify(
          {"status": "success", "minHumidity": min_humidity, "maxHumidity": max_humidity}
     )


if __name__ == "__main__":
     app.run(debug=True)
