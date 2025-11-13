# ecosense_dashboard.py
import json
import time

import streamlit as st
import paho.mqtt.client as mqtt

# ---------- CONFIG MQTT (MISMO BROKER Y TOPICS QUE WOKWI) ----------
BROKER = "broker.mqttdashboard.com"
PORT = 1883

TOPIC_DATA = "Sensor/THP2"        # <-- topic que publica el ESP32
TOPIC_CMD_VENT = "Sensor/cmd/vent"
TOPIC_CMD_LAMP = "Sensor/cmd/lamp"

# ---------- ESTADO GLOBAL (session_state) ----------
defaults = {
    "mqtt_client": None,
    "mqtt_connected": False,
    "last_data": None,
    "last_raw_msg": "",
    "last_error": "",
    "last_connect_rc": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------- CALLBACKS MQTT (API V1) ----------
def on_connect(client, userdata, flags, rc):
    """Se ejecuta cuando se conecta al broker."""
    st.session_state.last_connect_rc = rc
    if rc == 0:
        st.session_state.mqtt_connected = True
        try:
            client.subscribe(TOPIC_DATA)
        except Exception as e:
            st.session_state.last_error = f"Error al suscribirse: {e}"
    else:
        st.session_state.mqtt_connected = False
        st.session_state.last_error = f"on_connect rc={rc}"


def on_message(client, userdata, msg):
    """Se ejecuta cuando llega CUALQUIER mensaje."""
    try:
        payload = msg.payload.decode("utf-8", errors="ignore")
        st.session_state.last_raw_msg = f"{msg.topic}: {payload}"

        if msg.topic == TOPIC_DATA:
            data = json.loads(payload)
            st.session_state.last_data = data

    except Exception as e:
        st.session_state.last_error = f"on_message error: {e}"


def on_disconnect(client, userdata, rc):
    st.session_state.mqtt_connected = False
    if rc != 0:
        st.session_state.last_error = f"Desconectado inesperadamente rc={rc}"


def on_log(client, userdata, level, buf):
    # Muy útil para depurar: último log de paho
    st.session_state.last_error = f"LOG MQTT: {buf}"


# ---------- CREAR / RECUPERAR CLIENTE ----------
def get_mqtt_client():
    client = st.session_state.mqtt_client
    if client is None:
        client_id = f"ecosense_dashboard_{int(time.time())}"

        # Forzamos callbacks de API V1 (4 parámetros en on_connect)
        client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        )

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        # Descomenta si quieres ver todavía más logs:
        # client.on_log = on_log

        try:
            # Conexión SÍNCRONA (si falla, lanza excepción)
            client.connect(BROKER, PORT, keepalive=60)
            client.loop_start()
        except Exception as e:
            st.session_state.last_error = f"Error al conectar al broker: {e}"

        st.session_state.mqtt_client = client

    return client


def send_command(topic: str, msg: str):
    """Publica un comando MQTT si hay cliente."""
    client = get_mqtt_client()
    try:
        client.publish(topic, msg)
    except Exception as e:
        st.session_state.last_error = f"Error al publicar comando: {e}"


# =====================================================================
#                                UI
# =====================================================================

st.set_page_config(
    page_title="EcoSense – Proyecto Final",
    page_icon="🌱",
    layout="wide",
)

# Aseguramos que el cliente se inicializa al cargar la página
get_mqtt_client()

st.title("🌱 Dashboard EcoSense – Proyecto Final")
st.caption("por: Juan David Castro Valencia")

st.write(
    "Este panel recibe en tiempo real los datos enviados por el ESP32 en Wokwi "
    "a través de **MQTT**, y permite **controlar la lámpara y el ventilador** "
    "mediante botones o comandos escritos (simulando voz)."
)

# ---------- BARRA DE ESTADO SUPERIOR ----------
status_col1, status_col2 = st.columns([3, 1])

with status_col1:
    if st.session_state.last_data is None:
        st.info(
            "Esperando datos desde el ESP32... "
            "Asegúrate de que el proyecto esté en **Play** en Wokwi "
            "y que el JSON se publique en el topic `Sensor/THP2`."
        )
    else:
        st.success("Datos recibidos desde el ESP32 🎉 (MQTT activo)")

