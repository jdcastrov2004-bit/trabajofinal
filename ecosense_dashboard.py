import json
import time
import random

import pandas as pd
import streamlit as st
import paho.mqtt.client as mqtt

# ==========================
# Configuración básica
# ==========================
MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_PORT = 1883
TOPIC_DATOS = "ecosense/datos"   # Publicado por el ESP32
TOPIC_CMD = "ecosense/cmd"       # Comandos desde el dashboard

st.set_page_config(
    page_title="EcoSense · Dashboard",
    layout="wide",
    page_icon="🌱",
)

st.title("🌱 EcoSense · Panel en Tiempo Real")
st.caption("Por: **Juan David Castro Valencia**")

st.markdown(
    """
Este panel se conecta al mismo **broker MQTT** que el ESP32 en Wokwi.

- El ESP32 publica lecturas cada ~2 s en el topic `ecosense/datos`.
- Desde aquí podemos visualizar **temperatura, luz y gas**.
- También enviamos comandos al topic `ecosense/cmd` para controlar la **alarma**.
"""
)

# ==========================
# Estado de la app
# ==========================
if "mqtt_client" not in st.session_state:
    st.session_state.mqtt_client = None

if "lecturas" not in st.session_state:
    # Lista de dicts: {"t": timestamp, "temp": ..., "luz": ..., "gas": ...}
    st.session_state.lecturas = []

if "estado_alarma" not in st.session_state:
    st.session_state.estado_alarma = "OFF"


# ==========================
# Callbacks MQTT
# ==========================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado a MQTT ✔")
        client.subscribe(TOPIC_DATOS)
    else:
        print("Error de conexión MQTT, rc =", rc)


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)

        now = time.time()

        st.session_state.lecturas.append(
            {
                "t": now,
                "temp": float(data.get("temp", 0)),
                "luz": float(data.get("luz", 0)),
                "gas": float(data.get("gas", 0)),
            }
        )

        # Limitar a las últimas 200 lecturas para no crecer infinito
        if len(st.session_state.lecturas) > 200:
            st.session_state.lecturas = st.session_state.lecturas[-200:]

    except Exception as e:
        print("Error al procesar mensaje:", e)


# ==========================
# Inicializar cliente MQTT
# ==========================
def init_mqtt_client():
    client_id = f"ecosense-dashboard-{random.randint(0, 9999)}"
    client = mqtt.Client(client_id=client_id, clean_session=True)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


if st.session_state.mqtt_client is None:
    st.session_state.mqtt_client = init_mqtt_client()


# ==========================
# Layout principal
# ==========================
col_status, col_alarma = st.columns([3, 2])

with col_status:
    st.subheader("📡 Estado de conexión")
    st.write(f"**Broker:** `{MQTT_BROKER}`")
    st.write(f"**Topic datos:** `{TOPIC_DATOS}`")
    st.write(f"**Topic comandos:** `{TOPIC_CMD}`")

with col_alarma:
    st.subheader("🚨 Control de alarma")

    btn_on, btn_off = st.columns(2)
    with btn_on:
        if st.button("Activar alarma"):
            st.session_state.estado_alarma = "ON"
            st.session_state.mqtt_client.publish(TOPIC_CMD, "ALARMA_ON")
    with btn_off:
        if st.button("Desactivar alarma"):
            st.session_state.estado_alarma = "OFF"
            st.session_state.mqtt_client.publish(TOPIC_CMD, "ALARMA_OFF")

    st.markdown(
        f"**Estado actual:** "
        + (
            "🟥 `ALARMA ON`"
            if st.session_state.estado_alarma == "ON"
            else "🟩 `ALARMA OFF`"
        )
    )

st.markdown("---")

# ==========================
# Métricas en tiempo real
# ==========================
if st.session_state.lecturas:
    df = pd.DataFrame(st.session_state.lecturas)
    # Normalizar columna tiempo para gráfico (segundos desde el inicio)
    t0 = df["t"].min()
    df["tiempo_s"] = (df["t"] - t0).round(1)

    ult = df.iloc[-1]

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("🌡️ Temperatura (°C)", f"{ult['temp']:.1f}")
    with m2:
        st.metric("💡 Luz (ADC)", f"{int(ult['luz'])}")
    with m3:
        st.metric("🧪 Gas (ADC)", f"{int(ult['gas'])}")

    st.markdown("### 📈 Evolución de las mediciones")

    g1, g2, g3 = st.columns(3)

    with g1:
        st.line_chart(
            df.set_index("tiempo_s")["temp"],
            height=250,
        )

    with g2:
        st.line_chart(
            df.set_index("tiempo_s")["luz"],
            height=250,
        )

    with g3:
        st.line_chart(
            df.set_index("tiempo_s")["gas"],
            height=250,
        )

else:
    st.info(
        "Esperando datos desde el ESP32... "
        "Asegúrate de que el proyecto en **Wokwi** está en *Play*."
    )

st.markdown("---")
st.caption("EcoSense · Lectura de gas, luz y temperatura en tiempo real usando MQTT.")
