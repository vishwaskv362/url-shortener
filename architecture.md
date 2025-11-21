# URL Shortener - System Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Pattern](#architecture-pattern)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Service Layer Logic](#service-layer-logic)
6. [Utility Components](#utility-components)
7. [Configuration Management](#configuration-management)
8. [Data Flow Diagrams](#data-flow-diagrams)

---

## System Overview

The URL Shortener is a Flask-based web application that allows users to convert long URLs into short, manageable links. The system tracks analytics, supports custom aliases, and provides expiration functionality. Built with scalability and maintainability in mind, it follows modern software engineering practices.

### Technology Stack
- **Backend Framework**: Flask 2.x
- **Database**: PostgreSQL (Production) / SQLite (Testing)
- **ORM**: SQLAlchemy with Flask-SQLAlchemy
- **Database Migrations**: Flask-Migrate (Alembic)
- **URL Validation**: validators library
- **Containerization**: Docker & Docker Compose

---

## Architecture Pattern

### 1. **Layered Architecture**
The application follows a strict **three-tier layered architecture**:

```
┌─────────────────────────────────────┐
│     Presentation Layer (Routes)      │  ← HTTP Requests/Responses
├─────────────────────────────────────┤
│    Business Logic Layer (Services)   │  ← Domain Logic & Validation
├─────────────────────────────────────┤
│   Data Access Layer (Models + ORM)   │  ← Database Operations
└─────────────────────────────────────┘
```

#### **Presentation Layer** (`app/routes/`)
- **Responsibility**: Handle HTTP requests and responses
- **Components**: 
  - `main.py` - Web UI routes
  - `api.py` - RESTful API routes
- **Pattern**: Blueprint-based route registration
- **No Business Logic**: Routes delegate all business logic to the Service Layer

#### **Business Logic Layer** (`app/services/`)
- **Responsibility**: Core application logic, validation, and orchestration
- **Components**: 
  - `url_service.py` - URL shortening business logic
- **Pattern**: Static methods organized in service classes
- **Encapsulation**: All database operations go through this layer

#### **Data Access Layer** (`app/models.py`)
- **Responsibility**: Database schema definition and data persistence
- **Components**: SQLAlchemy models
- **Pattern**: Active Record pattern (models contain to_dict() methods)

### 2. **Design Patterns Used**

#### **Factory Pattern** (`app/__init__.py`)
```python
def create_app(config_name=None):
    """Application factory pattern."""
```
- Creates and configures Flask application instances
- Allows multiple instances with different configurations (development, testing, production)
- Enables easier testing and deployment

#### **Service Layer Pattern** (`app/services/url_service.py`)
- Encapsulates business logic
- Provides a clean API for routes
- Makes testing easier by isolating business logic
- All methods are static (stateless operations)

#### **Repository Pattern** (Implicit through SQLAlchemy ORM)
- Models act as repositories
- Abstracts database operations
- Query interface provided by SQLAlchemy

#### **Blueprint Pattern** (Flask Blueprints)
- Modular route organization
- Separation of API and web UI routes
- Enables route prefixing (`/api` for REST endpoints)

---

## Database Schema

### Entity-Relationship Diagram

```
┌─────────────────────────────┐
│          URLs               │
├─────────────────────────────┤
│ PK  id (Integer)            │
│     original_url (Text)     │
│ UQ  short_code (String)     │
│     custom (Boolean)        │
│     created_at (DateTime)   │
│     expires_at (DateTime?)  │
│     click_count (Integer)   │
└──────────────┬──────────────┘
               │
               │ 1:N
               │
               ▼
┌─────────────────────────────┐
│         Clicks              │
├─────────────────────────────┤
│ PK  id (Integer)            │
│ FK  url_id (Integer)        │
│     clicked_at (DateTime)   │
│     ip_address (String)     │
│     user_agent (Text)       │
│     referer (Text)          │
└─────────────────────────────┘
```

### Table: `urls`

**Purpose**: Stores the mapping between original URLs and their shortened codes.

| Column       | Type         | Constraints                 | Description                                    |
|--------------|--------------|----------------------------|------------------------------------------------|
| `id`         | Integer      | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for each URL entry           |
| `original_url` | Text       | NOT NULL                   | The full original URL to be shortened          |
| `short_code` | String(20)   | UNIQUE, NOT NULL, INDEXED  | The shortened code (e.g., "abc123")           |
| `custom`     | Boolean      | DEFAULT FALSE              | Flag indicating if short_code is custom        |
| `created_at` | DateTime     | NOT NULL, DEFAULT UTC NOW  | Timestamp when URL was created                 |
| `expires_at` | DateTime     | NULL                       | Optional expiration timestamp                  |
| `click_count`| Integer      | DEFAULT 0                  | Cached count of total clicks (performance)     |

**Indexes**:
- Primary index on `id`
- Unique index on `short_code` (for fast lookup during redirects)

**Business Rules**:
1. `short_code` must be unique across all entries
2. `original_url` can be duplicated (same URL can have multiple short codes)
3. If `expires_at` is NULL, the URL never expires
4. `click_count` is incremented on each redirect (denormalized for performance)
5. `custom` flag helps differentiate user-created aliases from auto-generated codes

### Table: `clicks`

**Purpose**: Tracks analytics for each click/redirect event.

| Column       | Type         | Constraints                 | Description                                    |
|--------------|--------------|----------------------------|------------------------------------------------|
| `id`         | Integer      | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for each click event         |
| `url_id`     | Integer      | FOREIGN KEY → urls.id, NOT NULL | Reference to the shortened URL               |
| `clicked_at` | DateTime     | NOT NULL, DEFAULT UTC NOW  | Exact timestamp of the click                   |
| `ip_address` | String(45)   | NULL                       | IP address of visitor (IPv6 compatible)        |
| `user_agent` | Text         | NULL                       | Browser/client user agent string               |
| `referer`    | Text         | NULL                       | HTTP referer header (where click came from)    |

**Foreign Keys**:
- `url_id` references `urls.id` with CASCADE DELETE (deleting URL removes all clicks)

**Business Rules**:
1. Each click creates a new record (append-only table)
2. Anonymous tracking (IP, user agent, referer only)
3. When a URL is deleted, all associated clicks are automatically deleted (CASCADE)

**Relationship**:
- One-to-Many: One URL can have many Clicks
- Defined in SQLAlchemy: `clicks = db.relationship('Click', backref='url', lazy='dynamic', cascade='all, delete-orphan')`

---

## API Endpoints

### 1. POST `/api/shorten`
**Purpose**: Create a new shortened URL

#### Request

**Method**: `POST`  
**Content-Type**: `application/json`

**Payload**:
```json
{
  "url": "https://example.com/very/long/url/path",
  "custom_code": "my-link",  // Optional
  "expires_at": "2024-12-31T23:59:59"  // Optional, ISO 8601 format
}
```

**Field Details**:
- `url` (required): The original long URL to shorten
  - Must be valid HTTP/HTTPS URL
  - Maximum length: 2048 characters
  - Validated using `validators.url()`
- `custom_code` (optional): User-defined short code
  - Length: 3-20 characters
  - Allowed characters: alphanumeric, hyphens, underscores
  - Must be unique
- `expires_at` (optional): Expiration datetime
  - ISO 8601 format
  - Can include timezone or use UTC
  - URL becomes inaccessible after this time

#### Response

**Success Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "url": {
      "id": 123,
      "original_url": "https://example.com/very/long/url/path",
      "short_code": "my-link",
      "short_url": "my-link",
      "custom": true,
      "created_at": "2024-11-21T10:30:00",
      "expires_at": "2024-12-31T23:59:59",
      "click_count": 0
    },
    "short_url": "http://localhost:5000/my-link",
    "message": "URL shortened successfully",
    "already_exists": false
  }
}
```

**Existing URL Response** (201 Created):
If the same URL was previously shortened (without custom code), returns existing short URL:
```json
{
  "success": true,
  "data": {
    "url": { /* existing URL object */ },
    "short_url": "http://localhost:5000/abc123",
    "message": "This URL was already shortened. Returning existing short URL.",
    "already_exists": true
  }
}
```

**Error Responses**:

**400 Bad Request** - Missing URL:
```json
{
  "success": false,
  "error": "URL is required"
}
```

**400 Bad Request** - Invalid URL format:
```json
{
  "success": false,
  "error": "Invalid URL format"
}
```

**400 Bad Request** - Invalid date format:
```json
{
  "success": false,
  "error": "Invalid date format. Use ISO 8601 format"
}
```

**400 Bad Request** - Custom code in use:
```json
{
  "success": false,
  "error": "Custom code already in use"
}
```

**400 Bad Request** - Invalid custom code:
```json
{
  "success": false,
  "error": "Invalid custom code format"
}
```

#### Logic Flow

1. **Request Parsing**:
   - Extract JSON payload
   - Parse `url`, `custom_code`, `expires_at` fields

2. **Date Parsing** (if `expires_at` provided):
   - Convert ISO 8601 string to Python datetime
   - Handle timezone conversion
   - Return 400 if format is invalid

3. **Delegate to Service Layer**:
   - Call `URLService.create_short_url()`
   - Pass validated parameters

4. **Service Layer Processing** (see Service Layer section for details):
   - Validate URL format and length
   - Check for existing URL (if not custom)
   - Validate or generate short code
   - Check uniqueness
   - Create database record
   - Commit transaction

5. **Response Construction**:
   - Convert model to dictionary
   - Add full short URL (base URL + code)
   - Return 201 with JSON response

#### Business Rules

- **Idempotency**: Same URL (without custom code) returns existing short URL
- **Custom Code Priority**: Custom codes bypass duplicate URL check
- **Expiration Validation**: Expired URLs are treated as non-existent
- **URL Length**: Maximum 2048 characters (configurable)
- **Transaction Safety**: Database rollback on any error

---

### 2. GET `/api/urls/<short_code>`
**Purpose**: Retrieve information and statistics about a shortened URL

#### Request

**Method**: `GET`  
**URL Parameter**: `short_code` - The shortened code to look up

**Example**: `GET /api/urls/my-link`

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": 123,
    "original_url": "https://example.com/very/long/url/path",
    "short_code": "my-link",
    "short_url": "http://localhost:5000/my-link",
    "custom": true,
    "created_at": "2024-11-21T10:30:00",
    "expires_at": "2024-12-31T23:59:59",
    "click_count": 42,
    "total_clicks": 42,
    "recent_clicks": [
      {
        "id": 567,
        "url_id": 123,
        "clicked_at": "2024-11-21T15:45:30",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
        "referer": "https://google.com/"
      },
      // ... up to 10 most recent clicks
    ]
  }
}
```

**Error Response** (404 Not Found):
```json
{
  "success": false,
  "error": "Short URL not found"
}
```

#### Logic Flow

1. **URL Parameter Extraction**:
   - Extract `short_code` from URL path

2. **Delegate to Service Layer**:
   - Call `URLService.get_url_stats(short_code)`

3. **Service Layer Processing**:
   - Query database for URL by short_code
   - Return 404 if not found
   - Convert URL model to dictionary
   - Query last 10 clicks (ordered by clicked_at DESC)
   - Convert clicks to dictionaries
   - Aggregate statistics

4. **Response Construction**:
   - Return 200 with comprehensive statistics
   - Include full short URL
   - Include click analytics

#### Data Captured

**URL Information**:
- All URL fields from database
- Full short URL (base URL + code)
- Expiration status

**Analytics**:
- Total click count (cached in URLs table)
- Last 10 clicks with:
  - Timestamp
  - IP address
  - User agent (browser/device info)
  - Referer (source of click)

#### Use Cases
- Dashboard statistics display
- Analytics reporting
- Verification of URL existence
- Monitoring URL performance

---

### 3. DELETE `/api/urls/<short_code>`
**Purpose**: Delete a shortened URL and all associated analytics

#### Request

**Method**: `DELETE`  
**URL Parameter**: `short_code` - The shortened code to delete

**Example**: `DELETE /api/urls/my-link`

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "URL deleted successfully"
}
```

**Error Response** (404 Not Found):
```json
{
  "success": false,
  "error": "Short URL not found"
}
```

#### Logic Flow

1. **URL Parameter Extraction**:
   - Extract `short_code` from URL path

2. **Delegate to Service Layer**:
   - Call `URLService.delete_url(short_code)`

3. **Service Layer Processing**:
   - Query database for URL by short_code
   - Return 404 if not found
   - Delete URL record from database
   - CASCADE DELETE automatically removes all clicks
   - Commit transaction

4. **Response Construction**:
   - Return 200 with success message

#### Database Operations

1. **Query**: Find URL by short_code
2. **Cascade Delete**: 
   - SQLAlchemy relationship defined with `cascade='all, delete-orphan'`
   - Automatically deletes all Click records with matching url_id
3. **Commit**: Persist changes to database
4. **Rollback**: On any error, revert all changes

#### Business Rules

- **Cascade Deletion**: Deleting a URL removes all analytics (clicks)
- **No Soft Delete**: Hard deletion (permanent)
- **Transaction Safety**: Rollback on errors
- **Idempotent**: Attempting to delete non-existent URL returns 404

#### Use Cases
- User-requested deletion
- Cleanup of expired URLs
- Removing inappropriate content
- Database maintenance

---

### 4. GET `/api/urls`
**Purpose**: List all shortened URLs with pagination

#### Request

**Method**: `GET`  
**Query Parameters**:
- `page` (optional, default: 1): Page number (1-indexed)
- `per_page` (optional, default: 50, max: 100): Items per page

**Example**: `GET /api/urls?page=2&per_page=20`

#### Response

**Success Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "urls": [
      {
        "id": 123,
        "original_url": "https://example.com/page1",
        "short_code": "abc123",
        "short_url": "http://localhost:5000/abc123",
        "custom": false,
        "created_at": "2024-11-21T10:30:00",
        "expires_at": null,
        "click_count": 42
      },
      // ... more URLs
    ],
    "total": 500,
    "pages": 25,
    "current_page": 2,
    "has_next": true,
    "has_prev": true
  }
}
```

