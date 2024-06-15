import paho.mqtt.client as mqtt

BROKER = 'localhost'
PORT = 1883
TOPIC_CONTROL = 'actuator/control'


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(TOPIC_CONTROL)


def on_message(client, userdata, msg):
    action = msg.payload.decode()
    print(f"Received action: {action}")
    # Giả lập điều khiển actuator
    if action == "ON":
        control_actuator_on()
    elif action == "OFF":
        control_actuator_off()


def control_actuator_on():
    print("Actuator is turned ON")
    # Thêm mã để điều khiển actuator thực sự ở đây


def control_actuator_off():
    print("Actuator is turned OFF")
    # Thêm mã để điều khiển actuator thực sự ở đây


# Khởi tạo MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

client.loop_forever()
