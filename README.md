# Escape from College

A web application for managing a college escape room event with multiple teams and rounds.

## Setup Instructions

1. Install PostgreSQL if not already installed
2. Create a new database:
```sql
CREATE DATABASE escape_college;
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Configure PostgreSQL:
- Make sure PostgreSQL is running on port 5432
- Create a user with password if not exists:
```sql
CREATE USER postgres WITH PASSWORD 'postgres';
```
- Grant privileges:
```sql
GRANT ALL PRIVILEGES ON DATABASE escape_college TO postgres;
```

5. Run the application:
```bash
python app.py
```

## Default Credentials

### Admin Login
- Username: admin
- Password: admin123

## Features
- Team registration via Excel upload
- 4 rounds of challenges
- Real-time leaderboard
- Team management
- Progress tracking
- Admin controls