**Error Response** (500 Internal Server Error):
```json
{
  "success": false,
  "error": "Error retrieving URLs: [error details]"
}
```

#### Logic Flow

1. **Query Parameter Parsing**:
   - Extract `page` (default: 1)
   - Extract `per_page` (default: 50)
   - Limit `per_page` to maximum 100 (prevent abuse)

2. **Delegate to Service Layer**:
   - Call `URLService.get_all_urls(page, per_page)`

3. **Service Layer Processing**:
   - Query URLs ordered by created_at DESC
   - Use SQLAlchemy paginate() method
   - Convert each URL to dictionary
   - Add full short URL to each entry
   - Calculate pagination metadata

4. **Response Construction**:
   - Return 200 with paginated results
   - Include navigation metadata

#### Pagination Logic

**SQLAlchemy Pagination**:
```python
pagination = URL.query.order_by(URL.created_at.desc()).paginate(
    page=page, 
    per_page=per_page, 
    error_out=False
)
```

**Pagination Object Attributes**:
- `items`: List of URL objects for current page
- `total`: Total number of URLs in database
- `pages`: Total number of pages
- `has_next`: Boolean, true if there's a next page
- `has_prev`: Boolean, true if there's a previous page

**Abuse Prevention**:
- Maximum `per_page` limit: 100
- Prevents memory exhaustion
- `per_page = min(per_page, 100)`

