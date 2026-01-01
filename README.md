# AI Traffic for MSFS 2020

Real-time AI aircraft traffic injection for Microsoft Flight Simulator 2020, providing immersive and realistic air traffic scenarios.

## Description

This project reads real-time flight data from FlightRadar24 and injects AI aircraft into Microsoft Flight Simulator 2020 (MSFS 2020). It supports various types of AI traffic injection:

- **Ground-based traffic**: Departure and arrival aircraft at airports
- **En-route traffic**: Aircraft in cruise phase using multiple data sources
- **Parked aircraft**: Static aircraft at gates during ground operations

The system dynamically manages AI traffic based on your current flight position to maintain performance while providing realism.

## Project Structure

```
AI_Traffic_Msfs2020/
├── FS_Hud_injector.py           # Main traffic injection script
├── Real_Time_AiInjector.py      # Alternative injector script
├── Run.bat                      # Windows batch runner
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── config_msfs.json             # Main configuration file
├── Database/                    # SQLite databases
│   ├── Airport.sqlite          # Airport information
│   ├── Approach.sqlite         # Approach/Departure procedures
│   ├── Waypoints.sqlite        # Navigation waypoints
│   └── callsign_data.sqlite    # Airline codes and call signs
├── Ai_Flight_Plans/            # Generated flight plan files
├── VMR_Files/                  # Model matching rules
│   ├── AIG.vmr                # AIG liveries
│   ├── FSLTL_Rules.vmr        # FSLTL liveries
│   └── FSTraffic.vmr          # FSTraffic liveries
├── FlightPlannerCli/           # Flight planning component
└── Sim_Connect_Custom/         # Custom SimConnect interface
```

## Features

### Traffic Types
- **Arrival Traffic**: Aircraft following instrument approaches and STARs
- **Departure Traffic**: Aircraft using SIDs and climbing to cruise altitudes
- **Cruise Traffic**: En-route aircraft retrieved from ADS-B Exchange and Volanta APIs
- **Parked Traffic**: Aircraft at departure gates awaiting clearance

### Aircraft Systems
- **Model Matching**: Automatic livery matching with AIG, FSLTL, and FSTraffic models
- **Flight Planning**: Integration with FlightPlannerCli for IFR route generation
- **Active ATC**: Continuous air traffic control integration
- **Performance Optimization**: Auto-removal of distant aircraft to maintain FPS

### Flight Dynamics
- **Minimum Separation**: 5 NM lateral separation during approaches
- **Smooth Transitions**: Realistic ground speeds and altitude management
- **Wind-Aware Routing**: Uses SimBrief for wind-optimized runway selection

### Real-Time Data Sources
- **FlightRadar24**: For arrivals and departures
- **Airlabs Exchange API**: For en-route cruise traffic
- **Volanta API**: Alternative real-time flight data
- **Little NavMap Database**: Navigation data and procedures


## Prerequisites

### Software Requirements
- **Python 3.8+**: Required runtime environment
- **Microsoft Flight Simulator 2020**: The flight simulator this tool enhances
- **SimBrief Account**: For flight plan generation and active runway information
- **FSLTL Base Package**: For AI aircraft models and liveries
- **RapidAPI Account**: For ADS-B Exchange API access

### API Requirements
- **ADS-B Exchange API**: For real-time cruise traffic data
  - Sign up at: https://rapidapi.com/adsbx/api/adsbx-flight-sim-traffic/pricing
  - Requires a paid subscription for full access

### Hardware/System Requirements
- Sufficient system memory for handling AI traffic (4GB+ RAM recommended)
- Active internet connection for real-time flight data
- MSFS 2020 installed with community folder properly configured

### Flight Plan Requirements
- **Pre-filed SimBrief flight plan**: Required for proper operation
- **Airport Compatibility**: Departure and destination airports must have medium and large gates
- **Navigation Database**: Little NavMap database must be available

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/NerdAtWork24X7/AI_Traffic_Msfs2020.git
git submodule update
cd AI_Traffic_Msfs2020
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Access
Create `config_user.json` with your API credentials:
```json
{
  "AirLab_key": "your-adsbx-api-key-here",
  "simbrief_username": "your-simbrief-username"
}
```

### 4. Verify MSFS Installation
Ensure MSFS 2020 is properly installed and FSLTL AI models are available in the community folder.

## Configuration

### Configuration Files

The system uses two configuration files:

#### `config_user.json` - User Credentials
This file contains your personal API keys and must be created:
```json
{
  "AirLab_key": "your-adsbx-api-key-here",
  "simbrief_username": "your-simbrief-username"
}
```

