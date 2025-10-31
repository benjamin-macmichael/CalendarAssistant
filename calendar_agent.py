"""
Calendar Sync AI Agent with Playwright Automation
An AI-powered chatbot that syncs Google Calendar with TherapyAppointment using browser automation
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
import asyncio

# You'll need to install these:
# pip install ollama google-auth-oauthlib google-auth-httplib2 google-api-python-client playwright
# playwright install

import ollama
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from playwright.async_api import async_playwright, Browser, Page

from dotenv import load_dotenv
load_dotenv()


class CalendarSyncAgent:
    """AI Agent that syncs calendars using LLM for natural language interaction"""
    
    def __init__(self, model_name="llama3.1"):
        self.model_name = model_name
        self.google_calendar = GoogleCalendarService()
        self.therapy_appointment = None  # Will be initialized when needed
        self.conversation_history = []
        
        # System message to guide the LLM
        self.conversation_history.append({
        'role': 'system',
        'content': '''You are a helpful AI assistant that helps therapists manage their calendars.
    You can sync Google Calendar events to TherapyAppointment to prevent double-bookings.
    When syncing calendars, just confirm how many events were blocked. Don't make up appointment details or times.
    Be concise and factual.'''
    })
        
    async def chat(self, user_message: str) -> str:
        """Main chat interface with function calling capability"""
        
        # Add user message to history
        self.conversation_history.append({
            'role': 'user',
            'content': user_message
        })
        
        # Define available tools/functions
        tools = [
            {
                'type': 'function',
                'function': {
                    'name': 'sync_calendars',
                    'description': 'Syncs Google Calendar events to TherapyAppointment by blocking out busy times. This logs into TherapyAppointment and blocks the times through the web interface.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'days_ahead': {
                                'type': 'integer',
                                'description': 'Number of days ahead to sync (default 7)',
                                'default': 7
                            }
                        }
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'get_upcoming_events',
                    'description': 'Gets upcoming events from Google Calendar to see what needs to be blocked',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'days_ahead': {
                                'type': 'integer',
                                'description': 'Number of days ahead to check',
                                'default': 7
                            }
                        }
                    }
                }
            }
        ]
        
        # Call LLM with tools
        response = ollama.chat(
            model=self.model_name,
            messages=self.conversation_history,
            tools=tools
        )
        
        # Check if LLM wants to call a function
        if response['message'].get('tool_calls'):
            # Execute the function calls
            for tool_call in response['message']['tool_calls']:
                function_name = tool_call['function']['name']
                function_args = tool_call['function']['arguments']
                
                print(f"\n🤖 Executing: {function_name}")
                
                # Call the appropriate function
                if function_name == 'sync_calendars':
                    result = await self.sync_calendars(**function_args)
                elif function_name == 'get_upcoming_events':
                    result = self.get_upcoming_events(**function_args)
                else:
                    result = f"Unknown function: {function_name}"
                
                # Add function result to conversation
                self.conversation_history.append({
                    'role': 'tool',
                    'content': json.dumps(result)
                })
            
            # Get final response from LLM after function execution
            final_response = ollama.chat(
                model=self.model_name,
                messages=self.conversation_history
            )
            assistant_message = final_response['message']['content']
        else:
            assistant_message = response['message']['content']
        
        # Add assistant response to history
        self.conversation_history.append({
            'role': 'assistant',
            'content': assistant_message
        })
        
        return assistant_message
    
    async def sync_calendars(self, days_ahead: int = 7) -> Dict:
        """Syncs Google Calendar to TherapyAppointment using browser automation"""
        try:
            print("📅 Fetching events from Google Calendar...")
            # Get events from Google Calendar
            events = self.google_calendar.get_events(days_ahead)
            
            if not events:
                return {
                    'success': True,
                    'message': 'No events found to sync',
                    'events_synced': 0
                }
            
            print(f"✓ Found {len(events)} events to sync")
            print("🌐 Opening TherapyAppointment...")
            
            # Initialize browser automation
            try:
                self.therapy_appointment = TherapyAppointmentAutomation()
                print("✓ TherapyAppointmentAutomation initialized")
                
                # Block times in TherapyAppointment
                blocked_count = await self.therapy_appointment.block_multiple_times(events)
            except Exception as e:
                print(f"❌ Error during automation: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            return {
                'success': True,
                'message': f'Successfully synced {blocked_count} out of {len(events)} events',
                'events_synced': blocked_count,
                'total_events': len(events)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error syncing calendars: {str(e)}',
                'events_synced': 0
            }
    
    def get_upcoming_events(self, days_ahead: int = 7) -> Dict:
        """Gets upcoming events from Google Calendar"""
        try:
            events = self.google_calendar.get_events(days_ahead)
            
            event_list = []
            for event in events:
                event_list.append({
                    'summary': event['summary'],
                    'start': event['start'],
                    'end': event['end']
                })
            
            return {
                'success': True,
                'events': event_list,
                'count': len(event_list)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting events: {str(e)}',
                'events': []
            }


class GoogleCalendarService:
    """Handles Google Calendar API interactions"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticates with Google Calendar API"""
        creds = None
        
        # Token file stores user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    print("⚠️  credentials.json not found!")
                    print("Download from Google Cloud Console and place in project root")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('calendar', 'v3', credentials=creds)
    
    def get_events(self, days_ahead: int = 7) -> List[Dict]:
        """Gets events from Google Calendar"""
        if not self.service:
            return []
        
        now = datetime.utcnow()
        end_time = now + timedelta(days=days_ahead)
        
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Parse and format events
        formatted_events = []
        for event in events:
            # Skip all-day events
            if 'dateTime' not in event['start']:
                continue
                
            start = event['start'].get('dateTime')
            end = event['end'].get('dateTime')
            
            formatted_events.append({
                'summary': event.get('summary', 'No Title'),
                'start': start,
                'end': end,
                'id': event['id']
            })
        
        return formatted_events


