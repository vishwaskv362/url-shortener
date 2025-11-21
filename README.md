# URL Shortener

A Flask-based URL shortener application with PostgreSQL database, running in Docker containers.

## Features

- 🔗 Shorten long URLs to compact, shareable links
- 🎯 Custom alias support for personalized short URLs
- 📊 Click tracking and analytics
- ⏰ Optional URL expiration dates
- 🎨 Modern, responsive web interface
- 🔌 RESTful API for programmatic access
- 🐳 Fully containerized with Docker Compose
- 🗄️ PostgreSQL database for production-grade persistence

## Tech Stack

- **Backend**: Flask (Python 3.11)
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy with Flask-Migrate
- **Server**: Gunicorn
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker
- Docker Compose

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd URL-shortener
```

2. Copy the example environment file:
```bash
cp .env.example .env
```

3. Edit `.env` file with your configuration (optional, defaults work for development)

4. Build and start the containers:
```bash
docker-compose up --build
```

5. Access the application:
- Web Interface: http://localhost:5000
- API: http://localhost:5000/api

### Database Migrations

Run migrations inside the container:
```bash
docker-compose exec web flask db upgrade
```

Create a new migration:
```bash
docker-compose exec web flask db migrate -m "Your migration message"
```

## API Documentation

### POST /api/shorten
Shorten a URL

**Request Body:**
```json
{
  "url": "https://example.com/very/long/url",
  "custom_code": "my-link",  // Optional
  "expires_at": "2024-12-31T23:59:59"  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "url": {
      "id": 1,
      "original_url": "https://example.com/very/long/url",
      "short_code": "my-link",
      "click_count": 0,
      "created_at": "2024-01-01T00:00:00"
    },
    "short_url": "http://localhost:5000/my-link",
    "message": "URL shortened successfully"
  }
}
```

### GET /api/urls/{short_code}
Get URL statistics

**Response:**
```json
{
  "success": true,
  "data": {
    "original_url": "https://example.com/very/long/url",
    "short_code": "my-link",
    "short_url": "http://localhost:5000/my-link",
    "click_count": 42,
    "created_at": "2024-01-01T00:00:00",
    "recent_clicks": [...]
  }
}
```

### DELETE /api/urls/{short_code}
Delete a shortened URL

**Response:**
```json
{
  "success": true,
  "message": "URL deleted successfully"
}
```

### GET /api/health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "service": "url-shortener",
  "version": "1.0.0"
}
```

## Project Structure

```
URL-shortener/
├── app/
│   ├── __init__.py           # App factory
│   ├── models.py             # Database models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py           # Web routes
│   │   └── api.py            # API routes
│   ├── services/
│   │   └── url_service.py    # Business logic
│   ├── utils/
│   │   └── short_code.py     # URL shortening utilities
│   ├── templates/            # HTML templates
│   │   ├── index.html
│   │   ├── stats.html
│   │   └── error.html
│   └── static/               # Static files
├── config.py                 # Configuration
├── run.py                    # Entry point
├── requirements.txt          # Python dependencies
├── Dockerfile               # Flask app container
├── docker-compose.yml       # Multi-container orchestration
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Development

### Running Locally Without Docker

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

4. Run the application:
```bash
python run.py
```

### Running Tests

```bash
docker-compose exec web python -m pytest
```

## Docker Commands

```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f web

# Rebuild containers
docker-compose up --build

# Remove all data (including database)
docker-compose down -v
```

## Configuration

Edit `.env` file to customize:

- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `FLASK_ENV`: Flask environment (development/production)
- `SECRET_KEY`: Flask secret key
- `BASE_URL`: Base URL for shortened links
- `SHORT_CODE_LENGTH`: Default length of short codes

## License

MIT License

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