#### Response Fields

**URLs Array**: List of URL objects with full details
**Pagination Metadata**:
- `total`: Total URLs in database
- `pages`: Total number of pages
- `current_page`: Current page number
- `has_next`: Can paginate forward
- `has_prev`: Can paginate backward

#### Use Cases
- Dashboard listing
- API exploration
- Bulk export preparation
- Administrative overview

---

### 5. GET `/api/health`
**Purpose**: Health check endpoint for monitoring and load balancers

#### Request

**Method**: `GET`  
**No Parameters**

**Example**: `GET /api/health`

#### Response

**Success Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "url-shortener",
  "version": "1.0.0"
}
```

#### Logic Flow

1. **Direct Response**:
   - No database queries
   - No external dependencies
   - Always returns 200 OK if application is running

2. **Purpose**:
   - Quick response to confirm service is up
   - Used by load balancers (e.g., AWS ELB, Kubernetes)
   - Monitoring systems (e.g., Prometheus, Datadog)

#### Use Cases
- Load balancer health checks
- Container orchestration (Kubernetes liveness probe)
- Monitoring dashboards
- Uptime monitoring services
- CI/CD deployment verification

---

## Web UI Routes (Non-API)

### 1. GET `/`
**Purpose**: Home page with URL shortening form

**Template**: `index.html`  
**Logic**: Simple render, no database queries  
**User Action**: Submit URL via form (posts to API)

---

### 2. GET `/<short_code>`
**Purpose**: Redirect short code to original URL and track analytics

#### Logic Flow

1. **Short Code Extraction**:
   - Extract from URL path

2. **Service Layer Call**:
   - `URLService.get_original_url(short_code)`
   - Returns URL object or error

3. **Validation**:
   - Check if URL exists
   - Check if URL is expired
   - Return 404 error page if not found or expired

4. **Analytics Tracking**:
   - Call `URLService.track_click(url, request)`
   - Captures:
     - IP address: `request.remote_addr`
     - User agent: `request.headers.get('User-Agent')`
     - Referer: `request.headers.get('Referer')`
   - Increments `click_count`
   - Creates Click record
   - Non-blocking: redirect succeeds even if analytics fail

5. **HTTP Redirect**:
   - 302 Temporary Redirect
   - Location header set to original URL
   - Browser follows redirect automatically

#### Redirect Status Code

**302 Found** (Temporary Redirect):
- Used instead of 301 (Permanent Redirect)
- Allows analytics tracking on each request
- Browsers don't cache 302 redirects as aggressively
- Each click goes through server for tracking

#### Error Handling

**404 Page** (`error.html`):
- Short URL not found
- Short URL expired
- User-friendly error message

#### Analytics Captured

**Click Table Entry**:
- `url_id`: Foreign key to URLs table
- `clicked_at`: Current timestamp
- `ip_address`: Client IP (anonymized tracking)
- `user_agent`: Browser/device identification
- `referer`: Source of traffic

**URL Table Update**:
- `click_count` incremented atomically

#### Performance Considerations

- **Fast Lookup**: Indexed short_code field
- **Non-blocking Analytics**: Redirect even if tracking fails
- **Database Transaction**: Atomic update of click_count

---

### 3. GET `/dashboard`
**Purpose**: Display all shortened URLs with pagination

**Template**: `dashboard.html`  
**Data Source**: `URLService.get_all_urls()`  
**Pagination**: 20 items per page  
**Features**:
- List all URLs
- Show click counts
- Display expiration status
- Pagination controls

---

### 4. GET `/stats/<short_code>`
**Purpose**: Display detailed statistics for a specific URL

**Template**: `stats.html`  
**Data Source**: `URLService.get_url_stats(short_code)`  
**Analytics Displayed**:
- Original URL
- Short URL
- Creation date
- Expiration date
- Total clicks
- Recent click details (last 10)
- IP addresses
- Referer sources
- User agents

---

## Service Layer Logic

The Service Layer (`app/services/url_service.py`) encapsulates all business logic and acts as the bridge between routes and models.

### URLService Class

**Pattern**: Static methods (stateless service)  
**Responsibility**: Business logic, validation, orchestration

---

### Method: `validate_url(url)`

**Purpose**: Validate URL format and length

**Parameters**:
- `url` (str): URL to validate

**Returns**: `(bool, str)` - (is_valid, message)

**Logic**:

1. **Null/Empty Check**:
   ```python
   if not url:
       return False, "URL is required"
   ```

2. **Length Validation**:
   ```python
   max_length = current_app.config.get('MAX_URL_LENGTH', 2048)
   if len(url) > max_length:
       return False, "URL must be less than 2048 characters"
   ```

3. **Format Validation**:
   ```python
   if not validators.url(url):
       return False, "Invalid URL format"
   ```
   - Uses `validators` library
   - Checks HTTP/HTTPS protocol
   - Validates domain format
   - Checks for valid URL structure

**Validation Rules**:
- Must not be empty
- Maximum 2048 characters (configurable)
- Must be valid HTTP/HTTPS URL
- Must have valid domain name

---

### Method: `create_short_url(original_url, custom_code=None, expires_at=None)`

**Purpose**: Create a new shortened URL with comprehensive logic

**Parameters**:
- `original_url` (str): The long URL to shorten
- `custom_code` (str, optional): User-defined short code
- `expires_at` (datetime, optional): Expiration datetime

**Returns**: `(bool, dict/str)` - (success, result/error_message)

**Logic Flow**:

#### 1. URL Validation
```python
is_valid, message = URLService.validate_url(original_url)
if not is_valid:
    return False, message
