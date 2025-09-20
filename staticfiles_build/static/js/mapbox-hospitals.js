// Mapbox Integration for Hospital Tracking

// Utility function for user-friendly notifications
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'warning' ? 'warning' : 'info'} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 350px;';
    notification.innerHTML = `
        <i class="fas fa-${type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to document and auto-remove after 5 seconds
    document.body.appendChild(notification);
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

function initMap() {
    map = new mapboxgl.Map({
        container: 'map',
        style: mapStyles[currentMapStyle],
        center: [78.9629, 20.5937], // Center of India
        zoom: 5
    });
    
    map.addControl(new mapboxgl.NavigationControl());
    map.addControl(new mapboxgl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true
    }));
    
    directions = new MapboxDirections({
        accessToken: mapboxgl.accessToken,
        unit: 'metric',
        profile: 'mapbox/driving'
    });
    
    map.on('load', function() {
        addHospitalMarkers();
        getCurrentLocationWithMapbox();
    });
}

function addHospitalMarkers() {
    hospitalLocations.forEach((hospital, index) => {
        const popupHTML = `
            <div class="hospital-popup">
                <h5>${hospital.name}</h5>
                <p><strong>📍 ${hospital.city}</strong></p>
                <p><strong>🚨 Emergency:</strong><br><a href="tel:${hospital.emergency}">${hospital.emergency}</a></p>
                <button onclick="selectHospital(${index})" class="btn btn-primary btn-sm">
                    <i class="fas fa-route"></i> Get Directions
                </button>
            </div>
        `;
        
        const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(popupHTML);
        const marker = new mapboxgl.Marker({ color: '#dc3545' })
            .setLngLat([hospital.lng, hospital.lat])
            .setPopup(popup)
            .addTo(map);
        
        hospitalMarkers.push({ marker, popup, data: hospital, distance: null });
    });
}

function getCurrentLocationWithMapbox() {
    if (!navigator.geolocation) return;
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            userLatitude = position.coords.latitude;
            userLongitude = position.coords.longitude;
            
            if (userMarker) userMarker.remove();
            
            userMarker = new mapboxgl.Marker({ color: '#007bff' })
                .setLngLat([userLongitude, userLatitude])
                .addTo(map);
            
            map.flyTo({ center: [userLongitude, userLatitude], zoom: 12 });
            calculateDistances();
        }
    );
}

function calculateDistances() {
    if (!userLatitude || !userLongitude) return;
    
    hospitalMarkers.forEach(hospitalMarker => {
        const distance = calculateHaversineDistance(
            userLatitude, userLongitude,
            hospitalMarker.data.lat, hospitalMarker.data.lng
        );
        hospitalMarker.distance = distance;
        updateHospitalCardDistance(hospitalMarker.data.name, distance);
    });
}

function calculateHaversineDistance(lat1, lng1, lat2, lng2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function updateHospitalCardDistance(hospitalName, distance) {
    const hospitalCards = document.querySelectorAll('.hospital-card');
    hospitalCards.forEach(card => {
        const nameElement = card.querySelector('.hospital-name');
        if (nameElement && nameElement.textContent.includes(hospitalName)) {
            const distanceBadge = document.createElement('div');
            distanceBadge.className = 'badge bg-success position-absolute';
            distanceBadge.style.cssText = 'top: 1rem; left: 1rem; font-size: 0.8rem; z-index: 10;';
            distanceBadge.innerHTML = `<i class="fas fa-map-marker-alt me-1"></i>${distance.toFixed(1)} km`;
            
            const header = card.querySelector('.hospital-header');
            if (header) {
                header.style.position = 'relative';
                const existingBadge = header.querySelector('.badge');
                if (existingBadge) existingBadge.remove();
                header.appendChild(distanceBadge);
            }
        }
    });
}

function showAllHospitals() {
    if (hospitalMarkers.length > 0) {
        const bounds = new mapboxgl.LngLatBounds();
        hospitalMarkers.forEach(hospitalMarker => {
            bounds.extend([hospitalMarker.data.lng, hospitalMarker.data.lat]);
        });
        map.fitBounds(bounds, { padding: 50 });
    }
}

function showNearbyHospitals() {
    if (!userLatitude || !userLongitude) {
        // Show user-friendly notification
        showNotification('Please enable location access to find nearby hospitals.', 'warning');
        return;
    }
    
    const maxDistance = 100;
    hospitalMarkers.forEach(hospitalMarker => {
        if (hospitalMarker.distance && hospitalMarker.distance <= maxDistance) {
            hospitalMarker.marker.getElement().style.display = 'block';
        } else {
            hospitalMarker.marker.getElement().style.display = 'none';
        }
    });
}

function selectHospital(index) {
    selectedHospital = hospitalMarkers[index];
    const hospital = selectedHospital.data;
    
    if (userLatitude && userLongitude) {
        directions.setOrigin([userLongitude, userLatitude]);
        directions.setDestination([hospital.lng, hospital.lat]);
        
        document.getElementById('distance-info').style.display = 'block';
        const distance = selectedHospital.distance || 0;
        document.getElementById('distance-text').innerHTML = `
            <strong>Route to ${hospital.name}:</strong><br>
            Distance: ${distance.toFixed(1)} km<br>
            Emergency: ${hospital.emergency}
        `;
        
        map.flyTo({ center: [hospital.lng, hospital.lat], zoom: 14 });
    } else {
        // Show user-friendly notification
        showNotification('Please enable location access to get directions to the hospital.', 'warning');
    }
}

function toggleDirections() {
    if (map.hasControl(directions)) {
        map.removeControl(directions);
        document.getElementById('distance-info').style.display = 'none';
    } else {
        map.addControl(directions, 'top-left');
    }
}

function changeMapStyle() {
    currentMapStyle = (currentMapStyle + 1) % mapStyles.length;
    map.setStyle(mapStyles[currentMapStyle]);
}

function flyToIndia() {
    map.flyTo({ center: [78.9629, 20.5937], zoom: 5 });
}

document.addEventListener('DOMContentLoaded', function() {
    initMap();
});