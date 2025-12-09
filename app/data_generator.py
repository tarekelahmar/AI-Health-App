import random
import pandas as pd
from datetime import datetime, timedelta
import json
from app.core.database import SessionLocal
from app.models import User, HealthDataPoint

def generate_simulated_health_data(days: int = 30) -> list:
    """
    Generate realistic simulated health data for testing.
    Simulates: sleep, glucose, HRV, activity over N days.
    Returns a list of dictionaries ready for database insertion.
    """
    data = []
    base_date = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        current_date = base_date + timedelta(days=day)
        
        # Sleep: normally 7±1.5 hours with some variation
        sleep_hours = max(4, min(10, random.gauss(7, 1.5)))
        data.append({
            'data_type': 'sleep_duration',
            'value': round(sleep_hours, 2),
            'unit': 'hours',
            'source': 'wearable',
            'timestamp': current_date
        })
        
        # Fasting glucose: normally 95±15 mg/dL
        glucose = max(60, min(200, random.gauss(95, 15)))
        data.append({
            'data_type': 'fasting_glucose',
            'value': round(glucose, 1),
            'unit': 'mg/dL',
            'source': 'lab',
            'timestamp': current_date
        })
        
        # HRV: normally 60±20 milliseconds
        hrv = max(20, min(150, random.gauss(60, 20)))
        data.append({
            'data_type': 'hrv_msec',
            'value': round(hrv, 1),
            'unit': 'milliseconds',
            'source': 'wearable',
            'timestamp': current_date
        })
        
        # Steps: normally 8000±3000
        steps = max(1000, random.gauss(8000, 3000))
        data.append({
            'data_type': 'daily_steps',
            'value': round(steps),
            'unit': 'steps',
            'source': 'wearable',
            'timestamp': current_date
        })
    
    return data

def get_or_create_test_user(db, name: str = "Test User", email: str = "test@example.com"):
    """Get existing user or create a new test user"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name=name, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created new user: {user.name} (ID: {user.id})")
    else:
        print(f"Using existing user: {user.name} (ID: {user.id})")
    return user

def insert_health_data_to_db(user_id: int, data_points: list, save_csv: bool = True):
    """Insert generated health data into the database"""
    db = SessionLocal()
    try:
        # Insert data points
        inserted_count = 0
        for data_point in data_points:
            db_data = HealthDataPoint(
                user_id=user_id,
                data_type=data_point['data_type'],
                value=data_point['value'],
                unit=data_point['unit'],
                source=data_point['source'],
                timestamp=data_point['timestamp']
            )
            db.add(db_data)
            inserted_count += 1
        
        db.commit()
        print(f"✅ Successfully inserted {inserted_count} data points into database")
        
        # Optionally save to CSV
        if save_csv:
            df = pd.DataFrame(data_points)
            # Convert datetime to string for CSV
            df['timestamp'] = df['timestamp'].apply(lambda x: x.isoformat())
            df.to_csv('sample_health_data.csv', index=False)
            print(f"📄 Also saved to sample_health_data.csv")
        
        return inserted_count
    except Exception as e:
        db.rollback()
        print(f"❌ Error inserting data: {e}")
        raise
    finally:
        db.close()

# Generate and insert sample data
if __name__ == "__main__":
    db = SessionLocal()
    try:
        # Get or create test user
        user = get_or_create_test_user(db)
        
        # Generate data
        print(f"Generating 30 days of sample health data...")
        data_points = generate_simulated_health_data(days=30)
        
        # Insert into database
        insert_health_data_to_db(user.id, data_points, save_csv=True)
        
        # Show summary
        total_points = db.query(HealthDataPoint).filter(
            HealthDataPoint.user_id == user.id
        ).count()
        print(f"\n📊 Total health data points for user {user.name}: {total_points}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()