```

#### 2. Duplicate URL Check (Non-Custom Only)
```python
if not custom_code:
    existing_url = URL.query.filter_by(original_url=original_url).first()
```

**Purpose**: Avoid creating duplicate short URLs for same long URL  
**Skip If**: User requested custom code  

**Expiration Check**:
```python
if existing_url:
    if not existing_url.expires_at or existing_url.expires_at > datetime.utcnow():
        return True, {
            'url': existing_url.to_dict(),
            'short_url': f"{BASE_URL}/{existing_url.short_code}",
            'message': 'URL already shortened. Returning existing.',
            'already_exists': True
        }
```

**Business Rule**: Only return existing URL if it's not expired

#### 3. Custom Code Processing

**If Custom Code Provided**:

**Step A: Validate Format**:
```python
if not ShortCodeGenerator.is_valid_custom_code(custom_code):
    return False, "Invalid custom code format"
```

Validation checks:
- Length: 3-20 characters
- Characters: alphanumeric, hyphens, underscores only
- Not empty

**Step B: Check Uniqueness**:
```python
if URL.query.filter_by(short_code=custom_code).first():
    return False, "Custom code already in use"
```

**Step C: Use Custom Code**:
```python
short_code = custom_code
is_custom = True
```

#### 4. Auto-Generated Code

**If No Custom Code**:
```python
short_code_length = current_app.config.get('SHORT_CODE_LENGTH', 6)
short_code = ShortCodeGenerator.generate_random(short_code_length)
```

**Generation Logic** (see Utility Components):
- Random selection from Base62 charset
- Uniqueness check against database
- Retry with longer length if collisions occur
- Maximum 10 attempts per length

#### 5. Database Record Creation

```python
new_url = URL(
    original_url=original_url,
    short_code=short_code,
    custom=is_custom,
    expires_at=expires_at
)
```

**Default Values** (from model):
- `created_at`: Current UTC timestamp
- `click_count`: 0
- `id`: Auto-increment

#### 6. Transaction Commit

```python
try:
    db.session.add(new_url)
    db.session.commit()
    return True, {
        'url': new_url.to_dict(),
        'short_url': f"{BASE_URL}/{new_url.short_code}",
        'message': 'URL shortened successfully',
        'already_exists': False
    }
except Exception as e:
    db.session.rollback()
    return False, f"Database error: {str(e)}"
