import streamlit as st
import requests
from haversine import haversine, Unit
import pandas as pd
import pickle
import numpy as np

# Optional: You might need to install these if not present
# pip install streamlit-folium folium

from streamlit_folium import st_folium
import folium

st.set_page_config(page_title="Food Delivery ETA", page_icon="🍕", layout="centered")
st.markdown("<h1 style='text-align:center;'>🚚 Food Delivery Time Prediction</h1>", unsafe_allow_html=True)
st.info(
    "This app predicts your food delivery time by considering distance, weather, city and traffic. "
    "You can enter addresses manually **or pick both delivery and restaurant locations on a map**. "
    "If you don't know the restaurant name, you can look up the 5 nearest restaurants after entering a delivery location.",
    icon="💡"
)


# --- Utility Functions (Unchanged logic) ---

def get_lat_lon_from_address(address, api_key='40d27dde73b54e2e82eee7d7b474f15e'):
    endpoint = (
        "https://api.geoapify.com/v1/geocode/search?"
        f"text={address}&"
        f"apiKey={api_key}"
    )
    response = requests.get(endpoint)
    data = response.json()
    features = data.get('features', [])
    if features:
        best_match = features[0]
        coords = best_match['geometry']['coordinates']
        return coords[1], coords[0]
    else:
        return None, None


def reverse_geocode(lat, lon, api_key='40d27dde73b54e2e82eee7d7b474f15e'):
    url = f"https://api.geoapify.com/v1/geocode/reverse?lat={lat}&lon={lon}&apiKey={api_key}"
    response = requests.get(url)
    data = response.json()
    features = data.get('features', [])
    if features:
        props = features[0]['properties']
        return props.get('formatted', props.get('name', 'Unknown'))
    else:
        return "Unknown"


def get_city_from_latlon(lat, lon, api_key='40d27dde73b54e2e82eee7d7b474f15e'):
    url = (
        f"https://api.geoapify.com/v1/geocode/reverse?"
        f"lat={lat}&lon={lon}&type=city&apiKey={api_key}"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        features = data.get('features', [])
        if features:
            city = features[0]['properties'].get('city', 'Unknown')
            return city
        else:
            return None
    except Exception as e:
        print("Error:", e)
        return None


def get_traffic_condition(start, end):
    api_key = "40d27dde73b54e2e82eee7d7b474f15e"
    urls = [
        f"https://api.geoapify.com/v1/routing?waypoints={start}|{end}&mode=drive&traffic=free_flow&apiKey={api_key}",
        f"https://api.geoapify.com/v1/routing?waypoints={start}|{end}&mode=drive&traffic=approximated&apiKey={api_key}"
    ]
    results = []
    for url in urls:
        response = requests.get(url)
        data = response.json()
        duration = data['features'][0]['properties']['time']
        results.append(duration)
    free_flow_time, congested_time = results
    ratio = congested_time / free_flow_time
    if ratio < 1.2:
        return 'Low'
    elif ratio < 1.5:
        return 'Medium'
    elif ratio < 1.7:
        return 'High'
    else:
        return 'Jam'


def infer_vehicle_condition(city):
    if city == "Semi-Urban":
        return 0
    else:
        return 1


with open('city_pop_dict.pkl', 'rb') as f:
    city_pop_dict = pickle.load(f)


def classify_city(city_name):
    key = city_name.strip().lower() if city_name else ''
    if key == 'new delhi':
        return 'Metropolitian'
    pop = city_pop_dict.get(key)
    if pop is None:
        return 'Urban'
    if pop >= 1000000:
        return 'Metropolitian'
    elif pop >= 100000:
        return 'Urban'
    elif pop >= 10000:
        return 'Semi-Urban'
    else:
        return 'Rural'


def get_weather_desc(lat, lon, api_key='c11bd0051eebaf9cca758f2691bbcc83'):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}"
    res = requests.get(url)
    data = res.json()
    if res.status_code != 200:
        print(f"Error: API returned status code {res.status_code}")
        print(data)
        return None
    if 'weather' in data and data['weather']:
        return data['weather'][0]['description']  # e.g., "overcast clouds", "clear sky"
    else:
        print("Error: 'weather' key not found in API response or is empty.")
        print(data)
        return None


def map_oapi_desc_to_model(weather_desc):
    desc = weather_desc.lower()
    if "sand" in desc:
        return "Sandstorms"
    if "fog" in desc or "mist" in desc or "haze" in desc:
        return "Fog"
    if "storm" in desc or "thunder" in desc:
        return "Stormy"
    if "wind" in desc or "breeze" in desc or "gust" in desc:
        return "Windy"
    if "cloud" in desc or "overcast" in desc:
        return "Cloudy"
    if "clear" in desc or "sun" in desc:
        return "Sunny"
    return "Sunny"


