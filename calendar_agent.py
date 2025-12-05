"""
Calendar Sync AI Agent with LangChain and Human-in-the-Loop
Uses LangChain for agent orchestration and HITL for confirmation before syncing
"""

import json
import os
from datetime import datetime, timedelta
import datetime as dt
from typing import List, Dict, Optional, Any
import asyncio

# LangChain imports
from langchain_community.chat_models import ChatOllama
from langchain.agents import AgentExecutor
from langchain.tools import Tool

# Existing imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from playwright.async_api import async_playwright, Browser, Page
import msal
import requests

from dotenv import load_dotenv
load_dotenv()


# ============================================================================
# HUMAN-IN-THE-LOOP MIDDLEWARE
# ============================================================================

class HumanApprovalMiddleware:
    """Middleware for human approval before executing sensitive operations"""
    
    def __init__(self):
        self.pending_events = []
        self.awaiting_approval = False
    
    def request_approval(self, events: List[Dict]) -> str:
        """Store events and request human approval"""
        self.pending_events = events
        self.awaiting_approval = True
        
        # Format events as numbered list
        message = "📋 **Events to sync from Google Calendar:**\n\n"
        for i, event in enumerate(events, 1):
            start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
            message += f"{i}. **{event['summary']}**\n"
            message += f"   📅 {start_dt.strftime('%B %d, %Y at %I:%M %p')} - {end_dt.strftime('%I:%M %p')}\n\n"
        
        message += "\n🤔 **Which events would you like me to block on TherapyAppointment?**\n"
        message += "   • Type specific numbers (e.g., '1,3,5')\n"
        message += "   • Type 'all' to block all events\n"
        message += "   • Type 'none' or 'cancel' to skip syncing"
        
        return message
    
    def get_selected_events(self, selection: str) -> List[Dict]:
        """Parse user selection and return selected events"""
        selection = selection.lower().strip()
        
        if selection in ['none', 'cancel', 'skip']:
            self.awaiting_approval = False
            return []
        
        if selection == 'all':
            selected = self.pending_events
        else:
            # Parse comma-separated numbers
            try:
                numbers = [int(n.strip()) for n in selection.split(',')]
                selected = [
                    self.pending_events[n-1] 
                    for n in numbers 
                    if 1 <= n <= len(self.pending_events)
                ]
            except (ValueError, IndexError):
                return []
        
        self.awaiting_approval = False
        return selected
    
    def is_awaiting_approval(self) -> bool:
        return self.awaiting_approval


# ============================================================================
# CALENDAR SERVICES
# ============================================================================

