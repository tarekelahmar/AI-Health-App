# AI Health App

A FastAPI-based health application with Supabase database integration.

## Setup

### 1. Virtual Environment

Activate the virtual environment:
```bash
source venv/bin/activate
```

### 2. Environment Variables

Copy the example environment file and configure your Supabase connection:
```bash
cp env.example .env
```

Edit `.env` and add your Supabase database connection string:
```
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres
```

**To get your Supabase connection string:**
1. Go to your Supabase project dashboard
2. Navigate to **Settings** > **Database**
3. Find the **Connection string** section
4. Copy the URI connection string
5. Replace `[YOUR-PASSWORD]` with your database password

### 3. Database Connection

The database connection is configured in `app/database.py` using SQLAlchemy. The connection will automatically use the `DATABASE_URL` from your `.env` file.

## Project Structure

```
health-app/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app
│   ├── database.py           # Supabase/PostgreSQL setup
│   ├── models.py             # Data models
│   └── schemas.py            # API schemas
├── tests/
│   └── test_api.py
├── knowledge_base/
│   └── protocols.md
├── health_ontology.json
├── requirements.txt
└── README.md
```

## Running the Application

```bash
uvicorn app.main:app --reload
```