```

**Transaction Safety**:
- Rollback on any error
- Prevents partial data
- Returns error message to user

---

### Method: `get_original_url(short_code)`

**Purpose**: Retrieve and validate URL for redirection

**Parameters**:
- `short_code` (str): The short code to look up

**Returns**: `(bool, URL/str)` - (success, url_object/error_message)

**Logic Flow**:

#### 1. Database Query
```python
url = URL.query.filter_by(short_code=short_code).first()
```

**Index Usage**: Query uses indexed short_code field for fast lookup

#### 2. Existence Check
```python
if not url:
    return False, "Short URL not found"
```

#### 3. Expiration Validation
```python
if url.expires_at and url.expires_at < datetime.utcnow():
    return False, "Short URL has expired"
```

**Expiration Logic**:
- If `expires_at` is NULL: Never expires
- If `expires_at` is future: Valid
- If `expires_at` is past: Expired (return error)

#### 4. Return Valid URL
```python
return True, url
```

Returns full URL object for further processing (analytics, redirect)

---

### Method: `track_click(url, request)`

**Purpose**: Record analytics data for a redirect event

**Parameters**:
- `url` (URL object): The URL being accessed
- `request` (Flask request): HTTP request object

**Returns**: None (side effects only)

**Logic Flow**:

#### 1. Increment Click Counter
```python
url.click_count += 1
```

**Purpose**: Denormalized counter for performance  
**Atomic Operation**: Updated in same transaction as click record

#### 2. Extract Request Metadata
```python
ip_address = request.remote_addr
user_agent = request.headers.get('User-Agent', '')
referer = request.headers.get('Referer', '')
```

**Data Captured**:
- **IP Address**: Client's IP (may be proxy IP)
- **User Agent**: Browser/device identification string
- **Referer**: HTTP Referer header (source URL)

#### 3. Create Click Record
```python
click = Click(
    url_id=url.id,
    ip_address=ip_address,
    user_agent=user_agent,
    referer=referer
)
```

**Timestamp**: `clicked_at` auto-populated by database default

#### 4. Persist to Database
```python
try:
    db.session.add(click)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    print(f"Failed to track click: {str(e)}")
```

**Error Handling**:
- **Non-Blocking**: Errors logged but don't prevent redirect
- **User Experience**: Redirect succeeds even if analytics fail
- **Rollback**: Prevents partial data on error

**Business Rule**: Analytics failure should never break core functionality (redirects)

---

### Method: `get_url_stats(short_code)`

**Purpose**: Retrieve comprehensive statistics for analytics display

**Parameters**:
- `short_code` (str): The short code to get stats for

**Returns**: `(bool, dict/str)` - (success, stats_dict/error_message)

**Logic Flow**:

#### 1. Retrieve URL
```python
url = URL.query.filter_by(short_code=short_code).first()
if not url:
    return False, "Short URL not found"
```

#### 2. Convert URL to Dictionary
```python
stats = url.to_dict()
```

**Base Fields**:
- id, original_url, short_code
- custom, created_at, expires_at
- click_count

#### 3. Add Full Short URL
```python
stats['short_url'] = f"{current_app.config['BASE_URL']}/{url.short_code}"
```

#### 4. Add Click Count
```python
stats['total_clicks'] = url.click_count
```

#### 5. Retrieve Recent Clicks
```python
stats['recent_clicks'] = [
    click.to_dict() for click in 
    url.clicks.order_by(Click.clicked_at.desc()).limit(10)
]
```

**Click Query**:
- **Relationship**: Uses SQLAlchemy relationship (`url.clicks`)
- **Lazy Loading**: `lazy='dynamic'` allows query chaining
- **Ordering**: Most recent first (`desc()`)
- **Limit**: Last 10 clicks only (performance)

**Click Data**:
- Click timestamp
- IP address
- User agent
- Referer

#### 6. Return Complete Statistics
```python
return True, stats
```

**Use Case**: Dashboard, analytics pages, API responses

---

### Method: `get_all_urls(page=1, per_page=50)`

**Purpose**: Retrieve paginated list of all URLs

**Parameters**:
- `page` (int): Page number (1-indexed)
- `per_page` (int): Items per page

**Returns**: `(bool, dict/str)` - (success, pagination_data/error_message)

**Logic Flow**:

#### 1. Query with Pagination
```python
pagination = URL.query.order_by(URL.created_at.desc()).paginate(
    page=page, 
    per_page=per_page, 
    error_out=False
)
```

**Query Details**:
- **Ordering**: Most recent first (`created_at DESC`)
- **Pagination**: SQLAlchemy's built-in paginate()
- **Error Handling**: `error_out=False` prevents exceptions on invalid page

#### 2. Process Each URL
```python
urls = []
for url in pagination.items:
    url_dict = url.to_dict()
    url_dict['short_url'] = f"{BASE_URL}/{url.short_code}"
    urls.append(url_dict)
```

#### 3. Build Response
```python
return True, {
    'urls': urls,
    'total': pagination.total,
    'pages': pagination.pages,
    'current_page': page,
    'has_next': pagination.has_next,
    'has_prev': pagination.has_prev
}
```

**Pagination Metadata**:
- `total`: Total URLs in database
- `pages`: Total pages available
- `current_page`: Current page number
- `has_next`: Boolean, more pages available
- `has_prev`: Boolean, previous pages exist

#### 4. Error Handling
```python
except Exception as e:
    return False, f"Error retrieving URLs: {str(e)}"
```

---

### Method: `delete_url(short_code)`

**Purpose**: Permanently delete URL and all analytics

**Parameters**:
- `short_code` (str): The short code to delete

**Returns**: `(bool, str)` - (success, message)

**Logic Flow**:

#### 1. Find URL
```python
url = URL.query.filter_by(short_code=short_code).first()
if not url:
    return False, "Short URL not found"
```

#### 2. Delete URL
```python
try:
    db.session.delete(url)
    db.session.commit()
    return True, "URL deleted successfully"
```

**Cascade Effect**:
- SQLAlchemy relationship: `cascade='all, delete-orphan'`
- Automatically deletes all Click records
- Single DELETE operation cascades to related tables

#### 3. Error Handling
```python
except Exception as e:
    db.session.rollback()
    return False, f"Database error: {str(e)}"
