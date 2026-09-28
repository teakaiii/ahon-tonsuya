# API Documentation

## Overview

AHON FloodWatch provides a RESTful API built with Django REST Framework. All API endpoints are prefixed with `/api/`.

## Base URL

```
http://localhost:8000/api
```

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Authentication Endpoints

#### Login
```
POST /api/auth/login/
```

**Request Body:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

#### Register (Admin Only)
```
POST /api/auth/register/
```

**Request Body:**
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "password_confirm": "password123",
  "role": "staff"
}
```

#### Logout
```
POST /api/auth/logout/
```

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Get Profile
```
GET /api/auth/profile/
```

#### Change Password
```
POST /api/auth/change-password/
```

**Request Body:**
```json
{
  "old_password": "oldpass123",
  "new_password": "newpass123"
}
```

## Water Level Endpoints

#### List Water Level Readings
```
GET /api/water-level/
```

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page
- `status`: Filter by status (Normal, Alert, Warning, Danger)
- `start_date`: Filter by start date (ISO 8601)
- `end_date`: Filter by end date (ISO 8601)

#### Get Current Water Level
```
GET /api/water-level/current/
```

**Response:**
```json
{
  "reading_id": "uuid",
  "water_level_cm": 45.5,
  "status": "Alert",
  "timestamp": "2026-07-13T14:30:00Z",
  "sensor_status": "online",
  "gsm_status": "connected"
}
```

#### Create Water Level Reading (Admin Only)
```
POST /api/water-level/create/
```

**Request Body:**
```json
{
  "water_level_cm": 50.0,
  "sensor_status": "online",
  "gsm_status": "connected"
}
```

#### Get Water Level History
```
GET /api/water-level/history/
```

**Query Parameters:**
- `hours`: Number of hours to look back (default: 24)

#### Get Water Level Statistics
```
GET /api/water-level/statistics/
```

**Response:**
```json
{
  "average": 45.5,
  "maximum": 75.0,
  "minimum": 25.0,
  "total_readings": 1000
}
```

## Residents Endpoints

#### List Residents
```
GET /api/residents/
```

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page
- `status`: Filter by status (active, inactive, evacuated)
- `purok_zone`: Filter by purok/zone

#### Create Resident (Admin Only)
```
POST /api/residents/create/
```

**Request Body:**
```json
{
  "full_name": "John Doe",
  "mobile_number": "+639123456789",
  "address": "123 Test St",
  "purok_zone": "Zone 1",
  "status": "active",
  "sms_enabled": true
}
```

#### Update Resident (Admin Only)
```
PUT /api/residents/{resident_id}/
```

#### Delete Resident (Admin Only)
```
DELETE /api/residents/{resident_id}/
```

#### Get Active Residents
```
GET /api/residents/active/
```

#### Get Residents by Purok
```
GET /api/residents/purok/{purok_zone}/
```

#### Get Resident Statistics
```
GET /api/residents/statistics/
```

## Alerts Endpoints

#### List Alerts
```
GET /api/alerts/
```

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page
- `alert_level`: Filter by alert level
- `is_active`: Filter by active status

#### Create Alert (Admin Only)
```
POST /api/alerts/create/
```

**Request Body:**
```json
{
  "reading_id": "uuid",
  "alert_level": "Warning",
  "message": "Warning flood level detected"
}
```

#### Get Active Alerts
```
GET /api/alerts/active/
```

#### Get Recent Alerts
```
GET /api/alerts/recent/
```

**Query Parameters:**
- `hours`: Number of hours to look back (default: 24)

#### Get Alert Statistics
```
GET /api/alerts/statistics/
```

## SMS Endpoints

#### List SMS Logs
```
GET /api/sms/
```

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page
- `delivery_status`: Filter by delivery status
- `start_date`: Filter by start date
- `end_date`: Filter by end date

#### Create SMS Log (Admin Only)
```
POST /api/sms/create/
```

**Request Body:**
```json
{
  "recipient": "+639123456789",
  "message": "Test SMS message"
}
```

#### Get SMS Statistics
```
GET /api/sms/statistics/
```

**Query Parameters:**
- `hours`: Number of hours to look back (default: 24)

#### Get Failed SMS
```
GET /api/sms/failed/
```

## Predictions Endpoints

#### List Predictions
```
GET /api/predictions/
```

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page
- `severity`: Filter by severity

#### Create Prediction (Admin Only)
```
POST /api/predictions/create/
```

**Request Body:**
```json
{
  "water_level_cm": 50.0,
  "flood_probability": 65.5,
  "severity": "medium",
  "alert_level": "Alert",
  "confidence_score": 75.0
}
```

#### Get Latest Prediction
```
GET /api/predictions/latest/
```

#### Get Prediction Statistics
```
GET /api/predictions/statistics/
```

## AI Models Endpoints

#### List AI Models
```
GET /api/ai-models/
```

#### Create AI Model (Admin Only)
```
POST /api/ai-models/create/
```

**Request Body:**
```json
{
  "model_name": "RandomForest",
  "version": "1.0",
  "accuracy": 0.92,
  "precision": 0.90,
  "recall": 0.88,
  "f1_score": 0.89
}
```

#### Get Active AI Model
```
GET /api/ai-models/active/
```

## Reports Endpoints

#### List Reports
```
GET /api/reports/
```

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page
- `report_type`: Filter by report type

#### Create Report (Admin Only)
```
POST /api/reports/create/
```

**Request Body:**
```json
{
  "report_type": "daily",
  "file_format": "pdf"
}
```

#### Generate Report
```
GET /api/reports/generate/
```

**Query Parameters:**
- `type`: Report type (daily, weekly, monthly, annual)
- `format`: File format (pdf, xlsx, csv)

#### Get Report Statistics
```
GET /api/reports/statistics/
```

## Notifications Endpoints

#### List Notifications
```
GET /api/notifications/
```

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page
- `is_read`: Filter by read status

#### Create Notification (Admin Only)
```
POST /api/notifications/create/
```

**Request Body:**
```json
{
  "title": "System Alert",
  "message": "Water level has reached warning threshold",
  "type": "warning"
}
```

#### Mark Notification as Read
```
PATCH /api/notifications/{notif_id}/
```

**Request Body:**
```json
{
  "is_read": true
}
```

#### Mark All Notifications as Read
```
POST /api/notifications/mark-all-read/
```

#### Get Unread Count
```
GET /api/notifications/unread-count/
```

**Response:**
```json
{
  "unread_count": 5
}
```

## Settings Endpoints

#### List System Settings (Admin Only)
```
GET /api/settings/
```

#### Create System Setting (Admin Only)
```
POST /api/settings/create/
```

**Request Body:**
```json
{
  "key": "setting_name",
  "value": "setting_value",
  "description": "Setting description"
}
```

#### Update System Setting (Admin Only)
```
PUT /api/settings/{setting_id}/
```

#### Delete System Setting (Admin Only)
```
DELETE /api/settings/{setting_id}/
```

#### Get Flood Thresholds
```
GET /api/settings/flood-thresholds/
```

**Response:**
```json
{
  "normal_threshold": 0,
  "warning_threshold": 2,
  "danger_threshold": 3
}
```

These boundaries apply to the calibrated 0-4 cm sensor. Normal is below 2 cm, Warning begins at 2 cm, and Danger begins at 3 cm.

## Dashboard Endpoints

#### Get Dashboard Overview
```
GET /api/dashboard/overview/
```

**Response:**
```json
{
  "current_water_level": {
    "water_level_cm": 45.5,
    "status": "Alert",
    "timestamp": "2026-07-13T14:30:00Z",
    "sensor_status": "online",
    "gsm_status": "connected"
  },
  "alerts": {
    "active_count": 1,
    "recent_count": 5
  },
  "residents": {
    "total": 150,
    "active": 145,
    "sms_enabled": 140
  },
  "sms": {
    "sent_last_24h": 50,
    "failed_last_24h": 2
  },
  "prediction": {
    "flood_probability": 65.5,
    "severity": "medium",
    "alert_level": "Alert",
    "confidence": 75.0
  }
}
```

#### Get Water Level Trend
```
GET /api/dashboard/water-level-trend/
```

**Query Parameters:**
- `hours`: Number of hours to look back (default: 24)

#### Get Alert History
```
GET /api/dashboard/alert-history/
```

**Query Parameters:**
- `hours`: Number of hours to look back (default: 24)

#### Get SMS Statistics
```
GET /api/dashboard/sms-statistics/
```

**Query Parameters:**
- `hours`: Number of hours to look back (default: 24)

#### Get Prediction Accuracy
```
GET /api/dashboard/prediction-accuracy/
```

#### Get Resident Distribution
```
GET /api/dashboard/resident-distribution/
```

#### Get System Status
```
GET /api/dashboard/system-status/
```

#### Get Water-Level Regression Forecast
```
GET /api/dashboard/water-level-forecast/
```

Requires authentication. The endpoint filters historical values to the calibrated 0-4 cm range, resamples valid readings, and evaluates a Random Forest regressor on a chronological holdout against a persistence baseline. It returns forecast estimates, MAE/RMSE/R-squared, data-quality counts, and a safety note. If there is not enough continuous data, it returns `available: false` with a reason instead of a synthetic forecast. Forecasts are exploratory and must not be used as the sole basis for evacuation decisions.

The existing `/api/dashboard/prediction-accuracy/` endpoint reports stored prediction confidence and severity counts; it is not measured forecast accuracy.

## Activity Logs Endpoints (Admin Only)

#### List Activity Logs
```
GET /api/activity-logs/
```

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page
- `user_id`: Filter by user
- `action`: Filter by action
- `entity`: Filter by entity type

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error message",
  "details": "Additional error details"
}
```

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `204 No Content`: Resource deleted successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Rate Limiting

The API implements rate limiting to prevent abuse:
- 1000 requests per hour per IP address
- 100 requests per minute per user

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1626172800
```

## Pagination

List endpoints support pagination. Use the `page` and `page_size` query parameters.

**Response Format:**
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/water-level/?page=2",
  "previous": null,
  "results": [...]
}
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/swagger/`
- ReDoc: `http://localhost:8000/redoc/`
- OpenAPI JSON: `http://localhost:8000/swagger.json`
