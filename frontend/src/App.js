import React, { useState, useEffect } from 'react';
import '@/App.css';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Zap, Navigation, Settings, Filter, MapPin, Plug, Clock, CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { toast } from 'sonner';
import { Toaster } from '@/components/ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxNiIgY3k9IjE2IiByPSIxMiIgZmlsbD0iIzIyQzU1RSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIi8+PC9zdmc+',
  iconUrl: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxNiIgY3k9IjE2IiByPSIxMiIgZmlsbD0iIzIyQzU1RSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIi8+PC9zdmc+',
  shadowUrl: null,
});

const getMarkerIcon = (available, stalls) => {
  const availability = (available / stalls) * 100;
  let color = '#22C55E';
  if (availability < 30) color = '#EF4444';
  else if (availability < 60) color = '#EAB308';

  const svgIcon = `<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="16" cy="16" r="12" fill="${color}" stroke="white" stroke-width="2"/>
    <path d="M16 10L14 18H18L16 22" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`;

  return L.divIcon({
    html: svgIcon,
    className: 'custom-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

const getStatusIcon = (available, stalls) => {
  const availability = (available / stalls) * 100;
  if (availability >= 60) return <CheckCircle className="w-5 h-5 text-green-500" />;
  if (availability >= 30) return <AlertCircle className="w-5 h-5 text-yellow-500" />;
  return <XCircle className="w-5 h-5 text-red-500" />;
};

function App() {
  const [superchargers, setSuperchargers] = useState([]);
  const [selectedCharger, setSelectedCharger] = useState(null);
  const [vehicleModel, setVehicleModel] = useState('Model 3 Long Range');
  const [currentCharge, setCurrentCharge] = useState(80);
  const [amenityFilters, setAmenityFilters] = useState({
    restrooms: false,
    food: false,
    wifi: false,
    shopping: false,
    lounge: false,
  });
  const [tripOrigin, setTripOrigin] = useState('');
  const [tripDestination, setTripDestination] = useState('');
  const [plannedTrip, setPlannedTrip] = useState(null);
  const [mapCenter, setMapCenter] = useState([39.8283, -98.5795]);
  const [mapZoom, setMapZoom] = useState(5);

  useEffect(() => {
    fetchSuperchargers();
  }, []);

  const fetchSuperchargers = async () => {
    try {
      const response = await axios.get(`${API}/superchargers`);
      setSuperchargers(response.data);
    } catch (error) {
      console.error('Error fetching superchargers:', error);
      toast.error('Failed to load superchargers');
    }
  };

  const handlePlanTrip = async () => {
    if (!tripOrigin || !tripDestination) {
      toast.error('Please enter both origin and destination');
      return;
    }

    const originCoords = tripOrigin.split(',').map(coord => parseFloat(coord.trim()));
    const destCoords = tripDestination.split(',').map(coord => parseFloat(coord.trim()));

    if (originCoords.length !== 2 || destCoords.length !== 2 || originCoords.some(isNaN) || destCoords.some(isNaN)) {
      toast.error('Invalid coordinates. Use format: lat, lng');
      return;
    }

    try {
      const response = await axios.post(`${API}/trips/plan`, {
        origin: { lat: originCoords[0], lng: originCoords[1] },
        destination: { lat: destCoords[0], lng: destCoords[1] },
        vehicleModel,
        currentCharge,
      });
      setPlannedTrip(response.data);
      setMapCenter([originCoords[0], originCoords[1]]);
      setMapZoom(7);
      toast.success(`Trip planned with ${response.data.stops.length} charging stops`);
    } catch (error) {
      console.error('Error planning trip:', error);
      toast.error('Failed to plan trip');
    }
  };

  const toggleAmenityFilter = (amenity) => {
    setAmenityFilters(prev => ({ ...prev, [amenity]: !prev[amenity] }));
  };

  const filteredSuperchargers = superchargers.filter(sc => {
    const activeFilters = Object.entries(amenityFilters)
      .filter(([_, isActive]) => isActive)
      .map(([amenity]) => amenity);
    
    if (activeFilters.length === 0) return true;
    return activeFilters.every(filter => sc.amenities.includes(filter));
  });

  const routeCoordinates = plannedTrip ? [
    [plannedTrip.origin.lat, plannedTrip.origin.lng],
    ...plannedTrip.stops.map(stop => [stop.location.lat, stop.location.lng]),
    [plannedTrip.destination.lat, plannedTrip.destination.lng],
  ] : [];

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      <Toaster position="top-right" theme="dark" />
      
      {/* Map Background */}
      <div className="absolute inset-0 z-0">
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          className="w-full h-full"
          zoomControl={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {filteredSuperchargers.map(sc => (
            <Marker
              key={sc.id}
              position={[sc.location.lat, sc.location.lng]}
              icon={getMarkerIcon(sc.available, sc.stalls)}
              eventHandlers={{
                click: () => setSelectedCharger(sc),
              }}
            >
              <Popup>
                <div className="text-zinc-900">
                  <h3 className="font-bold text-sm">{sc.name}</h3>
                  <p className="text-xs">{sc.available}/{sc.stalls} available</p>
                </div>
              </Popup>
            </Marker>
          ))}

          {routeCoordinates.length > 0 && (
            <Polyline
              positions={routeCoordinates}
              color="#3B82F6"
              weight={4}
              opacity={0.8}
            />
          )}
        </MapContainer>
      </div>

      {/* Top Bar */}
      <div className="absolute top-0 left-0 right-0 z-10 p-4">
        <div className="glass-panel rounded-2xl p-4 max-w-md">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center neon-glow-red">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white" data-testid="app-title">Supercharger Network</h1>
              <p className="text-xs text-zinc-400">{filteredSuperchargers.length} stations available</p>
            </div>
          </div>
        </div>
      </div>

      {/* Left Sidebar - Filters & Trip Planner */}
      <div className="absolute left-4 top-24 bottom-4 z-10 w-80 glass-panel rounded-2xl p-6 overflow-y-auto">
        <div className="space-y-6">
          {/* Vehicle Settings */}
          <div data-testid="vehicle-settings-section">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="w-5 h-5 text-primary" />
              <h2 className="text-lg font-bold text-white">Vehicle Settings</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <Label className="text-zinc-300 text-sm">Model</Label>
                <Select value={vehicleModel} onValueChange={setVehicleModel}>
                  <SelectTrigger className="bg-zinc-950/50 border-zinc-800 text-white" data-testid="vehicle-model-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-800">
                    <SelectItem value="Model 3 Long Range">Model 3 Long Range</SelectItem>
                    <SelectItem value="Model 3 Performance">Model 3 Performance</SelectItem>
                    <SelectItem value="Model S">Model S</SelectItem>
                    <SelectItem value="Model X">Model X</SelectItem>
                    <SelectItem value="Model Y">Model Y</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-zinc-300 text-sm mb-2 block">Current Charge: {currentCharge}%</Label>
                <Slider
                  value={[currentCharge]}
                  onValueChange={([value]) => setCurrentCharge(value)}
                  max={100}
                  step={5}
                  className="w-full"
                  data-testid="charge-slider"
                />
              </div>
            </div>
          </div>

          {/* Amenity Filters */}
          <div data-testid="amenity-filters-section">
            <div className="flex items-center gap-2 mb-4">
              <Filter className="w-5 h-5 text-primary" />
              <h2 className="text-lg font-bold text-white">Filter by Amenities</h2>
            </div>
            
            <div className="space-y-3">
              {Object.entries(amenityFilters).map(([amenity, isActive]) => (
                <div key={amenity} className="flex items-center gap-2">
                  <Checkbox
                    id={amenity}
                    checked={isActive}
                    onCheckedChange={() => toggleAmenityFilter(amenity)}
                    className="border-zinc-700 data-[state=checked]:bg-primary"
                    data-testid={`amenity-filter-${amenity}`}
                  />
                  <Label htmlFor={amenity} className="text-zinc-300 text-sm capitalize cursor-pointer">
                    {amenity}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          {/* Trip Planner */}
          <div data-testid="trip-planner-section">
            <div className="flex items-center gap-2 mb-4">
              <Navigation className="w-5 h-5 text-primary" />
              <h2 className="text-lg font-bold text-white">Trip Planner</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <Label className="text-zinc-300 text-sm">Origin (lat, lng)</Label>
                <Input
                  placeholder="37.7749, -122.4194"
                  value={tripOrigin}
                  onChange={(e) => setTripOrigin(e.target.value)}
                  className="bg-zinc-950/50 border-zinc-800 text-white placeholder:text-zinc-600"
                  data-testid="trip-origin-input"
                />
              </div>

              <div>
                <Label className="text-zinc-300 text-sm">Destination (lat, lng)</Label>
                <Input
                  placeholder="34.0522, -118.2437"
                  value={tripDestination}
                  onChange={(e) => setTripDestination(e.target.value)}
                  className="bg-zinc-950/50 border-zinc-800 text-white placeholder:text-zinc-600"
                  data-testid="trip-destination-input"
                />
              </div>

              <Button
                onClick={handlePlanTrip}
                className="w-full bg-primary hover:bg-primary/90 text-white rounded-full font-bold neon-glow-red transition-all hover:scale-105"
                data-testid="plan-trip-button"
              >
                <Navigation className="w-4 h-4 mr-2" />
                Plan Trip
              </Button>
            </div>

            {plannedTrip && (
              <div className="mt-4 p-4 bg-zinc-900/50 rounded-xl border border-zinc-800" data-testid="trip-summary">
                <h3 className="text-sm font-bold text-white mb-2">Trip Summary</h3>
                <div className="space-y-1 text-xs text-zinc-400">
                  <p>Distance: {plannedTrip.totalDistance.toFixed(0)} km</p>
                  <p>Duration: {plannedTrip.totalTime.toFixed(1)} hours</p>
                  <p>Charging Stops: {plannedTrip.stops.length}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Sidebar - Selected Charger Details */}
      {selectedCharger && (
        <div className="absolute right-4 top-24 bottom-4 z-10 w-96 glass-panel rounded-2xl p-6 overflow-y-auto" data-testid="charger-details-panel">
          <div className="space-y-6">
            <div>
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  {getStatusIcon(selectedCharger.available, selectedCharger.stalls)}
                  <h2 className="text-xl font-bold text-white">{selectedCharger.name}</h2>
                </div>
                <button
                  onClick={() => setSelectedCharger(null)}
                  className="text-zinc-400 hover:text-white transition-colors"
                  data-testid="close-details-button"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
              <p className="text-sm text-zinc-400">{selectedCharger.address}</p>
              <p className="text-xs text-zinc-500">{selectedCharger.city}, {selectedCharger.state}</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800">
                <div className="flex items-center gap-2 mb-1">
                  <Plug className="w-4 h-4 text-secondary" />
                  <p className="text-xs text-zinc-400">Available</p>
                </div>
                <p className="text-2xl font-bold text-white">{selectedCharger.available}/{selectedCharger.stalls}</p>
              </div>

              <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800">
                <div className="flex items-center gap-2 mb-1">
                  <Zap className="w-4 h-4 text-secondary" />
                  <p className="text-xs text-zinc-400">Power</p>
                </div>
                <p className="text-2xl font-bold text-white">{selectedCharger.power}kW</p>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-primary" />
                Amenities
              </h3>
              <div className="flex flex-wrap gap-2">
                {selectedCharger.amenities.map(amenity => (
                  <span
                    key={amenity}
                    className="px-3 py-1 bg-secondary/10 text-secondary border border-secondary/20 rounded-full text-xs font-medium backdrop-blur-md"
                  >
                    {amenity}
                  </span>
                ))}
              </div>
            </div>

            {selectedCharger.busyHours.length > 0 && (
              <div>
                <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-primary" />
                  Busy Hours
                </h3>
                <div className="space-y-2">
                  {selectedCharger.busyHours.map((range, idx) => (
                    <div
                      key={idx}
                      className="px-3 py-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-xs text-yellow-300"
                    >
                      {range.start} - {range.end}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Button
              className="w-full bg-secondary/10 text-secondary hover:bg-secondary/20 border border-secondary/20 rounded-full font-medium backdrop-blur-md transition-all hover:scale-105"
              data-testid="navigate-button"
            >
              <Navigation className="w-4 h-4 mr-2" />
              Navigate
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
