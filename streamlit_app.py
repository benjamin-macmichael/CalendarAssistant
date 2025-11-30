"""
Streamlit Web Interface for Multi-Calendar Sync AI Agent
Run: streamlit run streamlit_app.py
"""

import streamlit as st
import asyncio
import sys
from calendar_agent import CalendarSyncAgent
import os

# Ensure proper event loop policy for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Page config
st.set_page_config(
    page_title="Multi-Calendar Sync AI Agent",
    page_icon="📅",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Hide the deploy button */
    [data-testid="stToolbar"] {
        display: none;
    }
            
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    
    .stChatInputContainer {
        padding: 0.5rem 0;
    }
    
    .calendar-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        margin: 0.25rem;
    }
    
    .badge-outlook {
        background-color: #0078d4;
        color: white;
    }
    
    .badge-google {
        background-color: #4285f4;
        color: white;
    }
    
    .badge-therapy {
        background-color: #10b981;
        color: white;
    }
    
    .sync-flow {
        padding: 1rem;
        background: linear-gradient(90deg, #0078d4 0%, #4285f4 50%, #10b981 100%);
        border-radius: 0.5rem;
        color: white;
        text-align: center;
        font-weight: 600;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def run_async(coro):
    """Run async coroutine in a way that works with Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            st.error("Please install nest_asyncio: pip install nest-asyncio")
            return None
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)


def check_environment():
    """Check if required environment variables are set"""
    configs = {
        'outlook': {
            'vars': ['OUTLOOK_CLIENT_ID'],
            'name': 'Outlook Calendar'
        },
        'google': {
            'vars': ['credentials.json'],  # File check
            'name': 'Google Calendar'
        },
        'therapy': {
            'vars': ['THERAPY_APPOINTMENT_EMAIL', 'THERAPY_APPOINTMENT_PASSWORD'],
            'name': 'TherapyAppointment'
        }
    }
    
    status = {}
    
    # Check Outlook
    outlook_configured = all(os.getenv(var) for var in configs['outlook']['vars'])
    status['outlook'] = outlook_configured
    
    # Check Google
    google_configured = os.path.exists('credentials.json')
    status['google'] = google_configured
    
    # Check TherapyAppointment
    therapy_configured = all(os.getenv(var) for var in configs['therapy']['vars'])
    status['therapy'] = therapy_configured
    
    return status


def initialize_agent():
    """Initialize the agent with error handling"""
    try:
        return CalendarSyncAgent()
    except FileNotFoundError as e:
        st.error(f"⚠️ Configuration Error: {str(e)}")
        return None
    except ValueError as e:
        st.warning(f"⚠️ Partial Configuration: {str(e)}")
        st.info("💡 Some features may be limited. Check sidebar for details.")
        # Try to create agent anyway for basic functionality
        try:
            return CalendarSyncAgent()
        except:
            return None
    except Exception as e:
        st.error(f"⚠️ Error initializing agent: {str(e)}")
        return None


# Initialize session state
if "agent" not in st.session_state:
    st.session_state.agent = initialize_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True


# Header with calendar badges
st.title("📅 Multi-Calendar Sync AI Agent")
st.markdown("""
<div style="text-align: center; margin: 1rem 0;">
    <span class="calendar-badge badge-outlook">📧 Outlook</span>
    <span style="font-size: 1.5rem;">→</span>
    <span class="calendar-badge badge-google">📅 Google</span>
    <span style="font-size: 1.5rem;">→</span>
    <span class="calendar-badge badge-therapy">🗓️ TherapyAppointment</span>
</div>
""", unsafe_allow_html=True)

# Check configuration status
config_status = check_environment()
all_configured = all(config_status.values())

if not all_configured:
    missing = [k for k, v in config_status.items() if not v]
    st.warning(f"⚠️ Incomplete setup: {', '.join(missing).title()} not configured")
    with st.expander("📖 Setup Instructions", expanded=False):
        st.markdown("""
        ### Outlook Calendar Setup
        1. Register app in Azure Portal
        2. Add `OUTLOOK_CLIENT_ID` and `OUTLOOK_CLIENT_SECRET` to `.env`
        3. See setup guide for detailed instructions
        
        ### Google Calendar Setup
        1. Download `credentials.json` from Google Cloud Console
        2. Place in project root directory
        
        ### TherapyAppointment Setup
        1. Add `THERAPY_APPOINTMENT_EMAIL` and `THERAPY_APPOINTMENT_PASSWORD` to `.env`
        """)

# Welcome message
if st.session_state.show_welcome and not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("""
        👋 Hi! I'm your Multi-Calendar Sync AI Agent. I can help you:
        
        **📧 Outlook Calendar**
        - View Outlook events
        - Export to other calendars
        
        **📅 Google Calendar**
        - View Google events
        - Import from Outlook
        - Sync to TherapyAppointment
        
        **🗓️ TherapyAppointment**
        - Block busy times automatically
        - Prevent double-bookings
        
        ### Quick Commands:
        - "Show my Outlook calendar"
        - "Sync Outlook to Google"
        - "Sync everything to TherapyAppointment"
        - "What's on all my calendars?"
        """)

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Message Calendar Sync Agent..."):
    if not st.session_state.agent:
        st.error("⚠️ Agent not initialized. Please check your configuration.")
    else:
        st.session_state.show_welcome = False
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Processing..."):
                try:
                    response = run_async(st.session_state.agent.chat(prompt))
                    if response:
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        error_msg = "Unable to process request."
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Sidebar
with st.sidebar:
    st.header("🎛️ Quick Actions")
    
    # Outlook actions
    st.subheader("📧 Outlook")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("View Events", key="outlook_view", use_container_width=True, disabled=not config_status['outlook']):
            prompt = "Show me my Outlook calendar events"
            st.session_state.messages.append({"role": "user", "content": prompt})
            try:
                response = run_async(st.session_state.agent.chat(prompt))
                if response:
                    st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
            st.rerun()
    
    with col2:
        if st.button("→ Google", key="outlook_to_google", use_container_width=True, disabled=not (config_status['outlook'] and config_status['google'])):
            prompt = "Sync my Outlook calendar to Google Calendar"
            st.session_state.messages.append({"role": "user", "content": prompt})
            try:
                response = run_async(st.session_state.agent.chat(prompt))
                if response:
                    st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
            st.rerun()
    
    # Google actions
    st.subheader("📅 Google")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("View Events", key="google_view", use_container_width=True, disabled=not config_status['google']):
            prompt = "What events do I have on my Google Calendar?"
            st.session_state.messages.append({"role": "user", "content": prompt})
            try:
                response = run_async(st.session_state.agent.chat(prompt))
                if response:
                    st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
            st.rerun()
    
    with col2:
        if st.button("→ Therapy", key="google_to_therapy", use_container_width=True, disabled=not (config_status['google'] and config_status['therapy'])):
            prompt = "Sync my Google Calendar to TherapyAppointment"
            st.session_state.messages.append({"role": "user", "content": prompt})
            try:
                response = run_async(st.session_state.agent.chat(prompt))
                if response:
                    st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
            st.rerun()
    
    # Full sync
    st.subheader("🔄 Full Sync")
    if st.button("📧→📅→🗓️ Sync All", type="primary", use_container_width=True, disabled=not all_configured):
        prompt = "Sync Outlook to Google, then sync Google to TherapyAppointment"
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            response = run_async(st.session_state.agent.chat(prompt))
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
        st.rerun()
    
    st.divider()
    
    # Clear chat
    if st.button("🔄 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent = initialize_agent()
        st.session_state.show_welcome = True
        st.rerun()
    
    st.divider()
    
    # Configuration status
    st.header("⚙️ Configuration")
    
    status_emoji = {True: "✅", False: "❌"}
    
    st.text(f"{status_emoji[config_status['outlook']]} Outlook Calendar")
    st.text(f"{status_emoji[config_status['google']]} Google Calendar")
    st.text(f"{status_emoji[config_status['therapy']]} TherapyAppointment")
    
    if os.path.exists('token.pickle'):
        st.text("✅ Google authenticated")
    
    if os.path.exists('outlook_token_cache.json'):
        st.text("✅ Outlook authenticated")
    
    st.divider()
    
    # Help section
    with st.expander("💡 Example Commands"):
        st.markdown("""
        **View Events:**
        - "What's on my Outlook calendar?"
        - "Show Google calendar for next 3 days"
        - "What do I have scheduled?"
        
        **Sync Calendars:**
        - "Sync Outlook to Google"
        - "Copy my Outlook events to Google"
        - "Sync Google to TherapyAppointment"
        
        **Full Workflow:**
        - "Sync everything"
        - "Update all my calendars"
        - "Do a full calendar sync"
        
        **General Chat:**
        - "How does the syncing work?"
        - "What calendars do you support?"
        - "Help me understand the sync flow"
        """)
    
    with st.expander("📖 Setup Guide"):
        st.markdown("""
        **Outlook Setup:**
        1. Register app in Azure Portal
        2. Get Client ID and Secret
        3. Add to `.env` file
        
        **Google Setup:**
        1. Create project in Google Cloud Console
        2. Enable Calendar API
        3. Download `credentials.json`
        
        **TherapyAppointment:**
        1. Add credentials to `.env`
        
        See documentation for detailed steps.
        """)
    
    st.divider()
    st.caption("💬 Built with Streamlit, Ollama & Microsoft Graph")
    st.caption("🔒 All data stays local and secure")