# 🚌 Smart Bus Tracking System

🌐 **Live Demo:** https://smart-bus-trackingproduction.up.railway.app/

A full-stack real-time bus tracking web application built with Flask, MySQL, Socket.IO, and AI-powered features.

## 🚀 Features

- 📍 **Real-Time GPS Tracking** – Track buses and their live locations.
- 🤖 **AI Chatbot** – Get bus-related information using an AI chatbot.
- 🎤 **Voice Search** – Search for bus information using voice commands.
- 👨‍💼 **Admin Dashboard** – Manage users, buses, routes, and system data.
- 🚌 **Driver Dashboard** – Update bus location and manage assigned buses.
- 👤 **Passenger Dashboard** – View buses, routes, and live locations.
- ⏱️ **Smart ETA** – Estimate bus arrival time.
- 🔐 **Secure Authentication** – JWT and Bcrypt-based authentication.
- 📊 **History & Analytics** – View bus tracking history and useful statistics.
- 🌙 **Dark Mode** – User-friendly interface with dark mode support.
- 📱 **Responsive Design** – Works on desktop, tablet, and mobile devices.

## 🛠️ Tech Stack

### Frontend
- HTML
- CSS
- JavaScript
- Leaflet.js

### Backend
- Python
- Flask
- Flask-SocketIO

### Database
- MySQL

### AI
- Google Gemini API

### Security
- JWT Authentication
- Bcrypt Password Hashing
- Rate Limiting

### Tools
- Git
- GitHub
- VS Code
- Postman

## 👥 User Roles

### 👨‍💼 Admin
- Manage users
- Manage buses
- Manage routes
- Monitor live buses
- View system analytics

### 🚌 Driver
- View assigned bus
- Share live GPS location
- Update bus status

### 👤 Passenger
- View available buses
- Track buses in real time
- Search routes
- Check estimated arrival time
- Use AI chatbot and voice search

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Smart-Bus-Tracking.git
cd Smart-Bus-Tracking

2. Create Virtual Environment
python -m venv venv

Activate it on Windows:

venv\Scripts\activate
3. Install Dependencies
pip install -r requirements.txt
4. Configure Environment Variables

Create a .env file in the project folder:

GROQ_API_KEY=your_api_key_here

Add your other database/configuration variables if required by the project.

5. Run the Application
python app.py

The application will start on the local server.

📌 Project Highlights
Real-time location tracking using Socket.IO
Interactive maps using Leaflet.js
AI-powered chatbot
Voice-based search
Secure authentication system
Role-based dashboards
MySQL database integration
Responsive user interface

🔮 Future Scope
AI-based traffic prediction
More accurate ETA prediction using Machine Learning
Mobile application
Smart route optimization
Push notifications
Integration with public transport APIs