#### `config_msfs.json` - System Settings
This file contains customizable parameters and is included in the repository:
```json
{
  "USE_FSTRAFFIC_LIVERY": true,
  "USE_AIG_LIVERY": true,
  "USE_FSLTL_LIVERY": true,
  "DEPART_REALTIME": true,
  "MAX_ARRIVAL_AI_FLIGHTS": 30,
  "MAX_DEPARTURE_AI_FLIGHTS": 30,
  "MAX_CRUISE_AI_FLIGHTS": 30,
  "MAX_PARKED_AI_FLIGHTS": 50,
  "CRUISE_ALTITUDE": 10000,
  "SRC_GROUND_RANGE": 50,
  "DES_GROUND_RANGE": 150,
  "GROUND_INJECTION_TIME_ARR": 2,
  "GROUND_INJECTION_TIME_DEP": 2,
  "CRUISE_INJECTION_TIME": 5,
  "SPAWN_DIST": 200,
  "SPAWN_ALTITUDE": 20000,
  "MIN_SEPARATION": 10
}
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `USE_FSTRAFFIC_LIVERY` | `true` | Enable FSTraffic livery matching |
| `USE_AIG_LIVERY` | `true` | Enable AIG livery matching |
| `USE_FSLTL_LIVERY` | `true` | Enable FSLTL livery matching |
| `DEPART_REALTIME` | `true` | Use real-time departure scheduling |
| `MAX_*_AI_FLIGHTS` | 20-50 | Maximum aircraft per traffic type |
| `CRUISE_ALTITUDE` | 10000 | Minimum altitude for cruise traffic (ft) |
| `SRC_GROUND_RANGE` | 50 | Distance for departure airport (km) |
| `DES_GROUND_RANGE` | 150 | Distance for arrival airport (km) |
| `SPAWN_DIST` | 200 | Maximum distance for traffic spawning (km) |
| `MIN_SEPARATION` | 10 | Minimum aircraft separation (km) |

## Usage

### Quick Start (Windows)
```batch
# Run the main script (recommended)
Run.bat

# Or run manually
python FS_Hud_injector.py
```

### Multi-Script Operation

The project includes two main scripts - use them together for optimal performance:

#### 1. FS_Hud_injector.py (Primary)
The main traffic injection script with comprehensive functionality.

#### 2. Real_Time_AiInjector.py (Legacy/Alternative)
Legacy script with basic functionality.

### Detailed Usage Workflow

1. **Prepare Flight Plan**
   - Create and file a flight plan on SimBrief.com
   - Note your departure and destination airports

2. **Launch MSFS 2020**
   - Start Microsoft Flight Simulator 2020
   - Load your aircraft at the departure airport
   - Wait for complete world loading

3. **Start Traffic Injection**
   - Run `python FS_Hud_injector.py` or double-click `Run.bat`
   - The system will automatically detect your flight and begin traffic injection

4. **Monitor Operation**
   - Traffic injection starts automatically based on your location
   - Ground traffic appears near airports, en-route traffic in cruise areas
   - The system optimizes performance by removing distant aircraft

### Expected Behavior
- **At Departure Airport**: Arrival traffic, departure traffic, parked aircraft
- **In Cruise**: En-route traffic following real flight paths
- **At Destination Airport**: Arrival traffic, departure traffic from the destination


## Troubleshooting

### Common Issues

**Traffic not appearing:**
- Verify your SimBrief flight plan is correctly filed
- Check that `config_user.json` contains valid API credentials
- Ensure FSLTL AI models are installed in MSFS community folder
- Confirm airport has medium/large gates (not just small ones)

**Script crashes:**
- Verify all Python dependencies are installed
- Check internet connection for flight data APIs
- Ensure MSFS is running and properly loaded

**Performance Issues:**
- Reduce MAX_*_AI_FLIGHTS parameters in config_msfs.json
- Increase MIN_SEPARATION distance
- Decrease SPAWN_DIST to remove distant aircraft sooner

### Performance Tips
- Use the latest version of FSLTL for best model matching
- Keep your graphics settings reasonable while running AI traffic
- Monitor your frame rate and adjust settings accordingly

## Disclaimer

- **Educational Purpose**: This project is developed for educational and entertainment purposes only
- **Data Usage**: Use FlightRadar24 and other flight data sources responsibly
- **No Liability**: The author accepts no responsibility for issues arising from use
- **API Costs**: Third-party API services may require paid subscriptions

## Credits & Acknowledgments

This project builds upon the work of many talented developers and projects:

### Core Dependencies
- **Little NavMap Database** - Navigation and airport data
- **FSLTL Base Package** - AI aircraft models and flight dynamics
- **FSTraffic & AIG Liveries** - High-quality aircraft model packages
- **SimConnect** - Microsoft Flight Simulator connectivity interface

### Python Libraries
- **pandas & geopy** - Data processing and geographic calculations
- **requests** - API communication
- **selenium** - Web scraping for flight data
- **undetected-chromedriver** - Chrome automation

### Data Sources
- **FlightRadar24** - Real-time flight tracking
- **ADS-B Exchange** - The world's largest source of real-time flight data
- **Volanta API** - Alternative flight tracking service

## Contributing

Contributions are highly welcome! This project is in active development and could benefit from:

### Ways to Contribute
- **Bug Reports**: Open issues for problems you encounter
- **Feature Requests**: Suggest new functionality or improvements
- **Code Contributions**: Submit pull requests with enhancements
- **Documentation**: Help improve this README or inline code documentation

### Development Setup
```bash
# Fork and clone the repository
git clone https://github.com/your-username/AI_Traffic_Msfs2020.git
cd AI_Traffic_Msfs2020

# Create a feature branch
git checkout -b feature/your-feature-name

# Install development dependencies
pip install -r requirements.txt

# Make your changes and test thoroughly
# Then submit a pull request
```

### Code Quality
- Follow PEP 8 Python style guidelines
- Add comments for complex logic
- Test changes with your flight setup before submitting
- Document new configuration parameters

## License

This project is released under the MIT License. See the [LICENSE](LICENSE) file in the FlightPlannerCli subdirectory for details.

## Contact

**Project Author**: NerdAtWork24X7
**Project URL**: https://github.com/NerdAtWork24X7/AI_Traffic_Msfs2020

For questions, issues, or suggestions, please use the GitHub Issues page.

---

*Last updated: January 2026*
