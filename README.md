# Calendar Sync AI Agent 🤖📅

An AI-powered chatbot that helps therapists sync their Outlook, Google, and TherapyAppointment calendars.

## 🎯 Project Overview

An intelligent calendar management agent built with **LangChain** that helps therapists coordinate their Outlook, Google, and TherapyAppointment calendars. Features **Human-in-the-Loop (HITL)** approval for sensitive operations.

Key Technologies:
- **LangChain** - Agent orchestration and tool management
- **Ollama/Llama 3.1** - Local LLM for decision-making
- **Playwright** - Browser automation for TherapyAppointment (no API available)
- **Human-in-the-Loop** - Manual approval before syncing to TherapyAppointment
- **Multi-calendar integration** - Google Calendar API, Microsoft Graph API

## Features

- 💬 **Natural Language Interface** - Chat with the AI using plain English
- 🔄 **Multi-Calendar Syncing** - Outlook → Google → TherapyAppointment
- ✅ **Human-in-the-Loop** - Approve which events to sync before automation runs
- 🤖 **LangChain Agent** - Intelligent tool selection and orchestration
- 🌐 **Browser Automation** - Playwright controls TherapyAppointment web interface
- 📊 **Event Viewing** - View events from any connected calendar
- 🧠 **Local LLM** - Runs entirely on your machine with Ollama

## How It Works

### Agent Architecture
This project uses **LangChain's agent framework** with custom tools:

1. **Tools Available to Agent:**
   - `get_google_events` - Retrieve Google Calendar events
   - `get_outlook_events` - Retrieve Outlook Calendar events
   - `sync_outlook_to_google` - One-way sync with duplicate detection
   - `request_sync_approval` - Show events and request user approval

2. **Human-in-the-Loop Workflow:**
```
   User: "Sync my calendars to TherapyAppointment"
   ↓
   Agent calls request_sync_approval tool
   ↓
   Shows numbered list of events
   ↓
   User responds: "1,3,5" or "all"
   ↓
   Agent syncs only approved events
```

3. **Browser Automation:**
   - Playwright logs into TherapyAppointment
   - Navigates to availability settings
   - Blocks selected time slots
   - All controlled programmatically

## Quick Start

### Prerequisites
- Python 3.8+
- Ollama installed with **llama3.1** model (or llama3.2)
- TherapyAppointment account
- Google Calendar with API access
- Microsoft 365/Outlook Calendar

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
ollama pull llama3.1  # Recommended for LangChain agents
# OR for smaller memory footprint:
ollama pull llama3.2:3b
```

4. **Configure credentials**

Create a `.env` file:

Edit `.env` with your credentials:
```
THERAPY_APPOINTMENT_EMAIL=your_email@example.com
THERAPY_APPOINTMENT_PASSWORD=your_password
THERAPY_APPOINTMENT_URL=https://www.therapyappointment.com

OUTLOOK_CLIENT_ID=your_client_id
OUTLOOK_TENANT_ID=common  
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

### Publish App so your credentials last longer than 7 days

1. Go to "API & Services" and then select "OAuth Consent Screen" from the left menu
2. Click "Audience" in the new tab that appears on the left
3. Near the top of the page under "Publishing Status" click the button to publish your app

# Azure AD App Registration

To access Outlook Calendar, you need to register an application in Azure Active Directory.

---

## **Step 1: Register Application**

1. Go to **Azure Portal**
2. Navigate to **Azure Active Directory → App registrations**
3. Click **New registration**
4. Fill in:
   - **Name:** "Calendar Sync Agent" (or any name you prefer)
   - **Supported account types:** "Accounts in any organizational directory and personal Microsoft accounts"
   - **Redirect URI:** Leave blank for now
5. Click **Register**

---

## **Step 2: Get Application IDs**

After registration, you'll see the application overview:

- Copy the **Application (client) ID**

Save this — you'll need them for your `.env` file.

---

