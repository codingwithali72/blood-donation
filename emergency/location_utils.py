"""
Location utilities for Emergency Blood Bank System
Provides IP geolocation, geocoding, and distance calculation services
"""

import requests
import logging
from math import radians, cos, sin, asin, sqrt
from django.conf import settings
from django.core.cache import cache
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


class LocationService:
    """Enhanced location service with multiple providers and fallbacks"""
    
    def __init__(self):
        self.ipinfo_token = getattr(settings, 'IPINFO_TOKEN', '')
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        
    def get_location_from_ip(self, ip_address: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Get approximate location from IP address
        Returns: (latitude, longitude, city) or (None, None, None)
        """
        if not ip_address or ip_address in ['127.0.0.1', 'localhost']:
            return None, None, None
            
        # Check cache first
        cache_key = f"ip_location_{ip_address}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
            
        try:
            # Try IPInfo.io first (more accurate)
            if self.ipinfo_token:
                response = requests.get(
                    f"https://ipinfo.io/{ip_address}",
                    headers={"Authorization": f"Bearer {self.ipinfo_token}"},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'loc' in data:
                        lat_str, lng_str = data['loc'].split(',')
                        lat, lng = float(lat_str), float(lng_str)
                        city = data.get('city', 'Unknown')
                        result = (lat, lng, city)
                        # Cache for 1 hour
                        cache.set(cache_key, result, 3600)
                        return result
            
            # Fallback to ip-api.com (free, no key required)
            response = requests.get(
                f"http://ip-api.com/json/{ip_address}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    lat = float(data.get('lat', 0))
                    lng = float(data.get('lon', 0))
                    city = data.get('city', 'Unknown')
                    result = (lat, lng, city)
                    # Cache for 1 hour
                    cache.set(cache_key, result, 3600)
                    return result
                    
        except Exception as e:
            logger.warning(f"IP geolocation failed for {ip_address}: {e}")
            
        return None, None, None
    
    def geocode_address(self, address: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Convert address to coordinates using Google Maps Geocoding API
        Returns: (latitude, longitude) or (None, None)
        """
        if not address or not self.google_api_key:
            return None, None
            
        # Check cache first
        cache_key = f"geocode_{hash(address.lower())}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
            
        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={
                    'address': address,
                    'key': self.google_api_key
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    location = data['results'][0]['geometry']['location']
                    lat, lng = location['lat'], location['lng']
                    result = (lat, lng)
                    # Cache for 24 hours
                    cache.set(cache_key, result, 86400)
                    return result
                    
        except Exception as e:
            logger.error(f"Geocoding failed for '{address}': {e}")
            
        return None, None
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """
        Convert coordinates to address using Google Maps Reverse Geocoding API
        Returns: address string or None
        """
        if not self.google_api_key:
            return f"Coordinates: {lat:.6f}, {lng:.6f}"
            
        # Check cache first
        cache_key = f"reverse_geocode_{lat:.6f}_{lng:.6f}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
            
        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={
                    'latlng': f"{lat},{lng}",
                    'key': self.google_api_key
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and data.get('results'):
                    address = data['results'][0]['formatted_address']
                    # Cache for 24 hours
                    cache.set(cache_key, address, 86400)
                    return address
                    
        except Exception as e:
            logger.error(f"Reverse geocoding failed for {lat}, {lng}: {e}")
            
        return f"Coordinates: {lat:.6f}, {lng:.6f}"
    
    def get_location_details(self, request, user_lat=None, user_lng=None, location_text=None) -> Dict[str, Any]:
        """
        Get comprehensive location information from multiple sources
        Returns dictionary with location details
        """
        location_info = {
            'latitude': user_lat,
            'longitude': user_lng,
            'address': location_text or '',
            'city': '',
            'source': 'unknown',
            'accuracy': 'unknown'
        }
        
        # If GPS coordinates are provided, use them (most accurate)
        if user_lat and user_lng:
            location_info['source'] = 'gps'
            location_info['accuracy'] = 'high'
            
            # Try to get address from coordinates
            if not location_text:
                address = self.reverse_geocode(float(user_lat), float(user_lng))
                if address:
                    location_info['address'] = address
                    
        # If manual location text is provided, try to geocode it
        elif location_text:
            lat, lng = self.geocode_address(location_text)
            if lat and lng:
                location_info.update({
                    'latitude': lat,
                    'longitude': lng,
                    'source': 'geocoded',
                    'accuracy': 'medium'
                })
                
        # Fallback to IP-based location
        else:
            ip_address = self._get_client_ip(request)
            lat, lng, city = self.get_location_from_ip(ip_address)
            if lat and lng:
                location_info.update({
                    'latitude': lat,
                    'longitude': lng,
                    'city': city,
                    'address': f"{city} (approximate from IP)",
                    'source': 'ip',
                    'accuracy': 'low'
                })
                
        return location_info
    
    def _get_client_ip(self, request) -> str:
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class DistanceCalculator:
    """Calculate distances and provide routing information"""
    
    @staticmethod
    def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        try:
            # Convert decimal degrees to radians
            lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
            c = 2 * asin(sqrt(a))
            
            # Radius of earth in kilometers
            r = 6371
            return c * r
        except (ValueError, TypeError, ZeroDivisionError):
            return float('inf')
    
    def get_travel_time_estimate(self, distance_km: float) -> str:
        """
        Estimate travel time based on distance
        Assumes average city traffic conditions
        """
        if distance_km <= 0:
            return "N/A"
        elif distance_km <= 5:
            return f"~{int(distance_km * 4)} minutes"  # 15 km/h in heavy traffic
        elif distance_km <= 15:
            return f"~{int(distance_km * 2)} minutes"  # 30 km/h in moderate traffic
        else:
            return f"~{int(distance_km * 1.5)} minutes"  # 40 km/h highway
    
    def get_directions_url(self, dest_lat: float, dest_lng: float, 
                         origin_lat: float = None, origin_lng: float = None) -> str:
        """
        Generate Google Maps directions URL
        """
        if origin_lat and origin_lng:
            origin = f"{origin_lat},{origin_lng}"
        else:
            origin = "Current+Location"
            
        return f"https://maps.google.com/maps?daddr={dest_lat},{dest_lng}&saddr={origin}"


class HospitalFinder:
    """Find and rank hospitals based on location and blood availability"""
    
    def __init__(self):
        self.distance_calc = DistanceCalculator()
        self.location_service = LocationService()
    
    def find_nearby_hospitals_with_context(self, emergency_request, max_radius_km=25, max_results=5):
        """
        Find nearby hospitals with enhanced location context and ranking
        """
        from .models import EmergencyHospital
        
        if not emergency_request.user_latitude or not emergency_request.user_longitude:
            return []
        
        user_lat = float(emergency_request.user_latitude)
        user_lng = float(emergency_request.user_longitude)
        
        # Get all active emergency partner hospitals
        hospitals = EmergencyHospital.objects.filter(
            is_active=True,
            is_emergency_partner=True
        ).prefetch_related('hospital_blood_stock')
        
        available_hospitals = []
        
        for hospital in hospitals:
            # Check blood availability
            if not hospital.has_sufficient_blood(
                emergency_request.blood_group, 
                emergency_request.quantity_needed
            ):
                continue
            
            # Calculate distance
            distance = self.distance_calc.haversine_distance(
                user_lat, user_lng,
                float(hospital.latitude), float(hospital.longitude)
            )
            
            # Skip if too far
            if distance > max_radius_km:
                continue
            
            # Calculate travel time estimate
            travel_time = self.distance_calc.get_travel_time_estimate(distance)
            
            # Generate directions URL
            directions_url = self.distance_calc.get_directions_url(
                float(hospital.latitude), float(hospital.longitude),
                user_lat, user_lng
            )
            
            # Get blood stock details
            stock_info = hospital.get_available_blood_types()
            
            hospital_info = {
                'hospital': hospital,
                'distance_km': round(distance, 1),
                'travel_time': travel_time,
                'directions_url': directions_url,
                'available_stock': stock_info,
                'priority_score': self._calculate_priority_score(
                    distance, stock_info.get(emergency_request.blood_group, 0),
                    emergency_request.quantity_needed
                )
            }
            
            available_hospitals.append(hospital_info)
        
        # Sort by priority score (lower is better: closer + more stock)
        available_hospitals.sort(key=lambda x: x['priority_score'])
        
        return available_hospitals[:max_results]
    
    def _calculate_priority_score(self, distance: float, available_stock: int, needed_quantity: int) -> float:
        """
        Calculate priority score for hospital ranking
        Lower score = higher priority
        """
        # Base score from distance (0-100)
        distance_score = min(distance * 2, 100)
        
        # Stock availability bonus (subtract from score)
        stock_bonus = min(available_stock / needed_quantity * 20, 50)
        
        # Prefer hospitals with more than needed stock
        if available_stock >= needed_quantity * 2:
            stock_bonus += 10
        
        return distance_score - stock_bonus


def get_location_service():
    """Get singleton instance of LocationService"""
    if not hasattr(get_location_service, '_instance'):
        get_location_service._instance = LocationService()
    return get_location_service._instance


def get_hospital_finder():
    """Get singleton instance of HospitalFinder"""
    if not hasattr(get_hospital_finder, '_instance'):
        get_hospital_finder._instance = HospitalFinder()
    return get_hospital_finder._instance