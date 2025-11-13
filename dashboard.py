import streamlit as st
from paho.mqtt import client as mqtt
import json

BROKER = "broker.mqttdashboard.com"
TOPIC_DATA = "Sensor/THP2"     # <-- EXACTO COMO TU ESP32
TOPIC_CMD  = "Ecosense/CMD"    # <-- PARA COMANDOS NUEVOS

st.set_page_config(page_title="EcoSense", layout="wide")
st.title("🌱 Dashboard EcoSense – Proyecto Final")
st.caption("por: Juan David Castro Valencia")

status = st.empty()

col1, col2, col3, col4 = st.columns(4)

temp_box   = col1.metric("🌡 Temperatura (°C)", "—")
hum_box    = col2.metric("💧 Humedad (%)", "—")
luz_box    = col3.metric("💡 Luz (raw)", "—")
gas_box    = col4.metric("🔥 Gas (ppm)", "—")

servo_box = st.metric("🪁 Servo (°)", "—")
led_temp_status = st.empty()

# ---------------------- MQTT CALLBACK ----------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        status.success("🟢 Conectado a MQTT")
        client.subscribe(TOPIC_DATA)
    else:
        status.error("🔴 Error conectando a MQTT")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()

    try:
        data = json.loads(payload)

        temp_box.metric("🌡 Temperatura (°C)", data["Temp"])
        hum_box.metric("💧 Humedad (%)", data["Hum"])
        luz_box.metric("💡 Luz (raw)", data["Luz"])
        gas_box.metric("🔥 Gas (ppm)", int(data["Gas_ppm"]))

        servo_box.metric("🪁 Servo (°)", data["Servo_deg"])

        if data["LED_temp"] == 1:
            led_temp_status.warning("🔥 LED Térmico: Encendido")
        else:
            led_temp_status.info("❄ LED Térmico: Apagado")

    except Exception as e:
        status.error(f"Error procesando JSON: {e}")
        print(payload)

# ---------------------- MQTT CLIENT ----------------------
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, 1883, 60)
client.loop_start()

st.divider()

# ---------------- CONTROL DE DISPOSITIVOS -----------------
st.subheader("🕹 Control de dispositivos")

colA, colB = st.columns(2)

if colA.button("Encender luz"):
    client.publish(TOPIC_CMD, "LED_ON")
    st.success("💡 Luz encendida")

if colA.button("Apagar luz"):
    client.publish(TOPIC_CMD, "LED_OFF")
    st.info("💡 Luz apagada")

if colB.button("Activar ventilador"):
    client.publish(TOPIC_CMD, "FAN_ON")
    st.success("🌀 Ventilador encendido")

if colB.button("Desactivar ventilador"):
    client.publish(TOPIC_CMD, "FAN_OFF")
    st.info("🌀 Ventilador apagado")

st.divider()

# ----------------- RECONOCIMIENTO POR VOZ -----------------
st.subheader("🎤 Control por voz (opcional)")
st.caption("Di: 'enciende luz', 'apaga ventilador', etc.")

voice_cmd = st.text_input("Comando de voz:")

if st.button("Enviar comando"):
    client.publish(TOPIC_CMD, voice_cmd)
    st.success(f"Enviado: {voice_cmd}")