```

**Transaction Safety**: Rollback ensures no partial deletions

---

## Utility Components

### ShortCodeGenerator Class (`app/utils/short_code.py`)

**Purpose**: Generate and validate short codes using Base62 encoding

**Character Set**: Base62 (62 characters)
```python
CHARSET = string.ascii_letters + string.digits
# abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
```

**Why Base62?**:
- URL-safe (no special characters)
- Case-sensitive (more combinations)
- Human-readable
- Compact representation

---

#### Method: `encode_base62(num)`

**Purpose**: Convert integer to Base62 string

**Algorithm**:
```python
def encode_base62(num):
    if num == 0:
        return CHARSET[0]
    
    base62 = []
    base = 62
    
    while num:
        num, rem = divmod(num, base)
        base62.append(CHARSET[rem])
    
    return ''.join(reversed(base62))
```

**Example**:
- Input: 12345
- Output: "3D7"
- Calculation: 12345 = 3×62² + 13×62¹ + 7×62⁰

**Use Case**: Convert database IDs to short codes (alternative to random)

---

#### Method: `decode_base62(code)`

**Purpose**: Convert Base62 string back to integer

**Algorithm**:
```python
def decode_base62(code):
    base = 62
    num = 0
    
    for char in code:
        num = num * base + CHARSET.index(char)
    
    return num
```

**Example**:
- Input: "3D7"
- Output: 12345

**Use Case**: Reverse lookup, validation, analytics

---

#### Method: `generate_from_id(id_num, min_length=6)`

**Purpose**: Generate short code from database ID

**Logic**:
```python
def generate_from_id(id_num, min_length=6):
    code = encode_base62(id_num)
    
    if len(code) < min_length:
        code = code.zfill(min_length)
    
    return code
```

**Padding**: Ensures consistent length (left-padded with 'a')

**Use Case**: Deterministic code generation (alternative strategy)

**Not Currently Used**: Application uses random generation

---

#### Method: `generate_random(length=6, max_attempts=10)`

**Purpose**: Generate random short code with uniqueness guarantee

**Algorithm**:
```python
def generate_random(length=6, max_attempts=10):
    for _ in range(max_attempts):
        code = ''.join(random.choices(CHARSET, k=length))
        
        # Check uniqueness
        if not URL.query.filter_by(short_code=code).first():
            return code
    
    # Increase length if collisions persist
    return generate_random(length + 1, max_attempts)
```

**Collision Handling**:
1. Try 10 times to generate unique code at given length
2. If all attempts collide, increase length by 1
3. Recursively retry with longer length
4. Guarantees uniqueness eventually

**Collision Probability**:
- Length 6: 62^6 = 56.8 billion combinations
- Low collision probability in normal use
- Scales automatically if needed

**Database Query**: Each candidate checked against database for uniqueness

---

#### Method: `is_valid_custom_code(code)`

**Purpose**: Validate user-provided custom short codes

**Validation Rules**:

1. **Not Empty**:
   ```python
   if not code:
       return False
   ```

2. **Character Validation**:
   ```python
   allowed_chars = string.ascii_letters + string.digits + '-_'
   if not all(c in allowed_chars for c in code):
       return False
   ```
   
   **Allowed**:
   - Letters: a-z, A-Z
   - Numbers: 0-9
   - Hyphens: -
   - Underscores: _
   
   **Forbidden**:
   - Special characters: @, #, $, %, etc.
   - Spaces
   - Unicode characters

3. **Length Constraints**:
   ```python
   min_len = current_app.config.get('CUSTOM_ALIAS_MIN_LENGTH', 3)
   max_len = current_app.config.get('CUSTOM_ALIAS_MAX_LENGTH', 20)
   
   if not (min_len <= len(code) <= max_len):
       return False
   ```
   
   **Default Limits**:
   - Minimum: 3 characters
   - Maximum: 20 characters

**Why These Rules?**:
- **URL-safe**: No percent-encoding needed
- **Readable**: Easy to type and share
- **Practical**: Prevents abuse (too short/long)
- **Database-safe**: Compatible with VARCHAR(20)

---

## Configuration Management

### Configuration Pattern

**File**: `config.py`  
**Pattern**: Class-based configuration with environment inheritance

**Hierarchy**:
```
Config (Base)
  ├── DevelopmentConfig
  ├── ProductionConfig
  └── TestingConfig
```

---

### Base Config Class

```python
class Config:
    """Base configuration class."""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/urlshortener'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    
    # Application Configuration
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
    SHORT_CODE_LENGTH = int(os.getenv('SHORT_CODE_LENGTH', 6))
    
    # URL Configuration
    MAX_URL_LENGTH = 2048
    CUSTOM_ALIAS_MIN_LENGTH = 3
    CUSTOM_ALIAS_MAX_LENGTH = 20
```

#### Configuration Fields

**Flask Settings**:
- `SECRET_KEY`: Session encryption key (must change in production)
- `DEBUG`: Debug mode toggle

**Database Settings**:
- `SQLALCHEMY_DATABASE_URI`: Database connection string
  - Format: `postgresql://user:password@host:port/database`
  - Supports PostgreSQL, MySQL, SQLite
- `SQLALCHEMY_TRACK_MODIFICATIONS`: Disabled (performance)
- `SQLALCHEMY_ECHO`: Logs SQL queries when DEBUG=True

**Application Settings**:
- `BASE_URL`: Base URL for short links (e.g., "https://short.link")
- `SHORT_CODE_LENGTH`: Default length for generated codes

**URL Constraints**:
- `MAX_URL_LENGTH`: Maximum original URL length (2048 chars)
- `CUSTOM_ALIAS_MIN_LENGTH`: Minimum custom code length (3)
- `CUSTOM_ALIAS_MAX_LENGTH`: Maximum custom code length (20)

---

### Environment-Specific Configs

#### DevelopmentConfig
```python
class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
```

