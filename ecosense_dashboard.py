# ecosense_dashboard.py
import json
import time

import streamlit as st
import paho.mqtt.client as mqtt

# -------------- CONFIGURACIÓN MQTT -----------------

BROKER = "broker.mqttdashboard.com"
PORT = 1883

TOPIC_DATA = "Sensor/THP2"        # Datos desde el ESP32
TOPIC_CMD_VENT = "Sensor/cmd/vent"
TOPIC_CMD_LAMP = "Sensor/cmd/lamp"

# Último mensaje recibido (lo actualiza el callback)
LATEST_DATA = None

# Guardamos también el estado de conexión para mostrarlo
MQTT_CONNECTED = False


# -------------- CALLBACKS MQTT -----------------

def on_connect(client, userdata, flags, rc):
    global MQTT_CONNECTED
    if rc == 0:
        MQTT_CONNECTED = True
        print("Conectado al broker MQTT")
        # Suscribimos a TODO Sensor/# para estar 100% seguros
        client.subscribe("Sensor/#")
    else:
        MQTT_CONNECTED = False
        print("Error de conexión. Código:", rc)


def on_message(client, userdata, msg):
    """
    Este callback se ejecuta en un hilo aparte.
    NO usamos st.session_state aquí, solo variables globales.
    """
    global LATEST_DATA

    topic = msg.topic
    payload = msg.payload.decode("utf-8", errors="ignore")

    # Solo procesamos el topic que nos interesa
    if topic == TOPIC_DATA:
        try:
            data = json.loads(payload)
            LATEST_DATA = data
            print("Mensaje recibido en Sensor/THP2:", data)
        except Exception as e:
            print("Error al parsear JSON:", e)


def get_mqtt_client():
    """Crea (una sola vez) el cliente MQTT y lo deja en loop_start()."""
    if "mqtt_client" not in st.session_state or st.session_state.mqtt_client is None:
        client_id = f"ecosense-dashboard-{int(time.time())}"

        # API de callbacks v1 (requisito de paho-mqtt 2.x)
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id=client_id
        )

        client.on_connect = on_connect
        client.on_message = on_message

        # Conexión TCP normal al puerto 1883
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_start()

        st.session_state.mqtt_client = client

    return st.session_state.mqtt_client


# -------------- CONFIG STREAMLIT -----------------

st.set_page_config(page_title="EcoSense – Proyecto Final", layout="wide")

st.title("🌱 Dashboard EcoSense – Proyecto Final")
st.caption("por: **Juan David Castro Valencia**")

st.markdown(
    """
Este panel recibe en tiempo real los datos enviados por el ESP32 en Wokwi a través de **MQTT**  
y permite **controlar la lámpara y el ventilador** mediante botones o comandos escritos (simulando voz).
"""
)

st.markdown("---")

# Inicializamos el cliente MQTT
client = get_mqtt_client()

# ----------------- ESTADO DE CONEXIÓN -----------------

status_col = st.empty()
if MQTT_CONNECTED:
    status_col.success("✅ Conectado al broker MQTT. Esperando datos del ESP32...")
else:
    status_col.info(
        "Esperando datos desde el ESP32... "
        "Asegúrate de que el proyecto está en **Play** en Wokwi."
    )

# Leemos el último dato global
data = LATEST_DATA

# ----------------- MÉTRICAS -----------------

col_temp, col_hum, col_luz, col_gas, col_servo = st.columns(5)

if data is None:
    # Si aún no hay datos, dejamos las métricas vacías
    with col_temp:
        st.metric("🌡️ Temperatura (°C)", "---")
    with col_hum:
        st.metric("💧 Humedad (%)", "---")
    with col_luz:
        st.metric("💡 Luz (raw)", "---")
    with col_gas:
        st.metric("🔥 Gas (ppm)", "---")
    with col_servo:
        st.metric("🪫 Servo (°)", "---")
