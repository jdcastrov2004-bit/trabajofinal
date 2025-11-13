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


def get_mqtt_message(broker, port, topic, client_id):
    """Obtiene UN mensaje MQTT, pero solo acepta JSON válido del ESP32."""
    message_received = {"received": False, "payload": None}

    def on_message(client, userdata, message):
        # Guardamos siempre el texto crudo por si acaso
        text = message.payload.decode(errors="ignore")
        st.session_state.ultimo_crudo = text

        # Intentar parsear JSON
        try:
            payload = json.loads(text)

            # Aceptamos solo si es un dict y parece venir del ESP32
            if isinstance(payload, dict) and "Temp" in payload:
                message_received["payload"] = payload
                message_received["received"] = True
        except Exception:
            # Si no es JSON válido (por ejemplo "tt"), lo ignoramos
            pass

    try:
        client = mqtt.Client(client_id=client_id)
        client.on_message = on_message
        client.connect(broker, port, 60)
        client.subscribe(topic)
        client.loop_start()

        # Esperar máximo 10 segundos a que llegue UN JSON válido
        timeout = time.time() + 10
        while not message_received["received"] and time.time() < timeout:
            time.sleep(0.1)

        client.loop_stop()
        client.disconnect()

        # Si nunca llegó JSON, devolvemos None
        return message_received["payload"]

    except Exception as e:
        return {"error": str(e)}


# --------------------------------------------------
# Sidebar - Configuración
# --------------------------------------------------
with st.sidebar:
    st.subheader('⚙️ Configuración de Conexión')

    broker = st.text_input(
        'Broker MQTT',
        value='broker.mqttdashboard.com',
        help='Dirección del broker MQTT'
    )

    port = st.number_input(
        'Puerto',
        value=1883,
        min_value=1,
        max_value=65535,
        help='Puerto del broker (generalmente 1883)'
    )

    topic = st.text_input(
        'Tópico',
        value='Sensor/THP2',
        help='Tópico MQTT a suscribirse (debe coincidir con el del ESP32)'
    )

    client_id = st.text_input(
        'ID del Cliente',
        value='ecosense_streamlit',
        help='Identificador único para esta conexión'
    )

# --------------------------------------------------
# Título
# --------------------------------------------------
st.title('🌱 EcoSense – Lector de Sensor MQTT')

# --------------------------------------------------
# Información
# --------------------------------------------------
with st.expander('ℹ️ Información', expanded=False):
    st.markdown("""
    1. En Wokwi, pon el proyecto en **Play**.
    2. Asegúrate de que el ESP32 publique en el tópico **`Sensor/THP2`**.
    3. Presiona **Obtener datos del sensor** para leer el último JSON.
    """)

st.divider()

# --------------------------------------------------
# Botón para obtener datos
# --------------------------------------------------
if st.button('🔄 Obtener datos del sensor', use_container_width=True):
    with st.spinner('Conectando al broker y esperando datos...'):
        sensor_data = get_mqtt_message(broker, int(port), topic, client_id)
        st.session_state.sensor_data = sensor_data

# --------------------------------------------------
# Mostrar resultados
# --------------------------------------------------
if st.session_state.sensor_data:
    st.divider()
    st.subheader('📊 Datos recibidos')

    data = st.session_state.sensor_data

    # Error de conexión
    if isinstance(data, dict) and 'error' in data:
        st.error(f"❌ Error de conexión: {data['error']}")
    else:
        st.success('✅ Datos recibidos correctamente')

        # Si es JSON con campos del ESP32, mostramos métricas bonitas
        if isinstance(data, dict):
            # Métricas principales si existen
            temp = data.get("Temp")
            hum = data.get("Hum")
            luz = data.get("Luz")
            gas = data.get("Gas_ppm")
            servo = data.get("Servo_deg")

            cols = st.columns(5)

            cols[0].metric("Temp (°C)", f"{temp:.1f}" if isinstance(temp, (int, float)) else "—")
            cols[1].metric("Hum (%)", f"{hum:.1f}" if isinstance(hum, (int, float)) else "—")
            cols[2].metric("Luz (raw)", f"{luz}" if luz is not None else "—")
            cols[3].metric("Gas (ppm)", f"{gas:.1f}" if isinstance(gas, (int, float)) else "—")
            cols[4].metric("Servo (°)", f"{servo}" if servo is not None else "—")

            with st.expander('Ver JSON completo'):
                st.json(data)
        else:
            # Si por alguna razón no es dict, lo mostramos tal cual
            st.code(str(data))

# --------------------------------------------------
# Debug opcional
# --------------------------------------------------
with st.expander("🔍 Último mensaje crudo recibido"):
    st.code(st.session_state.ultimo_crudo or "Todavía ninguno")
