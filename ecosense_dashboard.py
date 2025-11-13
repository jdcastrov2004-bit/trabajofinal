import json
import streamlit as st
from paho.mqtt import client as mqtt
from streamlit_autorefresh import st_autorefresh

# ----------------- CONFIGURACIÓN MQTT -----------------
BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC_DATA = "Sensor/THP2"     # Tópico que publica el ESP32 (NO cambiar)
TOPIC_CMD  = "Ecosense/CMD"    # Tópico para comandos desde Streamlit

st.set_page_config(page_title="EcoSense", layout="wide")
st.title("🌱 Dashboard EcoSense – Proyecto Final")
st.caption("por: Juan David Castro Valencia")

# ----------------- ESTADO GLOBAL -----------------
if "mqtt_client" not in st.session_state:
    st.session_state.mqtt_client = None

if "last_data" not in st.session_state:
    st.session_state.last_data = None

if "mqtt_status" not in st.session_state:
    st.session_state.mqtt_status = "🔴 Desconectado de MQTT"


# ----------------- CALLBACKS MQTT -----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.mqtt_status = "🟢 Conectado a MQTT"
        client.subscribe(TOPIC_DATA)
    else:
        st.session_state.mqtt_status = f"🔴 Error al conectar (rc={rc})"


def on_message(client, userdata, msg):
    """Aquí SOLO guardamos los datos, no tocamos la UI."""
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        st.session_state.last_data = data
    except Exception as e:
        # Si falla el JSON, dejamos el último dato bueno
        print("Error procesando JSON:", e, msg.payload)


# ----------------- INICIALIZAR MQTT (UNA SOLA VEZ) -----------------
def init_mqtt():
    if st.session_state.mqtt_client is None:
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(BROKER, PORT, 60)
            client.loop_start()
            st.session_state.mqtt_client = client
        except Exception as e:
            st.session_state.mqtt_status = f"🔴 No se pudo conectar al broker: {e}"


init_mqtt()

# ----------------- AUTO REFRESH CADA 3s -----------------
st_autorefresh(interval=3000, key="ecosense_refresh", limit=None)

# ----------------- UI: ESTADO DE CONEXIÓN -----------------
st.subheader("📡 Estado de conexión")
st.info(st.session_state.mqtt_status)

st.divider()

# ----------------- MÉTRICAS PRINCIPALES -----------------
col1, col2, col3, col4, col5 = st.columns(5)

temp_val = hum_val = luz_val = gas_val = servo_val = "—"

data = st.session_state.last_data
if data is not None:
    temp_val  = f"{data.get('Temp', 0):.1f}"
    hum_val   = f"{data.get('Hum', 0):.1f}"
    luz_val   = str(data.get('Luz', 0))
    gas_val   = f"{data.get('Gas_ppm', 0):.0f}"
    servo_val = str(data.get('Servo_deg', 0))

col1.metric("🌡 Temperatura (°C)", temp_val)
col2.metric("💧 Humedad (%)", hum_val)
col3.metric("💡 Luz (raw)", luz_val)
col4.metric("🔥 Gas (ppm)", gas_val)
col5.metric("🪁 Servo (°)", servo_val)

led_box = st.empty()
if data is not None:
    led_temp = data.get("LED_temp", 0)
    if led_temp == 1:
        led_box.warning("🔥 LED térmico: ENCENDIDO")
    else:
        led_box.info("❄ LED térmico: APAGADO")
else:
    led_box.info("Esperando datos del ESP32…")

st.divider()

# ----------------- CONTROL DE DISPOSITIVOS -----------------
st.subheader("📍 Control de dispositivos")

colA, colB = st.columns(2)

client = st.session_state.mqtt_client

with colA:
    st.markdown("**💡 Luz ambiental (LED GPIO2)**")
    if st.button("Encender luz"):
        if client:
            client.publish(TOPIC_CMD, "LED_ON")
        st.success("Comando enviado: LED_ON")

    if st.button("Apagar luz"):
        if client:
            client.publish(TOPIC_CMD, "LED_OFF")
        st.info("Comando enviado: LED_OFF")

with colB:
    st.markdown("**🌀 Ventilador (servo)**")
    if st.button("Activar ventilador"):
        if client:
            client.publish(TOPIC_CMD, "FAN_ON")
        st.success("Comando enviado: FAN_ON")

    if st.button("Desactivar ventilador"):
        if client:
            client.publish(TOPIC_CMD, "FAN_OFF")
        st.info("Comando enviado: FAN_OFF")

st.divider()

# ----------------- CONTROL POR VOZ (TEXTO) -----------------
st.subheader("🎤 Control por voz (simulado)")
st.caption("Escribe el comando como si lo hubieras dicho: 'enciende luz', 'apaga ventilador', etc.")

voice_cmd = st.text_input("Comando de voz:")

if st.button("Enviar comando de voz"):
    if client and voice_cmd.strip():
        client.publish(TOPIC_CMD, voice_cmd.strip())
        st.success(f"Comando enviado: {voice_cmd.strip()}")
    else:
        st.warning("No hay comando o no hay conexión MQTT.")
