from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

class GeoPoint(BaseModel):
    lat: float
    lng: float

class TimeRange(BaseModel):
    start: str
    end: str

class Supercharger(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    location: GeoPoint
    stalls: int
    available: int
    power: int
    amenities: List[str]
    busyHours: List[TimeRange]
    address: str
    city: str
    state: str

class ChargingStop(BaseModel):
    superchargerId: str
    arrivalCharge: int
    departureCharge: int
    chargingTime: int
    name: str
    location: GeoPoint

class Trip(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    origin: GeoPoint
    destination: GeoPoint
    vehicleModel: str
    currentCharge: int
    stops: List[ChargingStop]
    totalDistance: float
    totalTime: float

class TripRequest(BaseModel):
    origin: GeoPoint
    destination: GeoPoint
    vehicleModel: str
    currentCharge: int

class VehicleProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str = "default_user"
    vehicleModel: str
    batteryCapacity: int
    currentCharge: int

def calculate_distance(point1: GeoPoint, point2: GeoPoint) -> float:
    """Calculate distance between two points using Haversine formula"""
    R = 6371
    lat1, lon1 = math.radians(point1.lat), math.radians(point1.lng)
    lat2, lon2 = math.radians(point2.lat), math.radians(point2.lng)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

@api_router.get("/")
async def root():
    return {"message": "Supercharger Network Explorer API"}

@api_router.get("/superchargers", response_model=List[Supercharger])
async def get_superchargers():
    superchargers = await db.superchargers.find({}, {"_id": 0}).to_list(1000)
    return superchargers

@api_router.get("/superchargers/{supercharger_id}", response_model=Supercharger)
async def get_supercharger(supercharger_id: str):
    supercharger = await db.superchargers.find_one({"id": supercharger_id}, {"_id": 0})
    if not supercharger:
        raise HTTPException(status_code=404, detail="Supercharger not found")
    return supercharger

@api_router.post("/trips/plan", response_model=Trip)
async def plan_trip(trip_request: TripRequest):
    superchargers = await db.superchargers.find({}, {"_id": 0}).to_list(1000)
    
    total_distance = calculate_distance(trip_request.origin, trip_request.destination)
    range_per_charge = 400
    battery_usage_per_km = 100 / range_per_charge
    
    stops = []
    current_charge = trip_request.currentCharge
    remaining_distance = total_distance
    
    if total_distance > (current_charge / battery_usage_per_km):
        num_stops = math.ceil((total_distance * battery_usage_per_km - current_charge) / 80)
        
        route_superchargers = sorted(
            superchargers,
            key=lambda s: calculate_distance(trip_request.origin, GeoPoint(**s['location']))
        )[:num_stops]
        
        for sc in route_superchargers:
            arrival_charge = max(current_charge - 20, 15)
            departure_charge = min(arrival_charge + 60, 95)
            charging_time = int((departure_charge - arrival_charge) * 0.75)
            
            stops.append(ChargingStop(
                superchargerId=sc['id'],
                arrivalCharge=arrival_charge,
                departureCharge=departure_charge,
                chargingTime=charging_time,
                name=sc['name'],
                location=GeoPoint(**sc['location'])
            ))
            current_charge = departure_charge
    
    trip = Trip(
        origin=trip_request.origin,
        destination=trip_request.destination,
        vehicleModel=trip_request.vehicleModel,
        currentCharge=trip_request.currentCharge,
        stops=stops,
        totalDistance=total_distance,
        totalTime=total_distance / 80 + sum(stop.chargingTime for stop in stops) / 60
    )
    
    trip_dict = trip.model_dump()
    await db.trips.insert_one(trip_dict)
    
    return trip

@api_router.post("/vehicle-profile", response_model=VehicleProfile)
async def save_vehicle_profile(profile: VehicleProfile):
    profile_dict = profile.model_dump()
    await db.vehicle_profiles.update_one(
        {"userId": profile.userId},
        {"$set": profile_dict},
        upsert=True
    )
    return profile

@api_router.get("/vehicle-profile", response_model=VehicleProfile)
async def get_vehicle_profile(userId: str = "default_user"):
    profile = await db.vehicle_profiles.find_one({"userId": userId}, {"_id": 0})
    if not profile:
        default_profile = VehicleProfile(
            vehicleModel="Model 3 Long Range",
            batteryCapacity=82,
            currentCharge=80
        )
        return default_profile
    return profile

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_db():
    count = await db.superchargers.count_documents({})
    if count == 0:
        superchargers_data = [
            {
                "id": str(uuid.uuid4()),
                "name": "San Francisco - Fremont Supercharger",
                "location": {"lat": 37.5483, "lng": -121.9886},
                "stalls": 24,
                "available": 18,
                "power": 250,
                "amenities": ["restrooms", "food", "wifi", "shopping"],
                "busyHours": [{"start": "08:00", "end": "10:00"}, {"start": "17:00", "end": "19:00"}],
                "address": "46900 Fremont Blvd",
                "city": "Fremont",
                "state": "CA"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Los Angeles - Santa Monica Supercharger",
                "location": {"lat": 34.0195, "lng": -118.4912},
                "stalls": 16,
                "available": 12,
                "power": 250,
                "amenities": ["restrooms", "wifi", "shopping"],
                "busyHours": [{"start": "12:00", "end": "14:00"}],
                "address": "1433 26th St",
                "city": "Santa Monica",
                "state": "CA"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "San Diego - Mission Valley Supercharger",
                "location": {"lat": 32.7682, "lng": -117.1649},
                "stalls": 20,
                "available": 15,
                "power": 250,
                "amenities": ["restrooms", "food", "shopping"],
                "busyHours": [{"start": "11:00", "end": "13:00"}],
                "address": "1640 Camino Del Rio N",
                "city": "San Diego",
                "state": "CA"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Las Vegas - Spring Valley Supercharger",
                "location": {"lat": 36.1070, "lng": -115.2218},
                "stalls": 32,
                "available": 24,
                "power": 250,
                "amenities": ["restrooms", "food", "wifi", "lounge"],
                "busyHours": [{"start": "09:00", "end": "11:00"}, {"start": "15:00", "end": "17:00"}],
                "address": "6730 S Las Vegas Blvd",
                "city": "Las Vegas",
                "state": "NV"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Phoenix - Scottsdale Supercharger",
                "location": {"lat": 33.4942, "lng": -111.9261},
                "stalls": 18,
                "available": 10,
                "power": 250,
                "amenities": ["restrooms", "food", "wifi"],
                "busyHours": [{"start": "14:00", "end": "16:00"}],
                "address": "15255 N Scottsdale Rd",
                "city": "Scottsdale",
                "state": "AZ"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Seattle - Bellevue Supercharger",
                "location": {"lat": 47.6101, "lng": -122.2015},
                "stalls": 20,
                "available": 16,
                "power": 250,
                "amenities": ["restrooms", "wifi", "food"],
                "busyHours": [{"start": "08:00", "end": "10:00"}],
                "address": "2055 152nd Ave NE",
                "city": "Bellevue",
                "state": "WA"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Portland - Downtown Supercharger",
                "location": {"lat": 45.5152, "lng": -122.6784},
                "stalls": 16,
                "available": 14,
                "power": 250,
                "amenities": ["restrooms", "wifi"],
                "busyHours": [{"start": "07:00", "end": "09:00"}],
                "address": "1455 SW Broadway",
                "city": "Portland",
                "state": "OR"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Denver - Cherry Creek Supercharger",
                "location": {"lat": 39.7294, "lng": -104.9531},
                "stalls": 22,
                "available": 8,
                "power": 250,
                "amenities": ["restrooms", "food", "wifi", "shopping"],
                "busyHours": [{"start": "12:00", "end": "14:00"}, {"start": "18:00", "end": "20:00"}],
                "address": "3000 E 1st Ave",
                "city": "Denver",
                "state": "CO"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Austin - Downtown Supercharger",
                "location": {"lat": 30.2672, "lng": -97.7431},
                "stalls": 20,
                "available": 17,
                "power": 250,
                "amenities": ["restrooms", "food", "wifi"],
                "busyHours": [{"start": "11:00", "end": "13:00"}],
                "address": "98 San Jacinto Blvd",
                "city": "Austin",
                "state": "TX"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Chicago - Lincoln Park Supercharger",
                "location": {"lat": 41.9216, "lng": -87.6499},
                "stalls": 18,
                "available": 12,
                "power": 250,
                "amenities": ["restrooms", "wifi", "food"],
                "busyHours": [{"start": "16:00", "end": "18:00"}],
                "address": "1551 N Clark St",
                "city": "Chicago",
                "state": "IL"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "New York - Manhattan Supercharger",
                "location": {"lat": 40.7580, "lng": -73.9855},
                "stalls": 14,
                "available": 6,
                "power": 250,
                "amenities": ["restrooms", "wifi"],
                "busyHours": [{"start": "08:00", "end": "10:00"}, {"start": "17:00", "end": "19:00"}],
                "address": "234 W 42nd St",
                "city": "New York",
                "state": "NY"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Miami - South Beach Supercharger",
                "location": {"lat": 25.7907, "lng": -80.1300},
                "stalls": 16,
                "available": 13,
                "power": 250,
                "amenities": ["restrooms", "food", "wifi"],
                "busyHours": [{"start": "10:00", "end": "12:00"}],
                "address": "1120 Washington Ave",
                "city": "Miami Beach",
                "state": "FL"
            }
        ]
        await db.superchargers.insert_many(superchargers_data)
        logger.info(f"Inserted {len(superchargers_data)} superchargers")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