with status_col2:
    if st.session_state.mqtt_connected:
        st.markdown("✅ **MQTT conectado**")
    else:
        st.markdown("⚠️ **MQTT no conectado**")

st.markdown("---")

# ---------- MÉTRICAS PRINCIPALES ----------
st.subheader("📊 Lecturas de sensores (último mensaje)")

col1, col2, col3, col4, col5 = st.columns(5)

data = st.session_state.last_data or {}

temp = data.get("Temp")
hum = data.get("Hum")
luz = data.get("Luz")
gas_ppm = data.get("Gas_ppm")
servo_deg = data.get("Servo_deg")
led_temp = data.get("LED_temp")
vent_on = data.get("Vent_on")
lamp_on = data.get("Lamp_on")

col1.metric("🌡️ Temperatura (°C)", f"{temp:.1f}" if isinstance(temp, (int, float)) else "—")
col2.metric("💧 Humedad (%)", f"{hum:.1f}" if isinstance(hum, (int, float)) else "—")
col3.metric("💡 Luz (raw)", f"{luz}" if luz is not None else "—")
col4.metric("🔥 Gas (ppm)", f"{gas_ppm:.1f}" if isinstance(gas_ppm, (int, float)) else "—")
col5.metric("🌀 Servo (°)", f"{servo_deg}" if servo_deg is not None else "—")

st.markdown("---")

# ---------- CONTROL DE DISPOSITIVOS ----------
st.subheader("📍 Control de dispositivos")

c1, c2 = st.columns(2)

with c1:
    st.markdown("**Lámpara (LED en pin 27)**")
    if st.button("Encender luz"):
        send_command(TOPIC_CMD_LAMP, "ON")
    if st.button("Apagar luz"):
        send_command(TOPIC_CMD_LAMP, "OFF")
    st.write("Estado reportado:", "🔆 Encendida" if lamp_on else "🌑 Apagada")

with c2:
    st.markdown("**Ventilador (Servo + LED en pin 2)**")
    if st.button("Activar ventilador"):
        send_command(TOPIC_CMD_VENT, "ON")
    if st.button("Desactivar ventilador"):
        send_command(TOPIC_CMD_VENT, "OFF")
    st.write("Estado reportado:", "🟢 ON" if vent_on else "⚫ OFF")

st.markdown("---")

# ---------- CONTROL POR TEXTO (SIMULA COMANDO DE VOZ) ----------
st.subheader("🎙️ Control por texto (simulación de voz)")

st.write("Ejemplos: `enciende luz`, `apaga luz`, `enciende ventilador`, `apaga ventilador`")

cmd = st.text_input("Comando de 'voz':")

if st.button("Enviar comando"):
    cmd_norm = cmd.lower().strip()

    if "enciende luz" in cmd_norm:
        send_command(TOPIC_CMD_LAMP, "ON")
    elif "apaga luz" in cmd_norm:
        send_command(TOPIC_CMD_LAMP, "OFF")
    elif "enciende ventilador" in cmd_norm or "enciende abanico" in cmd_norm:
        send_command(TOPIC_CMD_VENT, "ON")
    elif "apaga ventilador" in cmd_norm or "apaga abanico" in cmd_norm:
        send_command(TOPIC_CMD_VENT, "OFF")
    else:
        st.warning("No reconocí el comando. Intenta con: 'enciende luz', 'apaga luz', etc.")

# ---------- SECCIÓN DE DEPURACIÓN ----------
with st.expander("🔍 Depuración (debug MQTT)"):
    st.write("**Último mensaje crudo recibido:**")
    st.code(st.session_state.last_raw_msg or "Ninguno todavía", language="text")

    st.write("**Código de retorno de la última conexión (rc):**", st.session_state.last_connect_rc)
    if st.session_state.last_error:
        st.error(f"Último mensaje de error / log MQTT: {st.session_state.last_error}")
