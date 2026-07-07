# 🌟 Nathan - Localized Social & Safety Network Backend

Nathan is a feature-rich, high-performance Django-based backend application designed to support a localized social connection, local commerce, and real-time safety network. It combines geographical proximity algorithms (using the Haversine distance formula) with real-time bidirectional communication (via WebSockets) to connect users with nearby neighbors, listings, events, recommendations, and local safety alerts.

---

## 🚀 Key Features

### 👤 1. Accounts & Proximity Profiles
* **Secure Authentication:** JWT-based register, login, profile view, password update, and OTP verification flow.
* **Geotagged Profiles:** Custom profile details storing user latitude, longitude, and custom `distance_radius` settings.
* **Friendship Network:** Full-featured friendship system to send, accept, reject, list, and remove friend requests.
* **Nearby Users:** Locate nearby users based on geographic coordinates and distance preferences.

### 💬 2. Real-Time Messaging & Chat
* **Bidirectional WebSockets:** Instant communication utilizing Django Channels and Daphne.
* **Conversation History:** Connect to `/ws/chat/<conversation_id>/` to automatically retrieve conversation logs and chat in real-time.
* **Active Chats Feed:** Connect to `/ws/conversations/` to receive real-time updates whenever a new message lands.

### 📢 3. Location-Based Safety Alerts
* **Alert Categories:** Support for standard alerts, missing person reports, and emergencies.
* **Privacy Configurations:** Scope visibility to `anyone`, `friends`, or `only_me`.
* **Feed Filters:** Special `/api/alerts/active/` endpoint retrieving active local alerts within the last 24 hours.

### 🛒 4. Classified Listings
* **Listing Feeds:** Post and filter local goods or services.
* **Media Uploads:** Upload and manage up to 10 photos per listing.
* **Geographical Filtering:** Find listings near you using the custom search radius, category, status (`free` or `for_sale`), and title searches.

### 📅 5. Events & Recommendations
* **Dynamic Feed:** The `/api/events/upcoming/` action aggregates upcoming events, recommendations, and looking-for posts.
* **Sorting by Proximity:** Events are calculated using the Haversine formula and sorted with nearest locations prioritized first.

---

## 🛠️ Technology Stack

* **Core Framework:** Django 5.2+ & Python 3
* **API Toolkit:** Django REST Framework (DRF)
* **Real-time Engine:** Django Channels 4.0 & Daphne ASGI server
* **Authentication:** SimpleJWT (JSON Web Tokens)
* **API Documentation:** Swagger UI & ReDoc (via `drf-yasg`)
* **Database:** SQLite (default/development) or PostgreSQL support

---

## 📁 Repository Structure

```text
├── config/             # Project settings, URL routing, WSGI/ASGI configurations
├── accounts/           # User authentication, profiles, proximity calculations, and friends
├── alert/              # Emergency, missing person, and safety alert systems
├── events/             # Local events and upcoming combined radius feeds
├── listing/            # Classified listings with image uploads and radius search
├── looking_for/        # Local requests and classified needs
├── message/            # Private chat history and WebSocket consumers
├── notifications/      # WebSocket-based push notification system & signals
├── posts/              # Standard social/feed posts
├── recommendations/    # User-curated local recommendations
├── manage.py           # Django administrative task runner
└── requirements.txt    # Application dependencies
```

---

## 🏁 Getting Started

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/nahid2887/Nathan.git
cd Nathan

# Create and activate virtual environment
python -m venv env
# On Windows:
.\env\Scripts\activate
# On macOS/Linux:
source env/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Migrations
Run the migrations to create the database schema:
```bash
python manage.py migrate
```

### 4. Run the Development Server
Since the backend utilizes Django Channels and WebSockets, run the server using `daphne` or the ASGI-configured dev server:
```bash
python manage.py runserver 0.0.0.0:8003
```

---

## 📝 API & WebSocket Documentation

### REST API Documentation
Once the server is running, the interactive Swagger UI and API endpoints documentation can be accessed at:
👉 **[http://localhost:8003/swagger/](http://localhost:8003/swagger/)**

### WebSocket Endpoints
All WebSocket endpoints require JWT authentication.

1. **Conversations Feed WebSocket:**
   * **URL:** `ws://<host>/ws/conversations/`
   * **Purpose:** Real-time updates on active conversations list.

2. **Direct Chat WebSocket:**
   * **URL:** `ws://<host>/ws/chat/<conversation_id>/`
   * **Purpose:** Send and receive message logs in a specific chat.

3. **Notifications WebSocket:**
   * **URL:** `ws://<host>/ws/notifications/`
   * **Purpose:** User notifications for alerts, events, etc.
