import json
import time
import threading

import streamlit as st
import paho.mqtt.client as mqtt

BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC_DATA = "EcoSense/datos"
TOPIC_CMD  = "EcoSense/cmd"

if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = {
        "temp": None,
        "luz": None,
        "gas": None,
        "last_update": None,
    }

if "mqtt_client" not in st.session_state:
    st.session_state.mqtt_client = None

# ========= Callbacks MQTT =========
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC_DATA)
    else:
        print("Error al conectar MQTT:", rc)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        st.session_state.sensor_data["temp"] = data.get("temp")
        st.session_state.sensor_data["luz"] = data.get("luz")
        st.session_state.sensor_data["gas"] = data.get("gas")
        st.session_state.sensor_data["last_update"] = time.strftime(
            "%H:%M:%S", time.localtime()
        )
    except Exception as e:
        print("Error procesando mensaje:", e)

# ========= Inicializar MQTT una sola vez =========
def init_mqtt():
    client = mqtt.Client(client_id="EcoSense-Dashboard")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    return client

if st.session_state.mqtt_client is None:
    st.session_state.mqtt_client = init_mqtt()

client = st.session_state.mqtt_client

# ========= UI =========
st.set_page_config(page_title="EcoSense · Casa Inteligente", layout="wide")
st.title("🌱 EcoSense · Panel de Casa Inteligente")

col_main, col_side = st.columns([2, 1])

with col_main:
    st.subheader("Lecturas en tiempo real")

    temp = st.session_state.sensor_data["temp"]
    luz  = st.session_state.sensor_data["luz"]
    gas  = st.session_state.sensor_data["gas"]

    c1, c2, c3 = st.columns(3)
    c1.metric("🌡 Temperatura (°C)", f"{temp:.1f}" if temp is not None else "—")
    c2.metric("💡 Luz (ADC)", f"{luz}" if luz is not None else "—")
    c3.metric("🧪 Gas (ADC)", f"{gas}" if gas is not None else "—")

    st.write(
        "Última actualización:",
        st.session_state.sensor_data["last_update"] or "sin datos todavía...",
    )

    st.markdown("---")
    st.subheader("Historial (simple)")
    st.write(
        "Más adelante podemos guardar los datos en un DataFrame y graficar tendencias "
        "para el informe del proyecto."
    )

with col_side:
    st.subheader("Control de actuadores")

    st.write("Envía comandos al ESP32 vía MQTT:")

    col_a, col_b = st.columns(2)
    if col_a.button("🚨 ALARMA ON"):
        client.publish(TOPIC_CMD, "ALARMA_ON")
        st.success("Comando enviado: ALARMA_ON")

    if col_b.button("✅ ALARMA OFF"):
        client.publish(TOPIC_CMD, "ALARMA_OFF")
        st.success("Comando enviado: ALARMA_OFF")

    st.markdown("---")
    umbral_temp = st.slider(
        "Umbral de temperatura para alerta (solo visual por ahora)",
        20.0,
        40.0,
        30.0,
    )
    st.info(
        "Luego podemos hacer que el ESP32 reciba este umbral por MQTT "
        "y ajuste la lógica de alarma."
    )

st.caption("Conectado a MQTT: broker.mqttdashboard.com · Topics: EcoSense/datos / EcoSense/cmd")
