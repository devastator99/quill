# Quill

## Project Overview
Quill is a robust full-stack application designed for seamless reading and communication experiences. It features a modern React Native (Expo) frontend, a Python backend, and native Android support. Quill enables users to authenticate, onboard, chat, manage books, and more, all within a responsive, mobile-first interface.

---

## Table of Contents
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [Frontend (Expo)](#frontend-expo)
  - [Backend (Python)](#backend-python)
  - [Android](#android)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Links](#links)

---

## Features
- User authentication (login, signup, OTP verification, password reset)
- Onboarding flow for new users
- Real-time chat functionality
- Book management: view, upload, preview, organize
- User profile, customizable settings, notifications, help
- Responsive UI for mobile and Android
- Modular backend for easy extension

---

## Project Structure
```
quill/
├── backend/         # Python backend (API, models, logic)
├── node_modules/    # Frontend dependencies
├── android/         # Android native project files
├── assets/          # Images, fonts, etc.
├── App.js           # Expo entry point
├── package.json     # Frontend dependencies/config
├── tsconfig.json    # TypeScript config
├── README.md        # Project documentation
└── ...
```

---

## Prerequisites
- Node.js (>= 16.x)
- npm or yarn
- Python 3.8+
- pip
- Expo CLI (`npm install -g expo-cli`)
- (For Android) Android Studio or Expo Go app

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
3. (Optional) For TypeScript support, ensure `tsconfig.json` is configured properly.

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
- For custom builds, follow the [Expo EAS Build docs](https://docs.expo.dev/build/introduction/).

---

## Environment Variables
- Create a `.env` file in the root and/or backend directory as needed.
- Example variables:
  - `API_URL` (frontend)
  - `SECRET_KEY`, `DATABASE_URL` (backend)
- **Do not commit `.env` files.**

---

## Usage
- Access the app via Expo Go or a simulator/emulator.
- The backend API runs on the specified port (default: 8000).
- Update environment variables as needed in `.env` files.
- For production, consider deploying the backend using a WSGI server (e.g., Gunicorn) and configure environment variables securely.

---

## Troubleshooting
- **Dependency Issues:**
  - Delete `node_modules` and `package-lock.json`/`yarn.lock`, then reinstall.
  - For Python, recreate your virtual environment if you encounter version conflicts.
- **Expo Errors:**
  - Ensure you have the latest Expo CLI and compatible Node.js version.
- **Android Build Issues:**
  - Confirm correct keystore placement and configuration.
  - Check Android Studio and SDK versions.

---

## Contributing
1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

**Guidelines:**
- Follow code style and linting rules.
- Write clear commit messages.
- Add tests for new features when possible.
- Document any new functionality in the README.

---

## License
[MIT](LICENSE) (or specify your license here)

---

## Links
- [Expo Documentation](https://docs.expo.dev/)
- [React Native Docs](https://reactnative.dev/docs/getting-started)
- [Python Official Site](https://www.python.org/)
- [FastAPI (if used)](https://fastapi.tiangolo.com/)
- [Android Studio](https://developer.android.com/studio)

For questions or support, please open an issue or contact the maintainers.