import json
import time
import threading

import streamlit as st
import paho.mqtt.client as mqtt

from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events

# -------------------------
# Configuración general
# -------------------------
BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC_DATA = "ecosense/datos"
TOPIC_CMD = "ecosense/cmd"
CLIENT_ID = "EcoSenseDashboard"

st.set_page_config(page_title="EcoSense · Panel en Tiempo Real", layout="wide")

# -------------------------
# Estado global (por sesión)
# -------------------------
state = st.session_state

if "mqtt_client" not in state:
    state.mqtt_client = None
if "last_data" not in state:
    state.last_data = None
if "last_raw" not in state:
    state.last_raw = ""
if "last_update_ts" not in state:
    state.last_update_ts = None
if "alarm_state" not in state:
    state.alarm_state = "OFF"
if "light_state" not in state:
    state.light_state = "OFF"
if "fan_state" not in state:
    state.fan_state = "OFF"
if "voice_text" not in state:
    state.voice_text = ""
if "mqtt_connected" not in state:
    state.mqtt_connected = False


# -------------------------
# Callbacks MQTT
# -------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        state.mqtt_connected = True
        client.subscribe(TOPIC_DATA)
    else:
        state.mqtt_connected = False


def on_disconnect(client, userdata, rc):
    state.mqtt_connected = False


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="ignore")
    state.last_raw = payload
    state.last_update_ts = time.time()

    try:
        data = json.loads(payload)
        norm = {k.lower(): v for k, v in data.items()}
        state.last_data = norm
    except Exception:
        state.last_data = None


# -------------------------
# Inicializar cliente MQTT
# -------------------------
def start_mqtt():
    client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client.connect(BROKER, PORT, keepalive=60)
    th = threading.Thread(target=client.loop_forever, daemon=True)
    th.start()

    state.mqtt_client = client


if state.mqtt_client is None:
    start_mqtt()

client = state.mqtt_client

# -------------------------
# UI – encabezado
# -------------------------
st.title("🌿 EcoSense · Panel en Tiempo Real")
st.caption("Por: Juan David Castro Valencia")

with st.sidebar:
    st.subheader("ℹ️ Sobre este panel")
    st.write(
        "- Se conecta al mismo **broker MQTT** que el ESP32 en Wokwi.\n"
        "- El ESP32 publica lecturas en el topic `ecosense/datos`.\n"
        "- Aquí puedes ver en tiempo real **temperatura**, **luz** y **gas**.\n"
        "- Desde aquí controlas la **alarma**, la **luz** y el **ventilador**.\n"
        "- Los comandos se envían al topic `ecosense/cmd`."
    )
    st.markdown("---")
    st.write(f"**Broker:** `{BROKER}`")
    st.write(f"**Topic datos:** `{TOPIC_DATA}`")
    st.write(f"**Topic comandos:** `{TOPIC_CMD}`")

col_status, col_alarm = st.columns([2, 1])

# -------------------------
# Estado de conexión
# -------------------------
with col_status:
    st.subheader("📡 Estado de conexión")

    if state.mqtt_connected:
        st.success("Conectado al broker MQTT.")
    else:
        st.warning("Intentando conectar al broker MQTT...")

    if state.last_update_ts is None:
        st.info(
            "Esperando datos desde el ESP32... Asegúrate de que el proyecto en **Wokwi** está en **Play**."
        )
    else:
        elapsed = time.time() - state.last_update_ts
        st.write(f"⏱️ Último mensaje recibido hace **{elapsed:0.1f} s**")

# -------------------------
# Control de alarma
# -------------------------
with col_alarm:
    st.subheader("🚨 Control de alarma")

    btn_on = st.button("Activar alarma")
    btn_off = st.button("Desactivar alarma")

    if client is not None and state.mqtt_connected:
        if btn_on:
            client.publish(TOPIC_CMD, "ALARMA_ON")
            state.alarm_state = "ON"

        if btn_off:
            client.publish(TOPIC_CMD, "ALARMA_OFF")
            state.alarm_state = "OFF"

    estado = "🟥 ALARMA ON" if state.alarm_state == "ON" else "🟩 ALARMA OFF"
    st.write(f"Estado actual: **{estado}**")

st.markdown("---")

# -------------------------
# Controles de luz y ventilador
# -------------------------
col_light, col_fan = st.columns(2)