def get_nearby_restaurants(address, radius=400, api_key='40d27dde73b54e2e82eee7d7b474f15e'):
    lat, lon = get_lat_lon_from_address(address, api_key)
    if lat is None or lon is None:
        return []
    endpoint = (
        f"https://api.geoapify.com/v2/places?"
        f"categories=catering.restaurant&"
        f"filter=circle:{lon},{lat},{radius}&"
        f"limit=5&"
        f"apiKey={api_key}"
    )
    response = requests.get(endpoint)
    data = response.json()
    features = data.get('features', [])
    restaurants = []
    for place in features:
        props = place.get('properties', {})
        name = props.get('name', 'Unnamed')
        restaurants.append(name)
    return restaurants


# ========== UI Logic for Dual Input Modes ==========

st.markdown("### 1️⃣ Delivery & Restaurant Input Method")
input_mode = st.radio(
    "How do you want to set location addresses?",
    options=["Manual entry", "Pick on map"],
    index=0,
    horizontal=True,
    help="You can use a map interface or traditional text entry"
)

if input_mode == "Manual entry":
    # ---- Delivery Details ----
    st.markdown("#### 📦 Delivery Details")
    delivery_location = st.text_input("Delivery Location", placeholder="E.g., Hiranandani, Powai")

    # ---- Restaurant Details ----
    st.markdown("#### 🍽️ Restaurant Details")
    col1, col2 = st.columns([5, 2])
    with col2:
        dont_know = st.checkbox("Don't know the restaurant?", key="dont_know",
                                help="Click to pick from 5 nearby restaurants")
    with col1:
        manual_restaurant_name = st.text_input(
            "Restaurant Name",
            key="restaurant_name",
            disabled=dont_know,
            placeholder="E.g., Trishna, McDonald's"
        )

    # Suggestions UI
    suggestions = []
    restaurant_from_selectbox = ""
    if dont_know:
        if delivery_location.strip():
            st.caption("👇 Click below to discover restaurants near the delivery address")
            if st.button("Show 5 Nearby Restaurants 🍜"):
                with st.spinner("Finding restaurants nearby..."):
                    suggestions = get_nearby_restaurants(delivery_location)
                st.session_state['restaurant_suggestions'] = suggestions
            suggestions = st.session_state.get('restaurant_suggestions', [])
            if suggestions:
                restaurant_from_selectbox = st.selectbox("Pick a Restaurant Nearby", suggestions, key="rest_select",
                                                         help="Select one of these options, which are closest to your address")
            elif 'restaurant_suggestions' in st.session_state and len(st.session_state['restaurant_suggestions']) == 0:
                st.warning("Sorry, no restaurants found at that location. Try a different delivery location?")
        else:
            st.info("Enter delivery location above to see suggestions.")
    restaurant_name = restaurant_from_selectbox.strip() if dont_know else manual_restaurant_name.strip()
    lat_of_del, lon_of_del, lat_of_rest, lon_of_rest = None, None, None, None

elif input_mode == "Pick on map":
    st.markdown("##### Pick both locations on the map (restaurant & delivery)")
    tab1, tab2 = st.tabs(["📦 Delivery", "🍽️ Restaurant"])
    api_key = '40d27dde73b54e2e82eee7d7b474f15e'  # Geoapify

    with tab1:
        st.write("Choose your delivery location on the map:")
        m1 = folium.Map(location=[28.6448, 77.2167], zoom_start=12)
        m1.add_child(folium.LatLngPopup())
        out1 = st_folium(m1, height=400, width=650,key="delivery_map")
        delivery_location = ""
        lat_of_del, lon_of_del = None, None
        if out1 and out1.get('last_clicked'):
            lat_of_del = out1['last_clicked']['lat']
            lon_of_del = out1['last_clicked']['lng']
            delivery_location = reverse_geocode(lat_of_del, lon_of_del, api_key)
            st.success(f"📍 Selected Delivery: {delivery_location} (lat: {lat_of_del:.4f}, lon: {lon_of_del:.4f})")

    with tab2:
        st.write("Choose your restaurant location on the map:")
        m2 = folium.Map(location=[28.6448, 77.2167], zoom_start=12)
        m2.add_child(folium.LatLngPopup())
        out2 = st_folium(m2, height=400, width=650,key="restaurant_map")
        restaurant_name = ""
        lat_of_rest, lon_of_rest = None, None
        if out2 and out2.get('last_clicked'):
            lat_of_rest = out2['last_clicked']['lat']
            lon_of_rest = out2['last_clicked']['lng']
            restaurant_name = reverse_geocode(lat_of_rest, lon_of_rest, api_key)
            st.success(f"🍽️ Selected Restaurant: {restaurant_name} (lat: {lat_of_rest:.4f}, lon: {lon_of_rest:.4f})")
else:
    delivery_location = ""
    restaurant_name = ""
    lat_of_del = lat_of_rest = lon_of_del = lon_of_rest = None