## **Step 3: Create Client Secret**

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description (e.g., "Calendar Sync Secret")
4. Choose an expiration period (recommend **24 months**)
5. Click **Add**
6. **IMPORTANT:** Copy the **secret VALUE** immediately (it won't be shown again!)

---

## **Step 4: Configure API Permissions**

1. Go to **API permissions** in your app registration
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Add these permissions:
   - `Calendars.Read`
   - `Calendars.ReadWrite` (if you want to create events in Outlook too)
   - `User.Read`
6. Click **Add permissions**
7. Click **Grant admin consent** (if you have admin rights) or ask your admin

---

## **Step 5: Enable Device Code Flow**

1. Go to **Authentication** in your app registration
2. Under **Advanced settings → Allow public client flows**
3. Set **Enable the following mobile and desktop flows** to **Yes**
4. Click **Save**

---

## **Step 6: Update .env**

1. Add the following to your .env file
```
# Outlook/Microsoft 365 Configuration
OUTLOOK_CLIENT_ID=your_client_id
OUTLOOK_CLIENT_SECRET=your_client_secret
OUTLOOK_TENANT_ID=common
```

## Usage

Run the Streamlit web app:
```bash
streamlit run streamlit_app.py
```

This will automatically open your browser to http://localhost:8501 with a modern chat interface.

- Type naturally: "Sync my calendar for the next week"
- Use quick action buttons in the sidebar
- See real-time progress as events are synced

## Project Structure

```
calendarassistant/
├── calendar_agent.py          # Main agent with Playwright automation
├── streamlit_app.py          # Web UI interface
├── requirements.txt           # Python dependencies
├── .env                       # Your credentials (create this)
├── credentials.json          # Google OAuth (download this)
├── token.pickle              # Generated after first auth
├── .gitignore
└── README.md
```

## Key Features Explained

### 1. LangChain Agent with HITL
The agent uses **LangChain's ReAct pattern**:
- Thinks step-by-step about what tools to use
- Follows explicit rules (only do what user asks)
- Supports **Human-in-the-Loop** for sensitive operations
- Manual state tracking for approval workflows

**Example interaction:**
```
User: "Sync outlook to google, then google to therapy"

Agent reasoning:
1. Calls sync_outlook_to_google tool
2. Calls request_sync_approval tool
3. STOPS and waits for human input
4. User selects events
5. Python directly syncs (bypasses agent for safety)
```

### 2. Browser Automation (No API Needed)
Since TherapyAppointment lacks a public API, Playwright:
- Controls a real Chromium browser
- Logs in and navigates the web interface
- Fills forms to block availability
- Handles dynamic JavaScript content

### 3. Smart Multi-Calendar Syncing
- **Outlook → Google:** Automatic with duplicate detection
- **Google → TherapyAppointment:** With human approval
- Only syncs time-based events (skips all-day)
- Customizable sync window (default: 7 days)

### Environment Variables

```bash
# Required
THERAPY_APPOINTMENT_EMAIL=your_email@example.com
THERAPY_APPOINTMENT_PASSWORD=your_password
THERAPY_APPOINTMENT_URL=https://www.therapyappointment.com
OUTLOOK_CLIENT_ID=your_client_id
OUTLOOK_TENANT_ID=common  
```

### Model Selection
The default model is **llama3.1** which is optimized for agent workflows and function calling.

Available in `CalendarSyncAgentWithHITL.__init__()`:
```python
def __init__(self, model_name: str = "llama3.1"):
```

**Recommended models:**
- `llama3.1` - Best for agents, 4.7GB RAM
- `llama3.1:8b` - Same as above (alias)
- `llama3.2:3b` - Lighter weight, 2GB RAM, slightly less capable

## Troubleshooting

### Ollama Issues

**"Connection refused"**
```bash
# Make sure Ollama is running
ollama serve
```

**"Model not found"**
```bash
ollama pull llama3.2:3b
```

### Google Calendar Issues

**"credentials.json not found"**
- Download OAuth credentials from Google Cloud Console
- Place in project root directory

**"Permission denied"**
- Delete `token.pickle` and re-authenticate
- Make sure Calendar API is enabled in Google Cloud

### Running in Debug Mode

```bash
# Playwright inspector mode
PWDEBUG=1 python calendar_agent.py

# Slow motion (see each action)
# Edit code: slow_mo=1000 in browser.launch()
```

### LangChain/Agent Issues

**Agent doing too much or too little**
- Check the system prompt in `_create_agent()` 
- Adjust `max_iterations` (default: 3)
- Review agent's verbose output for reasoning

**HITL not working**
- Check `hitl.is_awaiting_approval()` state
- Verify Streamlit detects approval request (looks for 📋 emoji)
- Clear Streamlit cache: `st.cache_resource.clear()`

**"Pydantic validation error"**
- Ensure using `Tool` not `StructuredTool`
- Don't use `args_schema` with `initialize_agent`

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

### Dependencies
Key packages (see requirements.txt for complete list):

**LangChain Stack:**
- `langchain` - Agent framework
- `langchain-community` - Community integrations (ChatOllama)

**Calendar APIs:**
- `google-auth-oauthlib`, `google-api-python-client`
- `msal` (Microsoft Authentication Library)

**Automation:**
- `playwright` - Browser automation
- `ollama` - Local LLM interface

**Web Interface:**
- `streamlit` - Web UI
- `nest-asyncio` - Async support in Streamlit

**Utilities:**
- `python-dotenv`, `requests`

## Resources

- [LangChain Documentation](https://python.langchain.com/)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Ollama Documentation](https://ollama.ai/docs)
- [Google Calendar API](https://developers.google.com/calendar)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/api/resources/calendar)

---