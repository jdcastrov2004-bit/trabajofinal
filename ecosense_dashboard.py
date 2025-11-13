import json
import time
import random

import streamlit as st

# ===================== MQTT (opcional) =====================
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ModuleNotFoundError:
    HAS_MQTT = False

BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC_DATA = "EcoSense/datos"
TOPIC_CMD  = "EcoSense/cmd"

# ===================== Estado inicial =====================
if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = {
        "temp": None,
        "luz": None,
        "gas": None,
        "last_update": None,
    }

if "mqtt_client" not in st.session_state:
    st.session_state.mqtt_client = None

# ===================== Callbacks MQTT =====================
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

# ===================== Inicializar MQTT =====================
def init_mqtt():
    if not HAS_MQTT:
        return None
    client = mqtt.Client(client_id="EcoSense-Dashboard")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    return client

if HAS_MQTT and st.session_state.mqtt_client is None:
    st.session_state.mqtt_client = init_mqtt()

client = st.session_state.mqtt_client

# ===================== UI PRINCIPAL =====================
st.set_page_config(page_title="EcoSense · Casa Inteligente", layout="wide")
st.title("🌱 EcoSense · Panel de Casa Inteligente")

if not HAS_MQTT:
    st.warning(
        "⚠️ El módulo `paho-mqtt` no está instalado en este entorno.\n\n"
        "• La app se ejecuta en **modo demostración** (simulando datos).\n"
        "• Para usar MQTT real en tu computador, instala:\n"
        "  `pip install paho-mqtt`"
    )

col_main, col_side = st.columns([2, 1])

# ===================== Datos (reales o simulados) =====================
with col_main:
    st.subheader("Lecturas en tiempo real")

    # Si no hay MQTT, simulamos valores para que el panel no quede vacío
    if not HAS_MQTT:
        temp = st.session_state.sensor_data["temp"] or random.uniform(22, 30)
        luz  = st.session_state.sensor_data["luz"]  or random.randint(500, 2000)
        gas  = st.session_state.sensor_data["gas"]  or random.randint(200, 800)
        st.session_state.sensor_data["temp"] = temp
        st.session_state.sensor_data["luz"] = luz
        st.session_state.sensor_data["gas"] = gas
        st.session_state.sensor_data["last_update"] = time.strftime(
            "%H:%M:%S", time.localtime()
        )
    else:
        temp = st.session_state.sensor_data["temp"]
        luz  = st.session_state.sensor_data["luz"]
        gas  = st.session_state.sensor_data["gas"]

    c1, c2, c3 = st.columns(3)
    c1.metric("🌡 Temperatura (°C)", f"{temp:.1f}" if temp is not None else "—")
    c2.metric("💡 Luz (ADC)", f"{luz}" if luz is not None else "—")
    c3.metric("🧪 Gas (ADC)", f"{gas}" if gas is not None else "—")

    st.write(
        "⏱ Última actualización:",
        st.session_state.sensor_data["last_update"] or "sin datos todavía...",
    )

    st.markdown("---")
    st.subheader("Historial (idea para el informe)")
    st.write(
        "Más adelante podemos guardar los datos en un DataFrame y graficar tendencias "
        "de temperatura, luz y gas para el reporte del proyecto."
    )

# ===================== Panel de control =====================
with col_side:
    st.subheader("Control de actuadores")

    if HAS_MQTT and client is not None:
        st.write("Envía comandos al ESP32 vía MQTT:")

        col_a, col_b = st.columns(2)
        if col_a.button("🚨 ALARMA ON"):
            client.publish(TOPIC_CMD, "ALARMA_ON")
            st.success("Comando enviado: ALARMA_ON")

        if col_b.button("✅ ALARMA OFF"):
            client.publish(TOPIC_CMD, "ALARMA_OFF")
            st.success("Comando enviado: ALARMA_OFF")
    else:
        st.info(
            "En este entorno no hay MQTT real.\n"
            "En tu PC, con `paho-mqtt` instalado, estos botones enviarán comandos "
            "al ESP32 (topic `EcoSense/cmd`)."
        )

    st.markdown("---")
    umbral_temp = st.slider(
        "Umbral de temperatura para alerta (solo visual por ahora)",
        20.0,
        40.0,
        30.0,
    )
    st.caption(
        "Luego podemos hacer que el ESP32 reciba este umbral por MQTT y ajuste "
        "la lógica interna de alarmas."
    )

st.caption(
    "Conectado (o simulando) MQTT · Broker: broker.mqttdashboard.com · "
    "Topics: EcoSense/datos / EcoSense/cmd"
)