class GoogleCalendarService:
    """Handles Google Calendar API interactions"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError("credentials.json not found!")
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('calendar', 'v3', credentials=creds)
    
    def get_events(self, days_ahead: int = 7) -> List[Dict]:
        if not self.service:
            return []
        
        now = dt.datetime.now(dt.timezone.utc)
        end_time = now + timedelta(days=days_ahead)
        
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        formatted_events = []
        
        for event in events:
            if 'dateTime' not in event['start']:
                continue
            formatted_events.append({
                'summary': event.get('summary', 'No Title'),
                'start': event['start'].get('dateTime'),
                'end': event['end'].get('dateTime'),
                'id': event['id']
            })
        
        return formatted_events
    
    def add_event(self, summary: str, start_time: str, end_time: str, description: str = "") -> bool:
        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {'dateTime': start_time, 'timeZone': 'UTC'},
                'end': {'dateTime': end_time, 'timeZone': 'UTC'},
            }
            self.service.events().insert(calendarId='primary', body=event).execute()
            return True
        except Exception as e:
            print(f"✗ Failed to create event: {e}")
            return False


class OutlookCalendarService:
    """Handles Outlook Calendar API interactions"""
    
    def __init__(self):
        self.client_id = os.getenv('OUTLOOK_CLIENT_ID')
        self.tenant_id = os.getenv('OUTLOOK_TENANT_ID', 'common')
        
        if not self.client_id:
            raise ValueError("OUTLOOK_CLIENT_ID not set in .env")
        
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scopes = ['Calendars.Read', 'Calendars.ReadWrite', 'User.Read']
        self.app = msal.PublicClientApplication(self.client_id, authority=self.authority)
        self.token = self._get_token()
    
    def _get_token(self):
        token_cache_file = 'outlook_token_cache.json'
        if os.path.exists(token_cache_file):
            with open(token_cache_file, 'r') as f:
                cache_data = json.load(f)
                if cache_data.get('access_token'):
                    return cache_data['access_token']
        
        flow = self.app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flow:
            raise ValueError("Failed to create device flow")
        
        print("\n" + "="*60)
        print("🔐 OUTLOOK AUTHENTICATION REQUIRED")
        print("="*60)
        print(flow["message"])
        print("="*60 + "\n")
        
        result = self.app.acquire_token_by_device_flow(flow)
        if "access_token" in result:
            with open(token_cache_file, 'w') as f:
                json.dump(result, f)
            return result['access_token']
        else:
            raise ValueError(f"Failed to authenticate: {result.get('error_description')}")
    
    def get_events(self, days_ahead: int = 7) -> List[Dict]:
        now = datetime.now(dt.timezone.utc)
        end_time = now + timedelta(days=days_ahead)
        
        endpoint = "https://graph.microsoft.com/v1.0/me/calendar/events"
        params = {
            '$select': 'subject,start,end,body',
            '$filter': f"start/dateTime ge '{now.isoformat()}' and start/dateTime lt '{end_time.isoformat()}'",
            '$orderby': 'start/dateTime',
            '$top': 100
        }
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            events = response.json().get('value', [])
            
            formatted_events = []
            for event in events:
                start_dt = datetime.fromisoformat(event['start']['dateTime'])
                end_dt = datetime.fromisoformat(event['end']['dateTime'])
                
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=dt.timezone.utc)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=dt.timezone.utc)
                
                formatted_events.append({
                    'subject': event.get('subject', 'No Title'),
                    'start': start_dt.isoformat(),
                    'end': end_dt.isoformat(),
                    'body': event.get('body', {}).get('content', '')
                })
            
            return formatted_events
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                if os.path.exists('outlook_token_cache.json'):
                    os.remove('outlook_token_cache.json')
                self.token = self._get_token()
                return self.get_events(days_ahead)
            raise


class TherapyAppointmentAutomation:
    """Handles TherapyAppointment browser automation"""
    
    def __init__(self):
        self.email = os.getenv('THERAPY_APPOINTMENT_EMAIL')
        self.password = os.getenv('THERAPY_APPOINTMENT_PASSWORD')
        self.url = os.getenv('THERAPY_APPOINTMENT_URL', 'https://www.therapyappointment.com')
        
        if not self.email or not self.password:
            raise ValueError("TherapyAppointment credentials not set in .env")
    
    async def block_multiple_times(self, events: List[Dict]) -> int:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=500)
            context = await browser.new_context(viewport={'width': 1280, 'height': 720})
            page = await context.new_page()
            
            try:
                print("🔐 Logging in...")
                await self._login(page)
                print("📅 Navigating to calendar...")
                await self._navigate_to_availability(page)
                
                blocked_count = 0
                for i, event in enumerate(events, 1):
                    try:
                        print(f"\n⏰ [{i}/{len(events)}] Blocking: {event['summary']}")
                        if await self._block_time_slot(page, event):
                            blocked_count += 1
                            print(f"   ✓ Blocked successfully")
                        await self._navigate_to_availability(page)
                    except Exception as e:
                        print(f"   ✗ Error: {e}")
                        continue
                
                print(f"\n✅ Blocked {blocked_count}/{len(events)} events")
                await asyncio.sleep(2)
                return blocked_count
            finally:
                await browser.close()
    
    async def _login(self, page: Page):
        await page.goto(f"{self.url}/login", wait_until='networkidle')
        await page.fill('#user_username', self.email)
        await page.fill('#user_password', self.password)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state('networkidle')
    
    async def _navigate_to_availability(self, page: Page):
        await asyncio.sleep(1)
        await page.goto('https://api.portal.therapyappointment.com/n/schedule',
                       wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_load_state('networkidle')
    
    async def _block_time_slot(self, page: Page, event: Dict) -> bool:
        start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
        
        try:
            await page.click('text=Edit Availability')
            await asyncio.sleep(2)
            try:
                await page.get_by_role("button", name="Close dialog").click(timeout=2000)
            except:
                pass
            
            await page.click('button:has-text("Out Of Office")')
            await asyncio.sleep(2)
            await page.click('button:has-text("Let\'s do that")')
            await asyncio.sleep(2)
            
            await page.click('#event_date')
            await asyncio.sleep(1)
            await self._navigate_calendar(page, start_dt)
            
            day_selector = f'td.day:not(.old):not(.new):has-text("{start_dt.day}")'
            await page.click(day_selector)
            await asyncio.sleep(1)
            
            await page.fill('#event_starttime', start_dt.strftime('%H:%M'))
            await asyncio.sleep(0.5)
            await page.fill('#event_endtime', end_dt.strftime('%H:%M'))
            await asyncio.sleep(0.5)
            await page.fill('#calendar_event_name', 'Unavailable')
            await asyncio.sleep(0.5)
            
            await page.click('button[type="submit"].btn-action')
            await asyncio.sleep(3)
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    async def _navigate_calendar(self, page: Page, target_date: datetime):
        target_month, target_year = target_date.month, target_date.year
        for _ in range(24):
            try:
                combined = await page.text_content('th.datepicker-switch')
                parts = combined.split()
                month_name, current_year = parts[0], int(parts[1])
                current_month = datetime.strptime(month_name, '%B').month
                
                if current_year == target_year and current_month == target_month:
                    break
                elif (current_year < target_year) or (current_year == target_year and current_month < target_month):
                    await page.click('th.next')
                else:
                    await page.click('th.prev')
                await asyncio.sleep(0.5)
            except:
                break


# ============================================================================
# LANGCHAIN AGENT WITH HITL
# ============================================================================

class CalendarSyncAgentWithHITL:
    """LangChain-based agent with Human-in-the-Loop for calendar syncing"""
    
    def __init__(self, model_name: str = "llama3.1"):
        # Initialize services
        self.google_calendar = GoogleCalendarService()
        self.outlook_calendar = OutlookCalendarService()
        self.therapy_automation = None
        
        # Initialize HITL middleware
        self.hitl = HumanApprovalMiddleware()
        
        # Initialize LangChain LLM
        self.llm = ChatOllama(model=model_name, temperature=0)
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create agent
        self.agent = self._create_agent()
    
    def _create_tools(self) -> List:
        """Create LangChain tools for the agent"""
        
        def get_google_events(query: str = "") -> str:
            """Get upcoming events from Google Calendar"""
            try:
                events = self.google_calendar.get_events(7)
                if not events:
                    return "No events found on Google Calendar"
                
                result = f"Found {len(events)} events on Google Calendar:\n\n"
                for i, event in enumerate(events, 1):
                    start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
                    result += f"{i}. {event['summary']}\n"
                    result += f"   {start_dt.strftime('%B %d at %I:%M %p')} - {end_dt.strftime('%I:%M %p')}\n\n"
                return result
            except Exception as e:
                return f"Error getting Google events: {str(e)}"
        
        def get_outlook_events(query: str = "") -> str:
            """Get upcoming events from Outlook Calendar"""
            try:
                events = self.outlook_calendar.get_events(7)
                if not events:
                    return "No events found on Outlook Calendar"
                
                result = f"Found {len(events)} events on Outlook Calendar:\n\n"
                for i, event in enumerate(events, 1):
                    start_dt = datetime.fromisoformat(event['start'])
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=dt.timezone.utc)
                    local_start = start_dt.astimezone()
                    
                    end_dt = datetime.fromisoformat(event['end'])
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=dt.timezone.utc)
                    local_end = end_dt.astimezone()
                    
                    result += f"{i}. {event['subject']}\n"
                    result += f"   {local_start.strftime('%B %d at %I:%M %p')} - {local_end.strftime('%I:%M %p')}\n\n"
                return result
            except Exception as e:
                return f"Error getting Outlook events: {str(e)}"
        
        def request_sync_approval(query: str = "") -> str:
            """Request human approval for syncing Google Calendar events to TherapyAppointment"""
            try:
                events = self.google_calendar.get_events(7)
                if not events:
                    return "No events found to sync"
                
                return self.hitl.request_approval(events)
            except Exception as e:
                return f"Error requesting approval: {str(e)}"
        
        def sync_outlook_to_google(query: str = "") -> str:
            """Sync events from Outlook to Google Calendar"""
            try:
                outlook_events = self.outlook_calendar.get_events(7)
                if not outlook_events:
                    return "No Outlook events to sync"
                
                google_events = self.google_calendar.get_events(7)
                google_sigs = set()
                for ge in google_events:
                    start_dt = datetime.fromisoformat(ge['start'].replace('Z', '+00:00'))
                    google_sigs.add(f"{ge['summary']}_{start_dt.strftime('%Y%m%d%H%M')}")
                
                added, skipped = 0, 0
                for oe in outlook_events:
                    start_dt = datetime.fromisoformat(oe['start'])
                    sig = f"{oe['subject']}_{start_dt.strftime('%Y%m%d%H%M')}"
                    
                    if sig in google_sigs:
                        skipped += 1
                        continue
                    
                    if self.google_calendar.add_event(
                        oe['subject'], oe['start'], oe['end'],
                        f"Synced from Outlook\n\n{oe.get('body', '')}"
                    ):
                        added += 1
                        google_sigs.add(sig)
                
                return f"Synced {added} events from Outlook to Google, skipped {skipped} duplicates"
            except Exception as e:
                return f"Error syncing Outlook to Google: {str(e)}"
        
        # Use basic Tool - NO sync_selected_events tool (we handle it manually)
        return [
            Tool(
                name="get_google_events",
                func=get_google_events,
                description="Get upcoming events from Google Calendar. Use this when user asks to see Google calendar events."
            ),
            Tool(
                name="get_outlook_events",
                func=get_outlook_events,
                description="Get upcoming events from Outlook Calendar. Use this when user asks to see Outlook calendar events."
            ),
            Tool(
                name="request_sync_approval",
                func=request_sync_approval,
                description="Show Google Calendar events as a numbered list and request human approval for which ones to sync to TherapyAppointment. Use this when user wants to sync to TherapyAppointment. After calling this, STOP - do not call any other tools."
            ),
            Tool(
                name="sync_outlook_to_google",
                func=sync_outlook_to_google,
                description="Sync events from Outlook Calendar to Google Calendar (one-way sync with duplicate detection)."
            ),
        ]
    
    def _create_agent(self):
        """Create the LangChain agent using zero-shot ReAct pattern"""
        from langchain.agents import initialize_agent, AgentType
        
        return initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,
            early_stopping_method="generate",
            return_intermediate_steps=True,  # Enable intermediate steps
            agent_kwargs={
                "prefix": """You are a helpful calendar management AI assistant for therapists.