with col_light:
    st.subheader("💡 Control de luz")

    l_on = st.button("Encender luz", key="btn_light_on")
    l_off = st.button("Apagar luz", key="btn_light_off")

    if client is not None and state.mqtt_connected:
        if l_on:
            client.publish(TOPIC_CMD, "LUZ_ON")
            state.light_state = "ON"
        if l_off:
            client.publish(TOPIC_CMD, "LUZ_OFF")
            state.light_state = "OFF"

    txt_light = "🟡 LUZ ENCENDIDA" if state.light_state == "ON" else "⚫ LUZ APAGADA"
    st.write(f"Estado de luz: **{txt_light}**")

with col_fan:
    st.subheader("🌀 Control de ventilador")

    f_on = st.button("Encender ventilador", key="btn_fan_on")
    f_off = st.button("Apagar ventilador", key="btn_fan_off")

    if client is not None and state.mqtt_connected:
        if f_on:
            client.publish(TOPIC_CMD, "FAN_ON")
            state.fan_state = "ON"
        if f_off:
            client.publish(TOPIC_CMD, "FAN_OFF")
            state.fan_state = "OFF"

    txt_fan = "🟢 VENTILADOR ENCENDIDO" if state.fan_state == "ON" else "🔴 VENTILADOR APAGADO"
    st.write(f"Estado de ventilador: **{txt_fan}**")

st.markdown("---")

# -------------------------
# Control por voz del ventilador
# -------------------------
st.subheader("🎙️ Control por voz del ventilador")

st.write(
    "Pulsa **Escuchar comando**, di algo como:\n"
    "- “Enciende el abanico” / “Enciende el ventilador”\n"
    "- “Apaga el abanico” / “Apaga el ventilador”"
)

stt_button = Button(label="🎙️ Escuchar comando", width=250)
stt_button.js_on_event(
    "button_click",
    CustomJS(
        code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "es-ES";

    recognition.onresult = function (e) {
        var value = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                value += e.results[i][0].transcript;
            }
        }
        if (value !== "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
        }
    }
    recognition.start();
"""
    ),
)

result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT",
    key="voice_listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0,
)

if result and "GET_TEXT" in result:
    cmd_text = result["GET_TEXT"].strip().lower()
    state.voice_text = cmd_text

    st.write(f"🔊 Comando reconocido: **“{cmd_text}”**")

    if client is not None and state.mqtt_connected:
        if "enciende" in cmd_text or "prende" in cmd_text:
            if "abanico" in cmd_text or "ventilador" in cmd_text:
                client.publish(TOPIC_CMD, "FAN_ON")
                state.fan_state = "ON"
                st.success("Comando enviado: FAN_ON")
        elif "apaga" in cmd_text or "apague" in cmd_text:
            if "abanico" in cmd_text or "ventilador" in cmd_text:
                client.publish(TOPIC_CMD, "FAN_OFF")
                state.fan_state = "OFF"
                st.success("Comando enviado: FAN_OFF")

st.markdown("---")

# -------------------------
# Lecturas en tiempo real
# -------------------------
st.subheader("📊 Lecturas recibidas")

if state.last_update_ts is None:
    st.info(
        "Todavía no se han recibido lecturas. Revisa que el ESP32 esté "
        "publicando en el topic correcto."
    )
else:
    data = state.last_data or {}
    temp = (
        data.get("temp")
        or data.get("temperature")
        or data.get("temp_c")
        or data.get("temp_celsius")
    )
    luz = data.get("luz") or data.get("light") or data.get("ldr")
    gas = data.get("gas") or data.get("gas_ppm") or data.get("smoke") or data.get("gasppm")

    c1, c2, c3 = st.columns(3)
    with c1:
        if temp is not None:
            st.metric("🌡️ Temperatura (°C)", f"{float(temp):0.1f}")
        else:
            st.write("Temperatura: (sin dato)")

    with c2:
        if luz is not None:
            st.metric("💡 Luz (ADC)", f"{int(luz)}")
        else:
            st.write("Luz: (sin dato)")

    with c3:
        if gas is not None:
            st.metric("🧪 Gas", f"{float(gas):0.1f}")
        else:
            st.write("Gas: (sin dato)")

    st.markdown("#### Último payload recibido (crudo)")
    st.code(state.last_raw, language="json")

st.markdown("---")
st.caption("EcoSense · Lectura de gas, luz y temperatura en tiempo real usando MQTT.")
