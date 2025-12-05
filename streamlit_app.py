"""
Streamlit Web Interface for LangChain Calendar Sync Agent with HITL
Run: streamlit run streamlit_app.py
"""

import streamlit as st
import asyncio
import sys
from calendar_agent import CalendarSyncAgentWithHITL
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
    
    .hitl-box {
        background-color: #fef3c7;
        border: 2px solid #f59e0b;
        border-radius: 0.5rem;
        padding: 1rem;
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
    status = {
        'outlook': bool(os.getenv('OUTLOOK_CLIENT_ID')),
        'google': os.path.exists('credentials.json'),
        'therapy': bool(os.getenv('THERAPY_APPOINTMENT_EMAIL') and os.getenv('THERAPY_APPOINTMENT_PASSWORD'))
    }
    return status


def initialize_agent():
    """Initialize the agent with error handling"""
    try:
        return CalendarSyncAgentWithHITL()
    except FileNotFoundError as e:
        st.error(f"⚠️ Configuration Error: {str(e)}")
        return None
    except ValueError as e:
        st.warning(f"⚠️ Partial Configuration: {str(e)}")
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

if "awaiting_selection" not in st.session_state:
    st.session_state.awaiting_selection = False


# Header with calendar badges
st.title("📅 Multi-Calendar Sync AI Agent")
st.caption("🤖 Powered by LangChain with Human-in-the-Loop")

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

# Welcome message
if st.session_state.show_welcome and not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("""
        👋 Hi! I'm your **LangChain-powered** Calendar Sync AI Agent with **Human-in-the-Loop**.
        
        **🎯 Key Feature: You stay in control!**
        
        When syncing to TherapyAppointment, I'll:
        1. Show you a numbered list of all events
        2. Ask which ones you want to block
        3. Only sync what you approve ✅
        
        ### Quick Commands:
        - "Show my Outlook calendar"
        - "Sync Outlook to Google"
        - **"Sync Google to TherapyAppointment"** ← Uses HITL!
        - "Show all my calendars"
        
        ### How HITL Works:
        When you ask to sync to TherapyAppointment, I'll show you:
        ```
        1. Team Meeting - Dec 5 at 2:30 PM
        2. Client Session - Dec 6 at 10:00 AM
        3. Lunch Break - Dec 6 at 12:00 PM
        ```
        Then you respond: `1,2` or `all` or `none`
        """)

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Highlight HITL approval requests
        if message["role"] == "assistant" and "Which events would you like me to block" in message["content"]:
            st.session_state.awaiting_selection = True

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
                        
                        # Check if this is an approval request
                        if "Which events would you like me to block" in response:
                            st.session_state.awaiting_selection = True
                        elif st.session_state.awaiting_selection:
                            # User just responded to selection
                            st.session_state.awaiting_selection = False
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
    
    # Show HITL status
    if st.session_state.awaiting_selection:
        st.markdown("""
        <div class="hitl-box">
            <strong>⏳ Awaiting Your Selection</strong><br/>
            Type event numbers or 'all' in the chat
        </div>
        """, unsafe_allow_html=True)
    
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
        if st.button("→ Therapy", key="google_to_therapy", use_container_width=True, 
                    disabled=not (config_status['google'] and config_status['therapy']) or st.session_state.awaiting_selection):
            prompt = "Sync my Google Calendar to TherapyAppointment"
            st.session_state.messages.append({"role": "user", "content": prompt})
            try:
                response = run_async(st.session_state.agent.chat(prompt))
                if response:
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    if "Which events would you like me to block" in response:
                        st.session_state.awaiting_selection = True
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
            st.rerun()
    
    st.divider()
    
    # Clear chat
    if st.button("🔄 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent = initialize_agent()
        st.session_state.show_welcome = True
        st.session_state.awaiting_selection = False
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
    with st.expander("💡 HITL Examples"):
        st.markdown("""
        **Scenario: Sync with approval**
        
        You: "Sync Google to TherapyAppointment"
        
        Agent shows:
        ```
        1. Team Meeting - Dec 5 at 2:30 PM
        2. Client Session - Dec 6 at 10:00 AM  
        3. Personal Errand - Dec 6 at 3:00 PM
        ```
        
        **Your options:**
        - `1,2` - Only sync events 1 and 2
        - `all` - Sync all events
        - `none` - Cancel sync
        - `1,2,3` - Sync specific events
        """)
    
    with st.expander("🧠 About LangChain"):
        st.markdown("""
        **This agent uses:**
        
        ✅ **LangChain Framework**
        - `ChatOllama` - Local LLM (Llama 3.1)
        - `AgentExecutor` - Tool orchestration
        - `StructuredTool` - Type-safe tools
        - No external memory needed (Streamlit handles chat history)
        
        ✅ **Human-in-the-Loop**
        - Custom middleware
        - Approval workflow
        - User control over syncing
        
        ✅ **Multi-Calendar Integration**
        - Google Calendar API
        - Microsoft Graph API
        - Playwright automation
        """)
    
    with st.expander("📖 Why LangChain over CrewAI?"):
        st.markdown("""
        **LangChain** was chosen because:
        
        1. **Single-agent pattern** - One intelligent agent with multiple tools
        2. **Tool orchestration** - Perfect for API integrations
        3. **Memory management** - Built-in conversation history
        4. **HITL support** - Easy to implement approval workflows
        
        **CrewAI** would be overkill:
        - Designed for multi-agent collaboration
        - More complex for simple tool-calling
        - Not needed for sequential workflows
        """)
    
    st.divider()
    st.caption("💬 Built with LangChain, Ollama & Playwright")
    st.caption("🔒 All data stays local and secure")
    st.caption("✅ Human-in-the-Loop for safety")