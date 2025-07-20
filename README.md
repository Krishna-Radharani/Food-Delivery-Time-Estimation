# 🚚 Food Delivery Time Prediction

An intelligent machine learning project that predicts food delivery time using geolocation, weather data, and user input — designed with simplicity, modularity, and real-world usability in mind.

![App Screenshot](IMG2.png)
![App Screenshot](IMG3.png)
![App Screenshot](IMG4.png)
![App Screenshot](IMG5.png)
---

## 📌 Project Highlights

- 🗺️ Location-based predictions using geocoding and weather APIs  
- ⏱️ **Linear Regression** to estimate **Pickup Time**  
- 🔁 Final ETA prediction using **XGBoost** and **LightGBM**  
- 📍 Map-based input for delivery and restaurant locations  
- ⚡ Real-time inference via **Streamlit** deployment  

---
## 🛠️ Tech Stack
- 🐍 Python

- 📊 Pandas, NumPy

- 🧠 scikit-learn, XGBoost, LightGBM

- 🌐 Streamlit (frontend & deployment)

- 📍OpenStreeMap,Geoapify

- ☁️ OpenWeatherMap API

## Insatallation
1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/food-delivery-time-prediction.git
   cd food-delivery-time-prediction
   pip install -r requirements.txt
   streamlit run app.py

## 🧠 Model Architecture

### Step 1: Predict Pickup Time  
A **Linear Regression** model is trained to predict the time a restaurant takes to hand over the food after an order.

### Step 2: Predict Final ETA  
That predicted pickup time is then used as input to a **blended model** (XGBoost + LGBM) to predict final delivery time.

```mermaid
flowchart LR
    A[User Input] --> B[Geocoding API]
    B --> C[Weather API]
    C --> D[Pickup Time - Linear Regression]
    D --> E[ETA Prediction - XGBoost + LGBM]
    E --> F[Predicted Delivery Time]



---

## 🙋 Why Not KNN?

While **K-Nearest Neighbors (KNN)** is a popular method for finding nearby points, this project avoids it due to **limited dataset size** and hardware constraints.

Instead, we use a **real-time API** to fetch the 5 nearest restaurants for any delivery location. This:
- Reduces computation on personal machines
- Is more efficient than training a KNN model on a small dataset
- Makes it scalable and dynamic using live geolocation data