# ---- Order & Context ----
st.markdown("---")
st.markdown("### 📝 Order Details")
colA, colB, colC = st.columns(3)
with colA:
    order_hour = st.selectbox("Order Hour", list(range(0, 24)), index=12)
with colB:
    order_minute = st.selectbox("Order Minute", list(range(0, 60)))
with colC:
    multiple_deliveries = st.number_input("No. of Orders", min_value=1, value=1)
Festival = st.selectbox("Festival Today?", ["No", "Yes"])

st.markdown("---")

# ---- Submission ----
submit = st.button("🚀 Predict Delivery Time", use_container_width=True)

if submit:
    # --- Validate Inputs Based on Mode ---
    if input_mode == "Manual entry":
        if not delivery_location.strip():
            st.error("Please enter the delivery location.")
            st.stop()
        if not restaurant_name:
            st.error("Please provide or select a restaurant name.")
            st.stop()
        lat_of_del, lon_of_del = get_lat_lon_from_address(delivery_location)
        lat_of_rest, lon_of_rest = get_lat_lon_from_address(restaurant_name)
    elif input_mode == "Pick on map":
        if not (lat_of_del and lon_of_del):
            st.error("Please select a delivery location on the map.")
            st.stop()
        if not (lat_of_rest and lon_of_rest):
            st.error("Please select a restaurant location on the map.")
            st.stop()
        # Names are retrieved via reverse geocoding already; pass through
    else:
        st.error("Something went wrong. Please choose a valid input method.")
        st.stop()

    if (lat_of_rest is None or lon_of_rest is None or
            lat_of_del is None or lon_of_del is None):
        st.warning("Could not geocode one or both locations. Please check your input addresses or selections.")
        st.stop()

    # --- Rest is your original logic ---
    restaurant_coords = (lat_of_rest, lon_of_rest)
    delivery_coords = (lat_of_del, lon_of_del)
    distance_km = haversine(restaurant_coords, delivery_coords, unit=Unit.KILOMETERS)
    city = get_city_from_latlon(lat_of_del, lon_of_del)
    City = classify_city(city)
    start_coord_str = f"{lat_of_rest},{lon_of_rest}"
    end_coord_str = f"{lat_of_del},{lon_of_del}"
    Road_traffic_density = get_traffic_condition(start_coord_str, end_coord_str)
    Order_time_minutes = order_hour * 60 + order_minute

    # Weather autodetect (as before)
    result = get_weather_desc(lat_of_del, lon_of_del)
    weather = map_oapi_desc_to_model(result)

    with open('encoder.pkl', 'rb') as f:
        cols, ordinal_encoder = pickle.load(f)
    input_data = pd.DataFrame([{
        'Weather_conditions': weather,
        'Road_traffic_density': Road_traffic_density,
        'Festival': Festival,
        'City': City
    }])
    encoded_array = ordinal_encoder.transform(input_data[cols])
    sliced_encoded_array = encoded_array[:, 1:]

    with open('pickup_time_model.pkl', 'rb') as f:
        pickup_model = pickle.load(f)
    final_input = np.hstack([[[Order_time_minutes]], sliced_encoded_array])
    pickup_time_predicted = pickup_model.predict(final_input)
    Vehicle_condition = infer_vehicle_condition(City)

    with open('xgb_model.pkl', 'rb') as f:
        xgb_model = pickle.load(f)
    with open('lgbm_model.pkl', 'rb') as f:
        lgbm_model = pickle.load(f)

    X_test = np.hstack([
        encoded_array[:, [0]],
        encoded_array[:, [1]],
        [[Vehicle_condition]],
        [[multiple_deliveries]],
        encoded_array[:, 2:],
        [[Order_time_minutes]],
        [[pickup_time_predicted[0]]],
        [[distance_km]]
    ])
    xgb_predicted = xgb_model.predict(X_test)
    lgbm_predicted = lgbm_model.predict(X_test)
    result = 0.6 * xgb_predicted + 0.4 * lgbm_predicted

    st.success("Prediction Complete!")
    st.write("### 📊 Input Summary:")
    st.write(f"**Delivery Location:** {delivery_location}")
    st.write(f"**Restaurant:** {restaurant_name}")
    st.write(f"**Order Time:** {order_hour:02d}:{order_minute:02d}")
    st.write(f"**Weather (auto-detected):** {weather}")
    st.write(f"**Festival:** {Festival}")
    st.write(f"**Multiple Orders:** {int(multiple_deliveries)}")
    st.write(f"**Distance:** {distance_km:.2f} km")
    st.write(f"**Traffic:** {Road_traffic_density}")
    st.write(f"**City:** {City}")

    st.write("### ⏰ Prediction:")
    st.write(f"<h2 style='color:#388e3c'>{result[0]:.1f} minutes</h2>", unsafe_allow_html=True)

st.markdown(
    "<hr><center><small>Powered by Streamlit | © Your Food Delivery App</small></center>",
    unsafe_allow_html=True
)
