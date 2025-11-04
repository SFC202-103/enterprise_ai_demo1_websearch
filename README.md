# 🎮 Esports Live Match Tracker

[![Tests](https://img.shields.io/badge/tests-283%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-96.91%25-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.13+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

A comprehensive real-time esports match tracking platform that aggregates live match data from multiple sources across various competitive games. Built with FastAPI, this application provides a modern web interface and RESTful API for tracking matches, teams, players, and community sentiment across the esports ecosystem.

## 🎯 Key Features

### Real-Time Match Tracking
- **Multi-Game Support**: Tracks matches across League of Legends, CS:GO, Dota 2, Apex Legends, and Marvel Rivals
- **Live Updates**: Real-time match status, scores, and player statistics
- **Comprehensive Coverage**: Upcoming, live, and finished matches from multiple data sources

### Data Aggregation
- **8 Data Connectors**: Integrates with PandaScore, Riot Games API, OpenDota, HLTV, Battlefy, Apex Stats, Marvel Rivals API, and Liquipedia
- **Smart Caching**: Efficient data caching to minimize API calls and improve performance
- **Unified Interface**: Single API that normalizes data from multiple sources

### AI-Powered Analysis
- **Interactive AI Chatbot**: Real-time Q&A about matches, players, and strategies
- **Real Data Integration**: Fetches accurate information from Liquipedia, PandaScore, HLTV, and other APIs
- **15+ Question Categories**: Player stats, predictions, history, strategies, comparisons, and more
- **Intelligent Query Routing**: Automatically determines the type of question and fetches relevant data
- **Sentiment Analysis**: AI-driven community sentiment analysis for matches and teams
- **Context-Aware Responses**: AI assistant with comprehensive match context and real-time statistics

### Modern Web Interface
- **Single-Page Application**: Fast, responsive web UI built with vanilla JavaScript
- **Game Filters**: Easy filtering by game type (League of Legends, CS:GO, Dota 2, etc.)
- **Search Functionality**: Quick search for specific teams, matches, or players
- **Match Details**: Detailed match information with team rosters and statistics

### Professional Architecture
- **RESTful API**: Well-documented FastAPI backend with async support
- **Test Coverage**: 96.91% test coverage with 283 passing tests
- **Type Safety**: Full type hints and validation using Pydantic models
- **Logging**: Comprehensive logging for debugging and monitoring

## 🚀 Quick Start

### Prerequisites
- Python 3.13 or higher
- OpenAI API key (for AI features)
- PandaScore API key (optional, for enhanced match data)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/enterprise_ai_demo1_websearch.git
cd enterprise_ai_demo1_websearch
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
Create a `.env` file in the project root:
```env
OPENAI_API_KEY=your_openai_api_key_here
PANDASCORE_API_KEY=your_pandascore_key_here  # Optional
```

4. **Run the application**
```bash
python -m uvicorn src.fastapi_app:app --reload --port 8000
```

5. **Open your browser**
Navigate to `http://localhost:8000` to access the web interface.

## 📡 API Endpoints

### Match Endpoints
- `GET /api/live_matches` - Get all live and upcoming matches
  - Query params: `game` (filter by game), `status` (filter by match status), `provider` (filter by data source)
- `GET /api/matches/{match_id}` - Get specific match details
- `GET /api/match_stats` - Get match statistics (total, live, upcoming, finished counts)

### Team & Player Endpoints
- `GET /api/team_stats` - Get team statistics and performance data
  - Query params: `team_name` (filter by team name)
- `GET /api/player_stats` - Get player statistics and performance data
  - Query params: `player_name` (filter by player name)

### AI Endpoints
- `GET /api/sentiment` - Get AI-powered sentiment analysis
  - Query params: `match_id` (analyze specific match), `team_name` (analyze specific team)
- `GET /api/ai/chat` - Natural language Q&A about esports
  - Query params: `query` (your question)

### Administrative Endpoints
- `GET /api/games` - List all supported games
- `GET /api/tournaments` - Get tournament information
- `POST /api/admin/push_update` - Push match updates (requires admin token)
- `POST /api/admin/sync` - Trigger data synchronization (requires admin token)

## 🎮 Supported Games

| Game | Connector | Features |
|------|-----------|----------|
| League of Legends | Riot API, PandaScore | Live matches, player stats, team data |
| CS:GO | HLTV, PandaScore | Tournament matches, team rankings |
| Dota 2 | OpenDota, PandaScore | Live matches, player profiles, match history |
| Apex Legends | Apex Stats | Tournament brackets, player stats |
| Marvel Rivals | Marvel API | Competitive matches, team rosters |

## 🏗️ Architecture

### Backend Stack
- **FastAPI**: Modern, high-performance web framework
- **Pydantic**: Data validation and settings management
- **httpx**: Async HTTP client for API requests
- **pytest**: Comprehensive test suite with 96.91% coverage

### Data Layer
- **Connector Pattern**: Modular connectors for each data source
- **Response Caching**: Smart caching to reduce API load
- **Data Normalization**: Unified data format across all sources

### Frontend
- **Vanilla JavaScript**: No framework dependencies for fast loading
- **Responsive Design**: Works on desktop and mobile devices
- **Modern UI**: Clean, intuitive interface with real-time updates

## 🧪 Testing

Run the full test suite:
```bash
pytest tests/ -v
```

Run with coverage report:
```bash
pytest tests/ --cov=src --cov-report=html
```

Run specific test categories:
```bash
pytest tests/test_fastapi*.py  # API tests
pytest tests/test_connectors*.py  # Connector tests
pytest tests/test_db*.py  # Database tests
```

## 📊 Project Statistics

- **Total Tests**: 283 (100% passing)
- **Code Coverage**: 96.91%
- **Lines of Code**: 1,391 (excluding tests)
- **API Endpoints**: 15+
- **Data Connectors**: 8
- **Supported Games**: 5+

## 🛠️ Development

### Project Structure
```
enterprise_ai_demo1_websearch/
├── src/
│   ├── fastapi_app.py          # Main FastAPI application (569 lines)
│   ├── connectors/              # Data source connectors
│   │   ├── pandascore_connector.py
│   │   ├── riot_connector.py
│   │   ├── hltv_connector.py
│   │   └── ...
│   ├── client.py               # OpenAI client integration
│   ├── models.py               # Pydantic data models
│   └── db.py                   # Database operations
├── tests/                      # Comprehensive test suite
├── web/
│   └── index.html              # Frontend application
└── docs/                       # Documentation
```

### Adding a New Game Connector

1. Create a new connector in `src/connectors/`:
```python
from typing import List, Dict, Any

class YourGameConnector:
    async def get_matches(self, game: str = None) -> List[Dict[str, Any]]:
        # Implement your data fetching logic
        pass
```

2. Register the connector in `fastapi_app.py`:
```python
connectors.append(YourGameConnector())
```

3. Add tests in `tests/test_connectors*.py`

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure tests pass and coverage remains >96%
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **PandaScore** for comprehensive esports data API
- **Riot Games** for League of Legends data
- **OpenDota** for Dota 2 statistics
- **HLTV** for CS:GO match data
- **OpenAI** for AI-powered features

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ for the esports community**