**Use**: Local development  
**Features**: Debug mode, verbose logging

---

#### ProductionConfig
```python
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
```

**Use**: Production deployment  
**Features**: No debug, no SQL echo, secure secret key

---

#### TestingConfig
```python
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

**Use**: Unit tests  
**Features**: In-memory SQLite, isolated tests

---

### Configuration Loading

**Application Factory** (`app/__init__.py`):
```python
def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
```

**Environment Variable**: `FLASK_ENV`
- Values: "development", "production", "testing"
- Default: "development"

**Environment File**: `.env`
```bash
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:pass@db:5432/urlshortener
BASE_URL=https://yourdomain.com
```

---

## Data Flow Diagrams

### 1. URL Shortening Flow

```
User Request
    │
    ├─ POST /api/shorten
    │   └─ JSON: {"url": "https://...", "custom_code": "..."}
    │
    ▼
API Route (api.py)
    │
    ├─ Parse JSON
    ├─ Validate date format
    │
    ▼
Service Layer (url_service.py)
    │
    ├─ validate_url() ──────────────┐
    │   ├─ Check format             │
    │   └─ Check length              │ Validation
    │                                 │
    ├─ Check duplicate (if not custom)
    │   └─ Query: WHERE original_url = ? ──┐
    │                                        │
    ├─ Custom code?                          │ Database
    │   ├─ Yes: Validate format              │ Operations
    │   │   └─ Query: WHERE short_code = ?   │
    │   └─ No: generate_random() ────────────┤
    │       └─ Check uniqueness (loop)       │
    │                                         │
    ├─ Create URL object                     │
    ├─ INSERT INTO urls                      │
    └─ COMMIT ───────────────────────────────┘
        │
        ▼
Response
    └─ 201 Created
        └─ JSON: {"success": true, "data": {...}}
```

---

### 2. URL Redirect Flow

```
User Request
    │
    ├─ GET /abc123
    │
    ▼
Web Route (main.py)
    │
    ▼
Service Layer (url_service.py)
    │
    ├─ get_original_url(short_code)
    │   ├─ Query: WHERE short_code = 'abc123' ──┐
    │   ├─ Check exists                          │ Database
    │   └─ Check not expired                     │ Read
    │                                             │
    ├─ Found? ───────────────────────────────────┘
    │   ├─ No → Return (False, "Not found")
    │   │      └─ 404 Error Page
    │   │
    │   └─ Yes ↓
    │
    ├─ track_click(url, request)
    │   ├─ url.click_count += 1
    │   ├─ Extract: IP, User-Agent, Referer
    │   ├─ INSERT INTO clicks ───────────────────┐
    │   └─ COMMIT                                 │ Database
    │                                              │ Write
    ▼                                              │
HTTP Redirect ─────────────────────────────────────┘
    └─ 302 Found
        └─ Location: https://original-long-url.com
```

---

### 3. Analytics Retrieval Flow

```
User Request
    │
    ├─ GET /api/urls/abc123
    │
    ▼
API Route (api.py)
    │
    ▼
Service Layer (url_service.py)
    │
    ├─ get_url_stats(short_code)
    │   │
    │   ├─ Query: SELECT * FROM urls WHERE short_code = ? ──┐
    │   │                                                     │
    │   ├─ Found? Yes ↓                                      │
    │   │                                                     │
    │   ├─ Convert to dict: url.to_dict()                    │ Database
    │   │                                                     │ Operations
    │   ├─ Query: SELECT * FROM clicks                       │
    │   │         WHERE url_id = ?                           │
    │   │         ORDER BY clicked_at DESC                   │
    │   │         LIMIT 10 ────────────────────────────────┘
    │   │
    │   └─ Aggregate statistics
    │       ├─ Total clicks
    │       ├─ Recent clicks (last 10)
    │       └─ Full URL details
    │
    ▼
Response
    └─ 200 OK
        └─ JSON: {
               "success": true,
               "data": {
                   "url": {...},
                   "total_clicks": 42,
                   "recent_clicks": [...]
               }
           }
```

---

### 4. Database Transaction Flow

```
Service Method Call
    │
    ▼
┌────────────────────────────────┐
│  BEGIN TRANSACTION (Implicit)  │
├────────────────────────────────┤
│                                │
│  ┌──────────────────────────┐ │
│  │  Business Logic          │ │
│  │  ├─ Validations          │ │
│  │  ├─ Model Creation       │ │
│  │  └─ db.session.add()     │ │
│  └──────────────────────────┘ │
│            │                   │
│            ▼                   │
│      Success?                  │
│       ┌──┴──┐                 │
│       │     │                 │
│      Yes   No                 │
│       │     │                 │
│       ▼     ▼                 │
│  db.session. db.session.      │
│    commit()  rollback()       │
│       │         │              │
└───────┼─────────┼──────────────┘
        │         │
        ▼         ▼
    Success    Failure
    Response   Error Response
