# Quill

## Project Overview
Quill is a full-stack application featuring a React Native (Expo) frontend, a Python backend, and Android support. It provides features such as authentication, onboarding, chat, book management, and more.

---

## Table of Contents
- [Features](#features)
- [Setup](#setup)
  - [Frontend (Expo)](#frontend-expo)
  - [Backend (Python)](#backend-python)
  - [Android](#android)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

---

## Features
- User authentication (login, signup, OTP verification, password reset)
- Onboarding flow
- Chat functionality
- Book management (view, upload, preview)
- Profile, settings, notifications, help
- Responsive UI for mobile and Android

---

## Setup

### Frontend (Expo)
1. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```
2. Start the Expo development server:
   ```bash
   npx expo start
   ```

### Backend (Python)
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. (Recommended) Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the backend server:
   ```bash
   python main.py
   ```

### Android
- To run on Android, use Expo Go or build a native APK via EAS or Android Studio.
- Place your debug keystore in `android/app/debug.keystore` (do not commit this file).

---

## Usage
- Access the app via Expo Go or a simulator/emulator.
- The backend API runs on the specified port (default: 8000).
- Update environment variables as needed in `.env` files (not committed).

---

## Contributing
1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License
[MIT](LICENSE) (or specify your license here) 