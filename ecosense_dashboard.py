import streamlit as st
import paho.mqtt.client as mqtt
import json
import time

# -------------------------------------------------------------------
# Configuración de la página
# -------------------------------------------------------------------
st.set_page_config(
    page_title="EcoSense – Lector de Sensor MQTT",
    page_icon="🌱",
    layout="centered"
)

# -------------------------------------------------------------------
# Variables de estado
# -------------------------------------------------------------------
if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = None


def get_mqtt_message(broker, port, topic, client_id):
    """
    Se conecta al broker, se suscribe al topic y espera
    hasta 5 segundos a que llegue un mensaje.
    Devuelve el payload (dict si es JSON, o string si no lo es).
    """
    message_received = {"received": False, "payload": None}

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            message_received["payload"] = payload
            message_received["received"] = True
        except Exception:
            # Si no es JSON válido, guardar como texto plano
            message_received["payload"] = message.payload.decode()
            message_received["received"] = True

    try:
        # Cliente MQTT
        client = mqtt.Client(client_id=client_id)
        client.on_message = on_message

        # Conectar y suscribirse
        client.connect(broker, port, 60)
        client.subscribe(topic)

        # Iniciar loop y esperar mensajes
        client.loop_start()
        timeout = time.time() + 5  # máximo 5 s
        while not message_received["received"] and time.time() < timeout:
            time.sleep(0.1)

        # Cerrar conexión
        client.loop_stop()
        client.disconnect()

        return message_received["payload"]

    except Exception as e:
        # En caso de error, devolvemos un dict con la clave "error"
        return {"error": str(e)}


# -------------------------------------------------------------------
# Sidebar - Configuración (ya apuntando a tu Wokwi)
# -------------------------------------------------------------------
with st.sidebar:
    st.subheader("⚙️ Configuración de Conexión")

    broker = st.text_input(
        "Broker MQTT",
        value="broker.mqttdashboard.com",
        help="Dirección del broker MQTT"
    )

    port = st.number_input(
        "Puerto",
        value=1883,
        min_value=1,
        max_value=65535,
        help="Puerto del broker (generalmente 1883)"
    )

    topic = st.text_input(
        "Tópico",
        value="Sensor/THP2",   # <-- tópico que usa tu ESP32
        help="Tópico MQTT al que deseas suscribirte"
    )

    client_id = st.text_input(
        "ID del Cliente",
        value="ecosense_streamlit",
        help="Identificador único para este cliente"
    )

# -------------------------------------------------------------------
# Título y explicación
# -------------------------------------------------------------------
st.title("🌱 EcoSense – Lector de Sensor MQTT")

with st.expander("ℹ️ Información", expanded=False):
    st.markdown(
        """
        Esta app se conecta al mismo **broker MQTT** que el ESP32 en Wokwi
        y obtiene **un solo mensaje** cada vez que presionas el botón.

        Para este proyecto EcoSense:

        - Broker: `broker.mqttdashboard.com`
        - Puerto: `1883`
        - Tópico de datos: `Sensor/THP2`
        - El ESP32 envía un JSON con campos como:
          `Temp, Hum, Luz, Gas_ppm, Servo_deg, LED_temp, Vent_on, Lamp_on`.

        1. Verifica que el proyecto de Wokwi esté en **Play**.
        2. Pulsa **"Obtener datos del sensor"** para leer el último mensaje.
        """
    )

st.divider()

# -------------------------------------------------------------------
# Botón para obtener datos
# -------------------------------------------------------------------
if st.button("🔄 Obtener datos del sensor", use_container_width=True):
    with st.spinner("Conectando al broker y esperando datos..."):
        sensor_data = get_mqtt_message(broker, int(port), topic, client_id)
        st.session_state.sensor_data = sensor_data

# -------------------------------------------------------------------
# Mostrar resultados
# -------------------------------------------------------------------
if st.session_state.sensor_data:
    st.divider()
    st.subheader("📊 Datos recibidos")

    data = st.session_state.sensor_data

    # ¿Hubo error de conexión?
    if isinstance(data, dict) and "error" in data:
        st.error(f"❌ Error de conexión MQTT: {data['error']}")
    else:
        st.success("✅ Datos recibidos correctamente")

        # Intentamos interpretar el JSON del ESP32 EcoSense
        if isinstance(data, dict):
            # Tomamos los campos más importantes si existen
            temp = data.get("Temp")
            hum = data.get("Hum")
            luz = data.get("Luz")
            gas_ppm = data.get("Gas_ppm")
            servo_deg = data.get("Servo_deg")
            led_temp = data.get("LED_temp")
            vent_on = data.get("Vent_on")
            lamp_on = data.get("Lamp_on")

            # Métricas principales
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(
                    "🌡️ Temperatura (°C)",
                    f"{temp:.1f}" if isinstance(temp, (int, float)) else "—"
                )
                st.metric(
                    "💧 Humedad (%)",
                    f"{hum:.1f}" if isinstance(hum, (int, float)) else "—"
                )
            with c2:
                st.metric("💡 Luz (raw)", str(luz) if luz is not None else "—")
                st.metric(
                    "🔥 Gas (ppm)",
                    f"{gas_ppm:.1f}" if isinstance(gas_ppm, (int, float)) else "—"
                )
            with c3:
                st.metric("🌀 Servo (°)", str(servo_deg) if servo_deg is not None else "—")
                st.metric(
                    "🔥 LED temperatura",
                    "ON" if led_temp else "OFF" if led_temp is not None else "—"
                )

            st.markdown("---")

            # Estado de actuadores (si el ESP32 los envía)
            st.subheader("🔌 Estado de actuadores (según el JSON)")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Lámpara:**", "🔆 Encendida" if lamp_on else "🌑 Apagada")
            with col_b:
                st.write("**Ventilador:**", "🟢 ON" if vent_on else "⚫ OFF")

            # JSON completo para evidencias
            st.markdown("---")
            with st.expander("Ver JSON completo recibido"):
                st.json(data)

        else:
            # Si no es un dict, lo mostramos tal cual
            st.code(str(data), language="text")
