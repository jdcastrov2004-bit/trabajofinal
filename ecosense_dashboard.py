import streamlit as st
import paho.mqtt.client as mqtt
import json
import time

# --------------------------------------------------
# Configuración de la página
# --------------------------------------------------
st.set_page_config(
    page_title="EcoSense – Lector de Sensor MQTT",
    page_icon="🌱",
    layout="centered"
)

# --------------------------------------------------
# Estado
# --------------------------------------------------
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = None

if 'ultimo_crudo' not in st.session_state:
    st.session_state.ultimo_crudo = ""

# ------------ MQTT: obtener un mensaje ----------------
def get_mqtt_message(broker, port, topic, client_id):
    """Obtiene UN mensaje MQTT y solo acepta JSON válido del ESP32."""
    message_received = {"received": False, "payload": None}

    def on_message(client, userdata, message):
        text = message.payload.decode(errors="ignore")
        st.session_state.ultimo_crudo = text

        try:
            payload = json.loads(text)

            if isinstance(payload, dict) and "Temp" in payload:
                message_received["payload"] = payload
                message_received["received"] = True

        except:
            pass

    try:
        client = mqtt.Client(client_id=client_id)
        client.on_message = on_message
        client.connect(broker, port, 60)
        client.subscribe(topic)
        client.loop_start()

        timeout = time.time() + 10
        while not message_received["received"] and time.time() < timeout:
            time.sleep(0.1)

        client.loop_stop()
        client.disconnect()

        return message_received["payload"]

    except Exception as e:
        return {"error": str(e)}


# ------------ Publicar comandos MQTT ----------------
def send_mqtt_command(broker, port, topic, client_id, msg):
    """Envía un mensaje MQTT SIN suscribirse a nada."""
    try:
        client = mqtt.Client(client_id=client_id + "_cmd")
        client.connect(broker, port, 60)
        client.publish(topic, msg)
        client.disconnect()
    except Exception as e:
        st.error(f"Error publicando comando: {e}")


# --------------------------------------------------
# Sidebar - Configuración
# --------------------------------------------------
with st.sidebar:
    st.subheader('⚙️ Configuración MQTT')

    broker = st.text_input('Broker', value='broker.mqttdashboard.com')
    port = st.number_input('Puerto', value=1883)

    topic_data = st.text_input('Tópico datos', value='Sensor/THP2')
    topic_vent = st.text_input('Tópico ventilador', value='Sensor/cmd/vent')
    topic_lamp = st.text_input('Tópico lámpara', value='Sensor/cmd/lamp')

    client_id = st.text_input('ID Cliente', value='ecosense_streamlit')


# --------------------------------------------------
# UI principal
# --------------------------------------------------
st.title("🌱 EcoSense – Lector de Sensor MQTT")

with st.expander("ℹ️ Información"):
    st.write("""
    • Presiona **Obtener datos** para recibir la última lectura enviada por el ESP32.  
    • Los comandos de luz/ventilador se envían por MQTT.  
    • Puedes escribir un comando como "enciende luz" o "apaga ventilador".
    """)

st.divider()

# ------------ Botón de lectura ----------------
if st.button("🔄 Obtener datos del sensor", use_container_width=True):
    with st.spinner("Conectando y esperando datos..."):
        data = get_mqtt_message(broker, port, topic_data, client_id)
        st.session_state.sensor_data = data

# ------------ Mostrar datos ----------------
if st.session_state.sensor_data:

    if isinstance(st.session_state.sensor_data, dict) and "error" in st.session_state.sensor_data:
        st.error("❌ Error: " + st.session_state.sensor_data["error"])
    else:
        data = st.session_state.sensor_data

        st.success("Datos recibidos correctamente ✔")

        # ---- Métricas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🌡️ Temp (°C)", f"{data['Temp']:.1f}")
        col2.metric("💧 Hum (%)", f"{data['Hum']:.1f}")
        col3.metric("💡 Luz", data["Luz"])
        col4.metric("🔥 Gas (ppm)", f"{data['Gas_ppm']:.0f}")

        # ---- Estado de rejilla
        st.subheader("🪟 Estado de rejilla de gas")
        if data["Servo_deg"] > 90:
            st.info("🔓 **Rejilla abierta**")
        else:
            st.info("🔒 **Rejilla cerrada**")

        # ---- Sugerencias inteligentes ----
        st.subheader("💡 Sugerencias")

        if data["Temp"] > 30:
            st.warning("🔥 Hace calor — Te recomendamos encender el ventilador.")

        if data["Luz"] < 2000:
            st.warning("💡 Hay poca luz — Te recomendamos encender la lámpara.")

        if data["Gas_ppm"] > 2000:
            st.error("⚠️ Niveles peligrosos de gas — ventila el ambiente.")

        st.divider()

        # ---------- Control táctil ----------
        st.subheader("📍 Control manual")

        c1, c2 = st.columns(2)

        with c1:
            st.write("💡 **Lámpara**")
            if st.button("Encender luz"):
                send_mqtt_command(broker, port, topic_lamp, client_id, "ON")
            if st.button("Apagar luz"):
                send_mqtt_command(broker, port, topic_lamp, client_id, "OFF")

        with c2:
            st.write("🌀 **Ventilador (LED rojo)**")
            if st.button("Encender ventilador"):
                send_mqtt_command(broker, port, topic_vent, client_id, "ON")
            if st.button("Apagar ventilador"):
                send_mqtt_command(broker, port, topic_vent, client_id, "OFF")

        st.divider()

        # ---------- Comando de voz ----------
        st.subheader("🎙️ Control por comando de voz")

        voice = st.text_input("Escribe tu comando:")

        if st.button("Enviar comando"):
            v = voice.lower()

            if "enciende luz" in v:
                send_mqtt_command(broker, port, topic_lamp, client_id, "ON")
            elif "apaga luz" in v:
                send_mqtt_command(broker, port, topic_lamp, client_id, "OFF")
            elif "enciende ventilador" in v or "enciende abanico" in v:
                send_mqtt_command(broker, port, topic_vent, client_id, "ON")
            elif "apaga ventilador" in v or "apaga abanico" in v:
                send_mqtt_command(broker, port, topic_vent, client_id, "OFF")
            else:
                st.warning("Comando no reconocido. Intenta: 'enciende luz', 'apaga ventilador', etc.")

# ------------ Debug ----------------
with st.expander("📄 Último mensaje crudo MQTT"):
    st.code(st.session_state.ultimo_crudo or "Ninguno")
