# Calendar Sync AI Agent 🤖📅

An AI-powered chatbot that helps therapists sync their Google Calendar with TherapyAppointment using browser automation, automatically blocking out busy times so clients can't double-book.

## 🎯 Project Overview

Since TherapyAppointment doesn't offer a public API, this agent uses **Playwright browser automation** to interact with the web interface. This is a real-world solution that demonstrates:
- Agentic AI decision-making
- Natural language interaction with LLMs
- Browser automation for platforms without APIs
- Multi-system integration

## Features

- 💬 **Natural Language Interface** - Chat with the AI to sync calendars
- 🔄 **Automated Syncing** - Blocks TherapyAppointment times based on Google Calendar events
- 🌐 **Browser Automation** - Uses Playwright to control TherapyAppointment web interface
- 📊 **Event Viewing** - Ask about upcoming appointments
- 🧠 **LLM-Powered** - Uses Ollama with function calling for intelligent interactions

## Quick Start

### Prerequisites
- Python 3.8+
- Ollama installed
- TherapyAppointment account
- Google Calendar

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/calendar-sync-agent.git
cd CalendarAssistant
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
playwright install
```

3. **Install and setup Ollama**
```bash
# Download from https://ollama.com
ollama pull llama3.1
```

4. **Configure credentials**

Create a `.env` file:

Edit `.env` with your credentials:
```
THERAPY_APPOINTMENT_EMAIL=your_email@example.com
THERAPY_APPOINTMENT_PASSWORD=your_password
THERAPY_APPOINTMENT_URL=https://www.therapyappointment.com
```

5. **Setup Google Calendar API**
- Visit [Google Cloud Console](https://console.cloud.google.com/).
- Sign in with the same Google account you use for your personal calendar.
- This is where you’ll manage access to Google APIs.

### Create a New Project

1. Click the project dropdown at the top → **New Project**.  
2. Give it a name like **MyCalendarAPI** and click **Create**.  
3. Once created, make sure it’s selected in the top bar.

### Enable the Google Calendar API

1. In the left sidebar, go to **APIs & Services → Library**.  
2. Search for **Google Calendar API**.  
3. Click it → **Enable**.  
4. This activates the Calendar API for your project.

### Set Up the OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**.  
2. Choose **External** (this just means it’s for any Google account, including your own).  
3. Fill in basic info:
   - **App name:** e.g., `My Calendar Reader`
   - **User support email:** your Gmail
   - **Developer contact email:** your Gmail  
4. Click **Save and Continue** through the *Scopes* and *Test Users* pages (you can leave them blank).  
5. On the Summary page, click **Back to Dashboard**.

### Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**.  
2. Click **+ Create Credentials → OAuth client ID**.  
3. Choose **Application type → Desktop app**.  
4. Name it something like `CalendarDesktopClient`.  
5. Click **Create**.

### Download Your Client Secret File

1. You’ll now see your **Client ID** and **Client Secret**.  
2. Click **Download JSON**
3. Save or rename it to `credentials.json` and place it in your project’s root folder (same place as your Python script).  
> 💡 This file is what your code uses to authenticate with your Google account.
Once you’ve done this, you’re ready to use the `credentials.json` file in your code to authenticate and read calendar events.

### Add your email to test users

1. Go to "API & Services" and then select "OAuth Consent Screen" from the left menu
2. Click "Audience" in the new tab that appears on the left
3. Scroll down to Test Users and select "Add users"
4. Type in your email and hit Save

## Usage

Run the agent:
```bash
python calendar_agent.py
```

Chat naturally with the AI:
```
You: Sync my calendar for the next week

🤖 Agent: I'll sync your Google Calendar with TherapyAppointment now.
         Let me check your upcoming events...
         
🤖 Executing: sync_calendars
📅 Fetching events from Google Calendar...
✓ Found 5 events to sync
🌐 Opening TherapyAppointment...
🔐 Logging in...
✓ Login successful
📅 Navigating to calendar settings...
⏰ Blocking: Team Meeting (2024-10-21T09:00:00 - 2024-10-21T10:00:00)
   ✓ Blocked successfully
⏰ Blocking: Dentist (2024-10-22T14:00:00 - 2024-10-22T15:00:00)
   ✓ Blocked successfully
...

🤖 Agent: Done! I've blocked 5 time slots in TherapyAppointment to match 
         your Google Calendar. Your clients won't be able to book during 
         those times.
```

## Project Structure

```
calendar-sync-agent/
├── calendar_agent.py          # Main agent with Playwright automation
├── requirements.txt           # Python dependencies
├── .env                       # Your credentials (create this)
├── credentials.json          # Google OAuth (download this)
├── token.pickle              # Generated after first auth
├── .gitignore
└── README.md
```

## How It Works

```
┌─────────────┐
│   Therapist │
│   Types:    │
│"Sync my cal"│
└──────┬──────┘
       │
       v
┌──────────────────┐
│  Ollama LLM      │
│  (llama3.1)      │
│  Understands     │
│  Intent          │
└──────┬───────────┘
       │
       v
┌──────────────────┐
│ Function Calling │
│ Triggers:        │
│ sync_calendars() │
└──────┬───────────┘
       │
       ├───────────────────┐
       v                   v
┌──────────────┐    ┌──────────────────┐
│Google Calendar│    │  Playwright      │
│     API       │    │  Browser         │
│Get events     │    │  Automation      │
└──────┬────────┘    └──────┬───────────┘
       │                    │
       │                    v
       │             ┌──────────────────┐
       │             │TherapyAppointment│
       │             │  Web Interface   │
       │             │  Block times     │
       └─────────────►──────────────────┘
                     
                Result: Calendar Synced! ✅
