# ecosense_dashboard.py
import json
import random
import time
from datetime import datetime

import streamlit as st

# =========================
#  MQTT opcional
# =========================
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ModuleNotFoundError:
    HAS_MQTT = False


# =========================
#  Configuración básica
# =========================
st.set_page_config(
    page_title="EcoSense · Panel Ambiental",
    page_icon="🌿",
    layout="wide",
)

st.title("🌿 EcoSense · Monitoreo Ambiental")
st.caption("Proyecto final · Interfaces multimodales · por: Juan David Castro Valencia")

with st.sidebar:
    st.subheader("Acerca del proyecto")
    st.write(
        "Este panel muestra los valores de **gas**, **luz** y **temperatura** "
        "obtenidos desde un ESP32 con tres sensores conectados en Wokwi."
    )
    st.write(
        "Si no hay conexión MQTT, el sistema genera datos simulados para poder "
        "probar la interfaz sin hardware."
    )


# =========================
#  Estado inicial
# =========================
if "ultima_lectura" not in st.session_state:
    st.session_state.ultima_lectura = {
        "gas": 0,
        "luz": 0,
        "temp": 0.0,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "origen": "simulado",
    }


# =========================
#  MQTT (opcional / avanzado)
# =========================
def configurar_mqtt():
    broker = st.sidebar.text_input(
        "Broker MQTT",
        value="broker.mqttdashboard.com",
        help="Solo si usas conexión MQTT real.",
    )
    topic = st.sidebar.text_input(
        "Topic de lectura",
        value="ecosense/datos",
        help="Debe coincidir con el topic que publique el ESP32.",
    )

    usar_mqtt = HAS_MQTT and st.sidebar.toggle(
        "Activar MQTT (modo avanzado)", value=False,
        help="Requiere que el paquete 'paho-mqtt' esté instalado en el servidor."
    )

    if not HAS_MQTT and usar_mqtt:
        st.sidebar.warning("En este servidor no está instalado 'paho-mqtt'. "
                           "La app seguirá usando datos simulados.")
        usar_mqtt = False

    return usar_mqtt, broker, topic


def iniciar_cliente_mqtt(broker, topic):
    """Configura el cliente MQTT en modo no bloqueante."""
    client = mqtt.Client("EcoSenseDashboard")

    def on_connect(cl, userdata, flags, rc):
        if rc == 0:
            cl.subscribe(topic)
        else:
            st.toast(f"Error al conectar MQTT (código {rc})", icon="⚠️")

    def on_message(cl, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            data = json.loads(payload)
            # Se espera algo como {"gas": 123, "luz": 456, "temp": 24.5}
            st.session_state.ultima_lectura = {
                "gas": float(data.get("gas", 0)),
                "luz": float(data.get("luz", 0)),
                "temp": float(data.get("temp", 0.0)),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "origen": "MQTT",
                "raw": payload,
            }
        except Exception as e:
            st.session_state.ultima_lectura["raw"] = f"Error al parsear: {e}"

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker, 1883, 60)
        client.loop_start()
        return client
    except Exception as e:
        st.sidebar.error(f"No se pudo conectar al broker MQTT: {e}")
        return None


usar_mqtt, broker, topic = configurar_mqtt()
mqtt_client = None
if usar_mqtt:
    mqtt_client = iniciar_cliente_mqtt(broker, topic)


# =========================
#  Datos simulados
# =========================
def generar_datos_simulados():
    """Genera una lectura de ejemplo cuando no hay MQTT."""
    gas = random.randint(150, 850)          # ADC gas
    luz = random.randint(0, 4095)           # ADC fotoresistor
    temp = round(random.uniform(20, 32), 1) # °C
    st.session_state.ultima_lectura = {
        "gas": gas,
        "luz": luz,
        "temp": temp,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "origen": "simulado",
    }


# Si no usamos MQTT, cada recarga genera valores nuevos
if not usar_mqtt:
    generar_datos_simulados()


# =========================
#  Layout principal
# =========================
lectura = st.session_state.ultima_lectura
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🌡️ Temperatura (°C)", f"{lectura['temp']:.1f}")
with col2:
    st.metric("💡 Luz (ADC)", int(lectura["luz"]))
with col3:
    st.metric("🌫️ Gas (ADC)", int(lectura["gas"]))

st.caption(
    f"Última actualización: **{lectura['timestamp']}** · "
    f"Origen de datos: **{lectura['origen']}**"
)

st.markdown("---")

# =========================
#  Gráfica simple (historial en sesión)
# =========================
if "historial" not in st.session_state:
    st.session_state.historial = []

st.session_state.historial.append(
    {
        "t": datetime.now().strftime("%H:%M:%S"),
        "temp": lectura["temp"],
        "luz": lectura["luz"],
        "gas": lectura["gas"],
    }
)

with st.expander("📈 Ver historial de esta sesión"):
    import pandas as pd

    df = pd.DataFrame(st.session_state.historial)
    st.line_chart(df.set_index("t"))

# =========================
#  Debug / información
# =========================
with st.expander("🛠️ Información técnica / debug"):
    st.write("HAS_MQTT:", HAS_MQTT)
    st.write("Broker configurado:", broker)
    st.write("Topic:", topic)
    st.write("Última lectura completa:", st.session_state.ultima_lectura)

st.info(
    "Este panel puede usarse solo con datos simulados o conectarse a un broker MQTT "
    "si el entorno tiene instalado `paho-mqtt` y el ESP32 está publicando en el topic configurado."
)