```

**Transaction Guarantees**:
- **Atomicity**: All or nothing (commit or rollback)
- **Consistency**: Data integrity maintained
- **Isolation**: Concurrent requests don't interfere
- **Durability**: Committed changes persist

---

## Design Decisions & Rationale

### 1. Why Flask?
- **Lightweight**: Minimal overhead
- **Flexible**: Unopinionated design
- **Mature Ecosystem**: Extensions for everything
- **Easy to Learn**: Simple, Pythonic API

### 2. Why PostgreSQL?
- **ACID Compliance**: Transaction safety
- **Performance**: Excellent for read-heavy workloads
- **Reliability**: Production-proven
- **Indexing**: Fast lookups on short_code
- **Scalability**: Handles millions of URLs

### 3. Why SQLAlchemy?
- **ORM Benefits**: Object-relational mapping
- **Database Agnostic**: Switch databases easily
- **Query Builder**: Pythonic query syntax
- **Relationship Management**: Automatic JOIN queries
- **Migration Support**: Via Flask-Migrate (Alembic)

### 4. Why Base62 Encoding?
- **URL-Safe**: No special characters
- **Compact**: 62^6 = 56.8 billion combinations
- **Human-Readable**: Easy to type and share
- **Collision-Resistant**: Low probability

### 5. Why Service Layer?
- **Separation of Concerns**: Routes don't contain business logic
- **Testability**: Easy to unit test business logic
- **Reusability**: Same logic for API and web UI
- **Maintainability**: Changes centralized in one place

### 6. Why 302 Instead of 301 Redirects?
- **Analytics**: Must track every click
- **Flexibility**: Can change target URL
- **No Caching**: Browser doesn't cache redirect
- **Standard Practice**: Used by all URL shorteners

### 7. Why Cascade Delete?
- **Data Integrity**: No orphaned clicks
- **Simplicity**: Single DELETE operation
- **Consistency**: All related data removed
- **GDPR Compliance**: Complete data removal

### 8. Why Click Denormalization?
- **Performance**: Faster stats retrieval
- **UX**: Instant click counts on listings
- **Trade-off**: Slight data duplication acceptable
- **Atomic Updates**: Updated in same transaction

---

## Performance Considerations

### 1. Database Indexes
- **short_code**: UNIQUE INDEX for fast lookups (O(log n))
- **created_at**: Index for ordering (optional, for large datasets)

### 2. Query Optimization
- **Pagination**: Prevents loading entire table
- **Lazy Loading**: Clicks loaded only when needed (`lazy='dynamic'`)
- **Limit Queries**: Only fetch what's displayed (last 10 clicks)

### 3. Denormalization
- **click_count**: Cached in URLs table (avoid COUNT(*) queries)

### 4. Transaction Management
- **Atomic Operations**: Single commits reduce database locks
- **Rollback on Errors**: Prevents partial data

### 5. Non-Blocking Analytics
- **Redirect First**: Analytics failure doesn't break redirects
- **Best Effort**: Click tracking errors logged, not raised

### 6. Scalability Strategies (Future)
- **Caching**: Redis for frequently accessed URLs
- **Read Replicas**: Separate read/write database instances
- **CDN**: Static assets served from edge locations
- **Load Balancing**: Multiple application servers

---

## Security Considerations

### 1. Input Validation
- **URL Validation**: Prevents injection attacks
- **Length Limits**: Prevents buffer overflow
- **Character Whitelist**: Custom codes only allow safe characters

### 2. SQL Injection Prevention
- **ORM**: SQLAlchemy parameterizes all queries
- **No Raw SQL**: All queries use ORM methods

### 3. Rate Limiting (Recommended Future Enhancement)
- **Per IP**: Prevent abuse
- **Per Endpoint**: Protect resource-intensive operations

### 4. HTTPS (Production)
- **Encrypted Traffic**: Prevent eavesdropping
- **Certificate Validation**: Trust verification

### 5. Secret Key Management
- **Environment Variables**: Not hardcoded
- **Production**: Strong, random secret key
- **Rotation**: Periodic key updates

### 6. CORS (If API Used Cross-Domain)
- **Origin Whitelist**: Control access
- **Credentials**: Secure cookie/session handling

---

## Error Handling Strategy

### 1. Service Layer Returns Tuples
```python
(success: bool, result: dict/str)
```
- **Consistent**: All methods use same pattern
- **Explicit**: Success/failure clearly indicated
- **Informative**: Error messages returned

### 2. Database Transaction Safety
- **Try-Except Blocks**: Catch all database errors
- **Rollback**: Prevent partial data
- **User-Friendly Messages**: Hide internal errors

### 3. HTTP Status Codes
- **200 OK**: Successful retrieval
- **201 Created**: Successful creation
- **400 Bad Request**: Validation errors
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Unexpected errors

### 4. Logging (Production Enhancement)
- **Error Logging**: Log all exceptions
- **Audit Trail**: Log important events
- **Monitoring**: Integration with monitoring tools

---

## Testing Recommendations

### 1. Unit Tests
- Test each service method independently
- Mock database calls
- Test validation logic

### 2. Integration Tests
- Test API endpoints
- Test database operations
- Test complete workflows

### 3. Test Cases to Cover
- Valid URL shortening
- Duplicate URL handling
- Custom code validation
- Expiration logic
- Analytics tracking
- Pagination
- Error conditions

---

## Future Enhancements

### 1. Caching Layer
- **Redis**: Cache frequently accessed URLs
- **TTL**: Time-to-live based on access patterns

### 2. Advanced Analytics
- **Geographic Data**: Country/city from IP
- **Device Detection**: Mobile vs desktop
- **Referrer Analysis**: Top traffic sources
- **Time Series**: Clicks over time graphs

### 3. User Authentication
- **User Accounts**: Manage personal URLs
- **API Keys**: Programmatic access
- **Permissions**: Public vs private URLs

### 4. Rate Limiting
- **Flask-Limiter**: Prevent abuse
- **Per-IP Limits**: Protect resources

### 5. QR Code Generation
- **QR Codes**: Visual representation of short URLs
- **Download**: PNG/SVG export

### 6. Browser Extension
- **One-Click Shortening**: From any webpage
- **Context Menu**: Right-click to shorten

### 7. Batch Operations
- **Bulk Shortening**: Multiple URLs at once
- **CSV Export**: Analytics export

### 8. A/B Testing
- **Multiple Targets**: Rotate destinations
- **Traffic Split**: Percentage-based routing

---

## Conclusion

This URL Shortener application demonstrates clean architecture principles, separation of concerns, and production-ready patterns. The layered design ensures maintainability, testability, and scalability. Each component has a clear responsibility, and the service layer provides a robust abstraction between routes and data access.

The system is designed to handle high traffic with efficient database queries, proper indexing, and transaction management. Analytics are captured without impacting core functionality, and the API provides comprehensive endpoints for programmatic access.

With the foundation in place, the system can be easily extended with additional features like caching, advanced analytics, user authentication, and more sophisticated URL management capabilities.

---