```

## Key Features Explained

### 1. AI-Powered Interaction
The LLM (Ollama) understands natural language and decides when to call functions:
- "Sync my calendar" → Calls `sync_calendars()`
- "What's on my calendar tomorrow?" → Calls `get_upcoming_events()`
- Can be extended with more functions

### 2. Browser Automation
Playwright controls a real browser to:
- Login to TherapyAppointment
- Navigate to availability settings
- Fill out forms to block times
- Handle dynamic content and JavaScript

### 3. Smart Syncing
- Only syncs time-based events (skips all-day events)
- Customizable sync window (default: 7 days ahead)
- Prevents double-bookings automatically
- Maintains event privacy (only blocks times, not details)

## Configuration Options

### Environment Variables

```bash
# Required
THERAPY_APPOINTMENT_EMAIL=your_email@example.com
THERAPY_APPOINTMENT_PASSWORD=your_password

# Optional
THERAPY_APPOINTMENT_URL=https://www.therapyappointment.com
OLLAMA_MODEL=llama3.1
```

### Customization

**Change sync window:**
```
You: Sync my calendar for the next 14 days
```

**Change Ollama model:**
Edit `calendar_agent.py`:
```python
agent = CalendarSyncAgent(model_name="mistral")
```

**Run browser in headless mode:**
Edit line in `TherapyAppointmentAutomation.block_multiple_times()`:
```python
browser = await p.chromium.launch(headless=True)  # Change to True
```

## Troubleshooting

### Ollama Issues

**"Connection refused"**
```bash
# Make sure Ollama is running
ollama serve
```

**"Model not found"**
```bash
ollama pull llama3.1
```

### Google Calendar Issues

**"credentials.json not found"**
- Download OAuth credentials from Google Cloud Console
- Place in project root directory

**"Permission denied"**
- Delete `token.pickle` and re-authenticate
- Make sure Calendar API is enabled in Google Cloud

### Playwright Issues

**"Browser not found"**
```bash
playwright install
```

**"Element not found" or "Timeout"**
- You need to update the selectors for TherapyAppointment
- See [PLAYWRIGHT_SETUP.md](PLAYWRIGHT_SETUP.md) for detailed guide
- Use `PWDEBUG=1 python calendar_agent.py` to debug

**"Login failed"**
- Verify credentials in `.env` file
- Check if TherapyAppointment changed their login page
- Update selectors in `_login()` method

### TherapyAppointment Issues

**"Can't find availability page"**
- Login manually and note the URL structure
- Update `_navigate_to_availability()` method with correct URL/selectors

**"Times not blocking"**
- Inspect the form fields in TherapyAppointment
- Update selectors in `_block_time_slot()` method
- Check if date/time format matches what TherapyAppointment expects

## Development

### Running in Debug Mode

```bash
# Playwright inspector mode
PWDEBUG=1 python calendar_agent.py

# Slow motion (see each action)
# Edit code: slow_mo=1000 in browser.launch()
```

### Adding New Functions

To add new capabilities (e.g., analytics), add to the `tools` list in `chat()`:

```python
{
    'type': 'function',
    'function': {
        'name': 'analyze_booking_trends',
        'description': 'Analyzes booking patterns over time',
        'parameters': {...}
    }
}
```

Then implement the function in the `CalendarSyncAgent` class.

## Future Enhancements

- [ ] 📊 **Analytics Dashboard** - "Show me booking trends this month"
- [ ] 🔔 **Proactive Notifications** - Alert when conflicts detected
- [ ] ⏰ **Scheduled Syncs** - Auto-sync every hour
- [ ] 📱 **Web Interface** - Replace CLI with web UI
- [ ] 🎯 **Smart Filtering** - Ignore certain calendar types
- [ ] 🔄 **Bi-directional Sync** - Sync TherapyAppointment → Google Calendar
- [ ] 📧 **Email Summaries** - Daily sync reports
- [ ] 🤖 **More AI Features** - Suggest optimal scheduling times

## Security & Privacy

### Data Handling
- ✅ Event details stay private (only times are synced)
- ✅ Credentials stored in `.env` (not in code)
- ✅ Google tokens stored locally (`token.pickle`)
- ✅ Browser sessions are temporary

### Best Practices
- 🔒 Never commit `.env` file
- 🔒 Use environment variables for secrets
- 🔒 Regularly rotate passwords
- 🔒 Review TherapyAppointment's Terms of Service
- 🔒 Keep dependencies updated

### HIPAA Compliance
If handling PHI (Protected Health Information):
- Ensure encrypted connections (HTTPS)
- Log access appropriately
- Consider data retention policies
- Consult with legal/compliance team

## Contributing

This is a class project, but contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Academic Context

**Course:** Agentic AI Class  
**Objective:** Build an AI agent that autonomously manages tasks  
**Challenge:** Work with platforms that lack APIs  
**Solution:** Browser automation + LLM decision-making  

This project demonstrates:
- Real-world problem solving
- Integration of multiple technologies
- Agentic behavior (autonomous goal achievement)
- Practical AI applications

## License

MIT License - See LICENSE file for details

## Acknowledgments

- **Course Instructor:** [Name]
- **Client:** Independent Therapist Practice
- **Technologies:** Ollama, Playwright, Google Calendar API
- **Inspiration:** Making therapists' lives easier!

## Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [Ollama Documentation](https://ollama.ai/docs)
- [Google Calendar API](https://developers.google.com/calendar)
- [Function Calling with LLMs](https://docs.ollama.ai/api#function-calling)

---

Made with ❤️ for therapists who deserve better tools

**Star ⭐ this repo if it helped you!**