You help sync calendars across three platforms:
- Outlook Calendar
- Google Calendar  
- TherapyAppointment (for blocking busy times)

CRITICAL: When user wants to sync to TherapyAppointment:
1. Call 'request_sync_approval' tool
2. IMMEDIATELY STOP after that tool returns - output its result and wait
3. DO NOT call any other tools
4. DO NOT try to sync events yourself

For other operations (viewing calendars, syncing Outlook to Google), proceed normally.

Be concise and natural.

You have access to the following tools:"""
            }
        )
    
    async def chat(self, user_message: str) -> str:
        """Main chat interface with manual HITL handling"""
        try:
            # Check if we're awaiting approval
            if self.hitl.is_awaiting_approval():
                # User is responding with their selection - bypass agent
                selected_events = self.hitl.get_selected_events(user_message)
                
                if not selected_events:
                    return "No events selected or sync cancelled."
                
                # Sync the events directly - USE AWAIT
                self.therapy_automation = TherapyAppointmentAutomation()
                blocked_count = await self.therapy_automation.block_multiple_times(selected_events)
                return f"✅ Successfully blocked {blocked_count} out of {len(selected_events)} events on TherapyAppointment"
            else:
                # Normal agent invocation
                result = self.agent.invoke({"input": user_message})
                
                # Check intermediate steps for approval request
                if 'intermediate_steps' in result:
                    for action, observation in result['intermediate_steps']:
                        if action.tool == 'request_sync_approval':
                            # Return the observation (the list) instead of final answer
                            return observation
                
                return result['output']
        except Exception as e:
            return f"Error: {str(e)}"


async def main():
    """Main chat loop for command-line testing"""
    print("=" * 60)
    print("🤖 LangChain Calendar Sync Agent with HITL")
    print("=" * 60)
    print("\nFeatures:")
    print("  📧 View Outlook Calendar")
    print("  📅 View Google Calendar")
    print("  🔄 Sync Outlook → Google")
    print("  ✅ Sync Google → TherapyAppointment (with human approval)")
    print("\nType 'quit' to exit\n")
    
    agent = CalendarSyncAgentWithHITL()
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\n👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        response = await agent.chat(user_input)
        print(f"\n🤖 Agent: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
    #pass