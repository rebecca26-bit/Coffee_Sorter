import streamlit as st
import requests
import time
from collections import deque

st.set_page_config(page_title="Coffee Sorter Dashboard", layout="centered")

st.title("☕ Coffee Bean Sorter Dashboard")
st.write("Real-time updates from sorter_service.py")

# URL of sorter_service
STATUS_URL = "http://localhost:5000/status"

# Store last 50 events
history = deque(maxlen=50)

placeholder = st.empty()

while True:
    try:
        # Query sorter service
        r = requests.get(STATUS_URL, timeout=1).json()

        # Only proceed if we have a valid prediction (not None or "WAITING")
        if r.get("prediction") not in [None, "WAITING"]:
            timestamp = r["timestamp"]
            pred = r["prediction"]
            
            # Fixed: Access nested normalized values with uppercase keys
            rn = r["normalized"]["R"]
            gn = r["normalized"]["G"]
            bn = r["normalized"]["B"]
            
            # Fixed: Access nested raw values with uppercase keys
            rawr = r["raw"]["R"]
            rawg = r["raw"]["G"]
            rawb = r["raw"]["B"]

            history.appendleft({
                "time": timestamp,
                "prediction": pred,
                "r": rn,
                "g": gn,
                "b": bn,
                "raw_r": rawr,
                "raw_g": rawg,
                "raw_b": rawb
            })

            with placeholder.container():
                st.subheader(f"Latest Prediction: **{pred}**")

                col1, col2, col3 = st.columns(3)
                col1.metric("R (norm)", f"{rn:.3f}")
                col2.metric("G (norm)", f"{gn:.3f}")
                col3.metric("B (norm)", f"{bn:.3f}")

                st.write("### Raw RGB Frequencies")
                col4, col5, col6 = st.columns(3)
                col4.metric("Raw R", f"{rawr:.1f}")
                col5.metric("Raw G", f"{rawg:.1f}")
                col6.metric("Raw B", f"{rawb:.1f}")

                st.write("### Recent Events")
                st.dataframe(list(history))
        else:
            # If no valid data yet, show waiting message
            with placeholder.container():
                st.warning("Waiting for sorter_service.py to process first bean…")

        time.sleep(1)

    except Exception as e:
        # More specific error handling
        st.error(f"Error connecting to sorter_service.py: {str(e)}. Retrying...")
        time.sleep(2)
