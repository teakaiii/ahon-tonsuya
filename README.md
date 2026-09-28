# AHON FloodWatch

**Barangay Tonsuya, Malabon**

A comprehensive flood detection and monitoring system with AI-powered predictions, real-time alerts, and SMS notifications.

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

```powershell
# Install Docker Desktop first, then run:
.\scripts\deploy_docker.ps1
```

### Option 2: Local Development

```powershell
# Backend
.\scripts\deploy_backend.ps1

# Frontend
.\scripts\deploy_frontend.ps1

# AI Model
.\scripts\deploy_ai_model.ps1
```

## 📋 System Overview

### Components

- **Backend**: Django REST API with PostgreSQL database
- **Frontend**: React web dashboard with Material UI
- **Hardware**: Arduino Uno + Water Level Sensor + SIM800L GSM Module
- **Cloud**: Firebase Realtime Database for real-time sync
- **AI**: Scikit-learn based flood prediction models
- **SMS**: Automated SMS alert system

### Features

- Real-time water level monitoring
- AI-powered flood prediction
- Automated SMS alerts to residents
- Interactive web dashboard
- Comprehensive reporting system
- Activity logging and audit trail
- Role-based access control

## 📁 Project Structure

```
ai-flood-detection-system/
├── backend/
│   ├── Django/          # Django REST API
│   ├── api/             # Firebase and SMS services
│   └── ai/              # AI prediction models
├── frontend/
│   └── React/           # React web dashboard
├── hardware/
│   ├── Arduino/         # Arduino firmware
│   └── SIM800L/         # GSM module configuration
├── database/           # Database schema and documentation
├── docs/              # Comprehensive documentation
├── docker/            # Docker configuration
└── scripts/           # Deployment scripts
```

## 🔧 Installation

### Prerequisites

- Python 3.9+
- Node.js 16+
- PostgreSQL 13+ (or use Docker)
- Docker & Docker Compose (optional)
- Git

### Detailed Setup

See [Quick Start Guide](docs/QUICK_START_GUIDE.md) for detailed installation instructions.

## 📖 Documentation

- **[Quick Start Guide](docs/QUICK_START_GUIDE.md)** - Get started quickly
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference
- **[User Manual](docs/USER_MANUAL.md)** - End-user guide
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Development setup
- **[Hardware Setup](docs/HARDWARE_SETUP.md)** - Hardware installation
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Production deployment
- **[Security Guide](docs/SECURITY_GUIDE.md)** - Security best practices
- **[System Architecture](docs/SYSTEM_ARCHITECTURE.md)** - Architecture overview
- **[Database Schema](database/DATABASE_SCHEMA.md)** - Database design
- **[Colab Water-Level Forecast](docs/AHON_FloodWatch_Colab_Forecasting.ipynb)** - Historical visualization and regression forecast
- **[ISO/IEC 25010:2023 Evaluation Plan](docs/ISO_25010_2023_EVALUATION.md)** - Project quality test matrix

## 🔐 Security

- JWT authentication with role-based access control
- Encrypted data at rest and in transit
- Rate limiting and input validation
- SQL injection and XSS prevention
- Comprehensive audit logging

## 🧪 Testing

```bash
# Backend tests
cd backend/Django
python manage.py test

# Frontend tests
cd frontend/React
npm test

# AI model test
cd backend/ai
python flood_prediction.py
```

## 🚢 Deployment

### Docker Deployment

```bash
cd docker
docker-compose up -d --build
```

### Manual Deployment

See [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) for detailed manual deployment instructions.

## 📊 Dashboard Access

After deployment:

- **Frontend**: http://localhost (or your domain)
- **Backend API**: http://localhost:8000/api
- **API Documentation**: http://localhost:8000/swagger/
- **Django Admin**: http://localhost:8000/admin

## 🔑 Default Credentials

After first deployment, create a superuser:

```bash
cd backend/Django
python manage.py createsuperuser
```

## 📱 Hardware Setup

1. Install Arduino IDE
2. Open `hardware/Arduino/flood_detection.ino`
3. Configure settings (Firebase, thresholds, SMS)
4. Upload to Arduino
5. Install hardware following [Hardware Setup Guide](docs/HARDWARE_SETUP.md)

## 🔧 Configuration

### Environment Variables

See `.env.example` files in:
- `backend/Django/.env.example`
- `frontend/React/.env.example`
- `docker/.env.example`

### Required Configuration

- Django SECRET_KEY
- Database credentials
- Firebase project credentials
- SMS gateway API key (if using SMS)

## 🤖 AI Model Training

```powershell
.\scripts\deploy_ai_model.ps1
```

This will:
- Train the flood prediction model
- Save the model to `backend/ai/models/`
- Test the model with sample data

## 📈 Monitoring

### System Status

- Check dashboard for real-time status
- Monitor water levels and alerts
- Review SMS delivery logs
- View system performance metrics

### Logs

- Backend: `backend/Django/logs/django.log`
- Frontend: Browser console
- Hardware: Arduino Serial Monitor

## 🛠️ Troubleshooting

### Common Issues

1. **Django won't start**: Check database connection in .env
2. **Frontend won't build**: Clear node_modules and reinstall
3. **Docker issues**: Ensure Docker Desktop is running
4. **Hardware not connecting**: Check firmware configuration

For detailed troubleshooting, see the relevant documentation.

## 📞 Support

For issues or questions:
- Check documentation in `docs/` directory
- Review deployment scripts in `scripts/` directory
- Check logs for error messages
- Contact technical support

## 📝 License

This project is for educational and community use.

## 🎯 Version

**Current Version**: 1.0.0
**Release Date**: July 13, 2026
**Status**: Production Ready

## 🙏 Acknowledgments

- Barangay Tonsuya, Malabon
- Django REST Framework
- React and Material UI
- Firebase
- Arduino and SIM800L communities
- Scikit-learn team

## 🔄 Changelog

### Version 1.0.0 (2026-07-13)

- Initial release
- Complete Django REST API
- React web dashboard
- Arduino firmware
- AI prediction module
- SMS notification system
- Comprehensive documentation
- Docker deployment support

---

**Built with ❤️ for Barangay Tonsuya - AHON FloodWatch**
