# 📚 Quill - Modern Document Management & Chat Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-16.x%2B-green.svg)](https://nodejs.org/)

## 🚀 Project Overview
Quill is a powerful, full-stack document management and chat platform that combines the best of modern web and mobile technologies. Built with a React Native (Expo) frontend and a robust Python backend, Quill offers seamless document handling, real-time chat, and secure user authentication across all devices.

### 🌟 Key Features
- **Secure Authentication**
  - Email/Password & OTP verification
  - Secure password reset flow
  - JWT-based session management

- **Document Management**
  - Upload and organize documents
  - Real-time previews
  - Intelligent document processing
  - Version control

- **AI-Powered Chat**
  - Real-time messaging
  - Document context awareness
  - Smart search within conversations

- **Cross-Platform**
  - iOS and Android support via React Native
  - Responsive web interface
  - Offline capabilities

## 🏗 Project Structure

```
quill/
├── backend/                 # Python FastAPI backend
│   ├── app/                 # Application code
│   │   ├── api/             # API endpoints
│   │   ├── core/            # Core functionality
│   │   ├── models/          # Database models
│   │   └── services/        # Business logic
│   ├── tests/               # Backend tests
│   └── requirements.txt     # Python dependencies
│
├── frontend/                # React Native (Expo) app
│   ├── assets/              # Static assets
│   ├── components/          # Reusable components
│   ├── navigation/          # App navigation
│   ├── screens/             # App screens
│   └── App.tsx              # Entry point
│
├── android/                 # Android native code
├── ios/                     # iOS native code (if applicable)
└── docs/                    # Documentation
```

## 🛠 Prerequisites

### For Development
- Node.js 16.x or higher
- Python 3.8+
- npm (v7+) or yarn
- Expo CLI (`npm install -g expo-cli`)
- Git

### For Mobile Development (Optional)
- Android Studio (for Android)
- Xcode (for iOS, macOS only)
- Android SDK & NDK

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/quill.git
cd quill
```

### 2. Set Up Backend
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

### 3. Set Up Frontend
```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install
# or
yarn install

# Start the development server
npx expo start
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in both `backend/` and `frontend/` directories with the following variables:

**Backend (`.env` in backend/)**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/quill
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Frontend (`.env` in frontend/)**
```env
EXPO_PUBLIC_API_URL=http://localhost:8000
# Add other frontend environment variables here
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 🚀 Deployment

### Backend (Production)
```bash
# Install production dependencies
pip install gunicorn uvicorn[standard]

# Run with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### Frontend (Production)
```bash
# Build the production bundle
cd frontend
expo build:web

# The built files will be in the 'web-build' directory
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript) for React/JavaScript
- Write meaningful commit messages following [Conventional Commits](https://www.conventionalcommits.org/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Resources

- [Expo Documentation](https://docs.expo.dev/)
- [React Native Documentation](https://reactnative.dev/docs/getting-started)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)

## 🙋‍♂️ Support

For support, please open an issue in the GitHub repository or contact the maintainers.

---

<div align="center">
  Made with ❤️ by the Quill Team
</div>