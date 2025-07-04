# DevSprint Setup Guide

## Environment Configuration

### Backend Setup

1. **Copy the environment template:**

   ```bash
   cd backend
   cp backend.env.example backend.env
   ```

2. **Generate a new Django secret key:**

   ```python
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. **Update `backend.env` with your values:**
   - Replace `your-secret-key-here` with the generated secret key
   - Update database credentials
   - Set `DEBUG=0` for production
   - Update `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` for your domain

### Frontend Setup

1. **Create environment file:**

   ```bash
   cd frontend
   cp .env.example .env.local
   ```

2. **Update API URL in `.env.local`:**

   ```text
   NEXT_PUBLIC_API_URL=https://your-domain.com/api
   ```

### Docker Setup

1. **Create `.env.compose` file in the root directory:**

   ```text
   # Database Configuration
   DB_NAME=devsprint
   DB_USER=devsprint
   DB_PASSWORD=your-secure-db-password
   
   # Django Settings
   SECRET_KEY=your-django-secret-key
   DEBUG=0
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   # Redis Configuration
   REDIS_URL=redis://redis:6379/0
   CELERY_BROKER_URL=redis://redis:6379/0
   
   # AI Model Settings
   MODEL_NAME=ollama3.1
   MODEL_API_ENDPOINT=http://localhost:11434/api/generate
   GPT=false
   ```

## Security Notes

- Never commit `.env` files to version control
- Use strong, unique passwords for database
- Keep your secret key secure and unique per environment
- Set `DEBUG=0` in production
- Use HTTPS in production

## Running the Application

1. **Backend:**

   ```bash
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```

2. **Frontend:**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Docker (all services):**

   ```bash
   docker-compose up -d
   ```
