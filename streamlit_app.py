"""
Streamlit Web Interface for Calendar Sync AI Agent
Run: streamlit run streamlit_app.py
"""

import streamlit as st
import asyncio
import sys
from calendar_agent import CalendarSyncAgent

# Ensure proper event loop policy for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Page config
st.set_page_config(
    page_title="Calendar Sync AI Agent",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS for ChatGPT-like styling
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .stChatInputContainer {
        padding: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to run async code properly
def run_async(coro):
    """Run async coroutine in a way that works with Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # If loop is already running (in Streamlit), use nest_asyncio
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)

# Initialize session state
if "agent" not in st.session_state:
    st.session_state.agent = CalendarSyncAgent()
if "messages" not in st.session_state:
    st.session_state.messages = []

# Header
st.title("🤖 Calendar Sync AI Agent")
st.caption("Sync your Google Calendar with TherapyAppointment")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Message Calendar Sync Agent..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = run_async(st.session_state.agent.chat(prompt))
                st.markdown(response)
                # Add assistant response to chat
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Sidebar with suggestions
with st.sidebar:
    st.header("Quick Actions")
    
    if st.button("📅 Sync Calendar"):
        prompt = "Sync my calendar for the next week"
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            response = run_async(st.session_state.agent.chat(prompt))
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
        st.rerun()
    
    if st.button("📋 View Events"):
        prompt = "What events do I have coming up?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            response = run_async(st.session_state.agent.chat(prompt))
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
        st.rerun()
    
    if st.button("🔄 Clear Chat"):
        st.session_state.messages = []
        st.session_state.agent = CalendarSyncAgent()
        st.rerun()
    
    st.divider()
    st.caption("💡 Tip: The agent will automatically detect when to sync calendars or just chat with you!")