else:
    temp = data.get("Temp", 0.0)
    hum = data.get("Hum", 0.0)
    luz = data.get("Luz", 0)
    gas = data.get("Gas_ppm", 0.0)
    servo_deg = data.get("Servo_deg", 0)
    led_temp = data.get("LED_temp", 0)
    vent_on = bool(data.get("Vent_on", 0))
    lamp_on = bool(data.get("Lamp_on", 0))

    with col_temp:
        st.metric("🌡️ Temperatura (°C)", f"{temp:.1f}")
        st.caption("LED de temperatura encendido" if led_temp else "LED de temperatura apagado")

    with col_hum:
        st.metric("💧 Humedad (%)", f"{hum:.1f}")

    with col_luz:
        st.metric("💡 Luz (raw)", str(luz))

    with col_gas:
        st.metric("🔥 Gas (ppm)", f"{gas:,.1f}")

    with col_servo:
        st.metric("🪫 Servo (°)", f"{servo_deg:.0f}")
        st.caption("Indica la apertura del sistema de ventilación")

st.markdown("---")

# ----------------- CONTROL DE DISPOSITIVOS -----------------

st.subheader("📍 Control de dispositivos ↩️")

col_lamp_btns, col_vent_btns = st.columns(2)

with col_lamp_btns:
    st.markdown("**Lámpara (LED en pin 27)**")
    if st.button("Encender luz"):
        client.publish(TOPIC_CMD_LAMP, "ON")
        st.success("Comando enviado: **Encender luz** (Sensor/cmd/lamp → ON)")
    if st.button("Apagar luz"):
        client.publish(TOPIC_CMD_LAMP, "OFF")
        st.success("Comando enviado: **Apagar luz** (Sensor/cmd/lamp → OFF)")

with col_vent_btns:
    st.markdown("**Ventilador (Servo + LED en pin 2)**")
    if st.button("Activar ventilador"):
        client.publish(TOPIC_CMD_VENT, "ON")
        st.success("Comando enviado: **Activar ventilador** (Sensor/cmd/vent → ON)")
    if st.button("Desactivar ventilador"):
        client.publish(TOPIC_CMD_VENT, "OFF")
        st.success("Comando enviado: **Desactivar ventilador** (Sensor/cmd/vent → OFF)")

# Mostrar estado actual si ya tenemos datos
if data is not None:
    lamp_state = "ENCENDIDA" if lamp_on else "APAGADA"
    vent_state = "ENCENDIDO" if vent_on else "APAGADO"
    st.markdown(
        f"**Estado actual:** 💡 Lámpara: `{lamp_state}` | 🌀 Ventilador: `{vent_state}`"
    )

st.markdown("---")

# ----------------- CONTROL POR “VOZ” (TEXTO) -----------------

st.subheader("🎙️ Control por voz (simulado con texto)")
st.caption("Escribe comandos como: `enciende luz`, `apaga luz`, `enciende ventilador`, `apaga ventilador`…")

voice_cmd = st.text_input("Comando de voz:")

if st.button("Enviar comando"):
    if not voice_cmd.strip():
        st.warning("Por favor escribe un comando.")
    else:
        cmd = voice_cmd.lower()
        sent_any = False

        # Luz
        if any(p in cmd for p in ["enciende luz", "prende luz", "encender luz"]):
            client.publish(TOPIC_CMD_LAMP, "ON")
            st.success("🟢 Comando enviado: **Lámpara ON**")
            sent_any = True
        elif any(p in cmd for p in ["apaga luz", "apagar luz"]):
            client.publish(TOPIC_CMD_LAMP, "OFF")
            st.success("🔴 Comando enviado: **Lámpara OFF**")
            sent_any = True

        # Ventilador
        if any(p in cmd for p in ["enciende ventilador", "encender ventilador", "prende ventilador"]):
            client.publish(TOPIC_CMD_VENT, "ON")
            st.success("🟢 Comando enviado: **Ventilador ON**")
            sent_any = True
        elif any(p in cmd for p in ["apaga ventilador", "apagar ventilador"]):
            client.publish(TOPIC_CMD_VENT, "OFF")
            st.success("🔴 Comando enviado: **Ventilador OFF**")
            sent_any = True

        if not sent_any:
            st.info(
                "No se reconoció ningún dispositivo en el comando. "
                "Prueba con frases como `enciende luz` o `apaga ventilador`."
            )

st.markdown("---")
st.caption("EcoSense • Lectura y control de gas, luz y temperatura en tiempo real usando MQTT.")