class TherapyAppointmentAutomation:
    """Handles TherapyAppointment browser automation using Playwright"""
    
    def __init__(self):
        self.email = os.getenv('THERAPY_APPOINTMENT_EMAIL')
        self.password = os.getenv('THERAPY_APPOINTMENT_PASSWORD')
        self.url = os.getenv('THERAPY_APPOINTMENT_URL', 'https://www.therapyappointment.com')
        
        if not self.email or not self.password:
            raise ValueError("TherapyAppointment credentials not set in .env file!")
    
    async def block_multiple_times(self, events: List[Dict]) -> int:
        """Blocks multiple time slots in TherapyAppointment"""
        
        async with async_playwright() as p:
            # Launch browser (use headless=False to see what's happening)
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Login to TherapyAppointment
                print("🔐 Logging in...")
                await self._login(page)
                
                # Navigate to availability/calendar settings
                print("📅 Navigating to calendar settings...")
                await self._navigate_to_availability(page)
                
                blocked_count = 0
                
                # Block each time slot
                for event in events:
                    try:
                        print(f"⏰ Blocking: {event['summary']} ({event['start']} - {event['end']})")
                        success = await self._block_time_slot(page, event)
                        if success:
                            blocked_count += 1
                            print(f"   ✓ Blocked successfully")
                        else:
                            print(f"   ✗ Failed to block")
                        print("📅 Navigating to calendar settings...")
                        await self._navigate_to_availability(page)
                    except Exception as e:
                        print(f"   ✗ Error: {e}")
                        continue
                
                print(f"\n✅ Blocked {blocked_count} out of {len(events)} time slots")
                
                # Keep browser open for a moment so user can see result
                await asyncio.sleep(2)
                
                return blocked_count
                
            finally:
                await browser.close()
    
    async def _login(self, page: Page):
        """Logs into TherapyAppointment"""
        
        # Navigate to login page
        await page.goto(f"{self.url}/login")
        
        # Wait for page to load
        await page.wait_for_load_state('networkidle')
        
        # Fill in credentials
        # NOTE: These selectors need to be updated based on actual TherapyAppointment HTML
        # You'll need to inspect the page and find the correct selectors
        
        try:
            # Try common email/username field selectors
            await page.fill('#user_username', self.email)
            await page.fill('#user_password', self.password)
            
            # Click login button
            await page.click('button[type="submit"]')
            
            # Wait for navigation after login
            await page.wait_for_load_state('networkidle')
            
            print("✓ Login successful")
            
        except Exception as e:
            print(f"⚠️  Login failed: {e}")
            print("You may need to update the selectors in _login() method")
            print("Inspect TherapyAppointment's login page to find correct element selectors")
            raise
    
    async def _navigate_to_availability(self, page: Page):
        """Navigates to the availability/calendar settings page"""
        
        try:
            # Wait a bit after login for any redirects to complete
            await asyncio.sleep(2)
            
            # Navigate to the schedule page
            await page.goto('https://api.portal.therapyappointment.com/n/schedule', 
                        wait_until='domcontentloaded',  # Less strict waiting
                        timeout=60000)  # Give it more time
            
            # Wait for the page to be ready
            await page.wait_for_load_state('networkidle')
            print("✓ Navigated to schedule page")
            
        except Exception as e:
            print(f"Navigation error: {e}")
            print(f"Current URL: {page.url}")
            # Take a screenshot to see what's happening
            await page.screenshot(path='debug_navigation.png')
            print("Screenshot saved to debug_navigation.png")
            raise
    
    async def _block_time_slot(self, page: Page, event: Dict) -> bool:
        """Blocks a specific time slot"""
        
        # Parse datetime strings
        start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
        
        try:
            await page.click('text=Edit Availability')
            await asyncio.sleep(2)

            await page.get_by_role("button", name="Close dialog").click()

            # Step 2: Click "Out of Office"
            print(f"   Selecting 'Out of Office'")
            await page.click('button:has-text("Out Of Office")')
            await asyncio.sleep(2)

            # Step 3: Click "Lets do that"
            await page.click('button:has-text("Let\'s do that")')
            await asyncio.sleep(2)
            
            date_str = start_dt.strftime('%m/%d/%Y')  # MM/DD/YYYY format
            print(date_str)
            start_time_str = start_dt.strftime('%H:%M')  # 24-hour format
            end_time_str = end_dt.strftime('%H:%M')
            
            # Step 4: Navigate calendar to correct month and click day
            print(f"   Filling date: {date_str}")
            await page.click('#event_date')  # open calendar popup
            await asyncio.sleep(1)
            
            # Navigate to the correct month
            target_month = start_dt.month
            target_year = start_dt.year
            
            # Keep clicking next/previous until we're in the right month
            max_attempts = 24  # Prevent infinite loop
            for _ in range(max_attempts):
                try:
                    # Get the currently displayed month/year from the datepicker
                    combined = await page.text_content('th.datepicker-switch')
                    # Example: "October 2025" or "November 2024"
                    
                    parts = combined.split()
                    month_name = parts[0]  # "October"
                    current_year = int(parts[1])  # 2025
                    
                    # Convert month name to number (e.g., "November" -> 11)
                    from datetime import datetime as dt
                    current_month = dt.strptime(month_name, '%B').month
                    
                    if current_year == target_year and current_month == target_month:
                        break  # We're in the right month!
                    elif (current_year < target_year) or (current_year == target_year and current_month < target_month):
                        # Need to go forward
                        await page.click('th.next')
                    else:
                        # Need to go backward
                        await page.click('th.prev')
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"   Warning: Could not navigate calendar: {e}")
                    print(f"   You may need to update the calendar selectors")
                    break
            
            # Now click the day
            day_selector = f'td.day:not(.old):not(.new):has-text("{start_dt.day}")'
            await page.click(day_selector)
            await asyncio.sleep(1)
            
            # Step 5: Set start time
            print(f"   Filling start time: {start_time_str}")
            await page.fill('#event_starttime', start_time_str)
            await asyncio.sleep(1)
            
            # Step 6: Set end time
            print(f"   Filling end time: {end_time_str}")
            await page.fill('#event_endtime', end_time_str)
            await asyncio.sleep(1)

            # Step 7: Set title
            print(f"   Setting title to Unavailable")
            await page.fill('#calendar_event_name', 'Unavailable')
            await asyncio.sleep(1)
            
            # Step 8: Click Save
            print(f"   Clicking Save")
            await page.click('button[type="submit"].btn-action')
            
            # Wait for it to save
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"   Error: {e}")
            await page.screenshot(path='debug_error.png')
            return False


async def main():
    """Main chat loop"""
    print("=" * 60)
    print("🤖 Calendar Sync AI Agent with Browser Automation")
    print("=" * 60)
    print("\nI can help you sync your Google Calendar with TherapyAppointment!")
    print("I'll use browser automation to block times directly in the web interface.")
    print("\nTry saying things like:")
    print("  - 'Sync my calendar for the next week'")
    print("  - 'What events do I have coming up?'")
    print("  - 'Block out my busy times'")
    print("\nType 'quit' to exit\n")
    
    agent = CalendarSyncAgent()
    
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