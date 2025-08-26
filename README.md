# CallAudit Backend

A robust backend API for call auditing and quality management system built with FastAPI, featuring role-based authentication and comprehensive audit workflows.

## 🚀 Features

- **Role-Based Access Control**: Separate access levels for Managers and Auditors
- **Call Management**: Upload, store, and manage call recordings
- **Audit Workflows**: Comprehensive auditing system with scoring and feedback
- **User Management**: Multi-role user authentication and authorization


## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Authentication**: JWT-based authentication
- **API Documentation**: Swagger UI / ReDoc

## 📋 Prerequisites

Before running this project, ensure you have:

- Python 3.8+
- pip or uv
- PostgreSQL
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Shoyeb45/CallAudit-backend.git
cd CallAudit-backend
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt 
```

or 
```bash
uv run src/main.py
```


### 4. Environment Configuration

Create a `.env` file in the root directory:

```env

```

### 5. Database Setup

```bash
# Create database migrations
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 6. Run the Application

```bash
# Development server
uv run src/main.py
```
or 
```bash
python src/main.py
```


The API will be available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 👥 Default Users

The system comes with pre-configured test users:

### Managers
| Email | Password |
|-------|----------|
| sarah.johnson@company.com | manager123 |
| john.smith@company.com | manager123 |

### Auditors
| Email | Password |
|-------|----------|
| mike.wilson@company.com | auditor123 |
| lisa.chen@company.com | auditor123 |
| david.brown@company.com | auditor123 |
| emma.davis@company.com | auditor123 |

## 📚 API Documentation

### Authentication

All protected endpoints require JWT authentication. Include the token in the cookie


## 🏗️ Project Structure


