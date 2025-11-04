# Testing the Real API Integration

## Quick Start

1. **Start the server:**
   ```bash
   python -m uvicorn src.fastapi_app:app --reload --port 8000
   ```

2. **Open the website:**
   - Navigate to http://localhost:8000
   - You should see 8 demo matches loaded

3. **Test AI Chatbot with Real Data:**
   - Click on any match card
   - Modal opens with match details and AI chatbot
   - Try these test queries:

## Test Queries

### 1. Player Statistics
**Click:** "📊 Player Stats" button  
**Or type:** "Show me the player statistics"  
**Expected:** Real player KDA, win rates from backend API

### 2. Win Prediction
**Click:** "🎯 Win Prediction" button  
**Or type:** "Who will win this match?"  
**Expected:** Win probability percentages based on current score

### 3. Head-to-Head History
**Click:** "📜 Head-to-Head" button  
**Or type:** "What is the history between these teams?"  
**Expected:** List of past matches with scores

### 4. Strategic Analysis
**Click:** "🎮 Key Strategies" button  
**Or type:** "What strategies should I watch for?"  
**Expected:** Team playstyles and tactical analysis

### 5. Team Comparison
**Type:** "Compare these two teams"  
**Expected:** Side-by-side statistics table

### 6. General Questions
Try any of these:
- "What is the current score?"
- "When does this match start?"
- "What tournament is this?"
- "Tell me about the players"
- "Which team is stronger?"

## API Testing (Command Line)

### Test the new endpoint directly:

**1. Overview:**
```bash
curl "http://localhost:8000/api/ai_analysis/demo_lol_1?query_type=overview" | python -m json.tool
```

**2. Player Stats:**
```bash
curl "http://localhost:8000/api/ai_analysis/demo_csgo_1?query_type=players" | python -m json.tool
```

**3. Prediction:**
```bash
curl "http://localhost:8000/api/ai_analysis/demo_dota_1?query_type=prediction" | python -m json.tool
```

**4. History:**
```bash
curl "http://localhost:8000/api/ai_analysis/demo_valorant_1?query_type=history" | python -m json.tool
```

## Expected Behavior

### ✅ Success Case
- API returns `{"ok": true, ...}` with real data
- Frontend displays formatted response with actual statistics
- Response time: 500ms-2s

### ⚠️ Fallback Case
- If API fails, frontend shows demo response
- User sees helpful information even with errors
- Graceful degradation to mock data

### 🔄 Demo Mode
- Set `USE_DEMO_MODE=true` in code
- Uses local fixtures only
- Response time: <100ms

## Verification Checklist

- [ ] Server starts without errors
- [ ] Website loads 8 demo matches
- [ ] Can click match to open modal
- [ ] AI chatbot appears in modal
- [ ] Quick action buttons work
- [ ] Typing custom questions works
- [ ] Responses include real data
- [ ] Error handling works (try invalid match ID)
- [ ] All 15 question categories respond correctly

## Match IDs for Testing

- `demo_lol_1` - T1 vs Gen.G (League of Legends)
- `demo_csgo_1` - FaZe vs Na'Vi (CS:GO)
- `demo_csgo_2` - Team Spirit vs Team Liquid (CS:GO)
- `demo_dota_1` - OG vs Tundra Esports (Dota 2)
- `demo_valorant_1` - Sentinels vs Cloud9 (Valorant)
- `demo_valorant_2` - G2 Esports vs NRG (Valorant)
- `demo_rocket_1` - Vitality vs Heroic (Rocket League)

## Troubleshooting

### Server won't start
- Check Python version: `python --version` (need 3.13+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 not in use

### White screen
- Open browser console (F12)
- Check for JavaScript errors
- Verify API endpoint returning data: `curl http://localhost:8000/api/live_matches`

### AI responses are mock data
- Check `USE_DEMO_MODE=false` in code
- Verify API endpoint: `curl http://localhost:8000/api/ai_analysis/demo_lol_1`
- Check browser Network tab for API calls

### No data from connectors
- API keys may be required
- Check connector configuration
- Demo mode still works with fixtures

## Performance Benchmarks

**Expected Response Times:**
- Page Load: <100ms
- Match Modal Open: <200ms
- AI Chat Response (Demo): <200ms
- AI Chat Response (Real API): 500ms-2s

## Next Steps

After testing, you can:
1. Add API keys for real connectors (PandaScore, HLTV, etc.)
2. Disable demo mode for production
3. Implement caching for faster responses
4. Add more question types
5. Integrate additional data sources

## Support

If you encounter issues:
1. Check `docs/API_INTEGRATION.md` for detailed documentation
2. Review `docs/GETTING_STARTED.md` for setup help
3. Check `docs/DEMO_PLAYBOOK.md` for demo guidance
4. Run tests: `pytest` (should pass 283 tests)
