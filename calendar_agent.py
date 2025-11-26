"""
Calendar Sync AI Agent with Outlook and Google Calendar Integration
Syncs between Outlook, Google Calendar, and TherapyAppointment
"""

import json
import os
from datetime import datetime, timedelta
import datetime as dt
from typing import List, Dict, Optional
import asyncio

import ollama
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from playwright.async_api import async_playwright, Browser, Page

# Microsoft Graph API for Outlook
import msal
import requests

from dotenv import load_dotenv
load_dotenv()


class CalendarSyncAgent:
    """AI Agent that syncs calendars using LLM for natural language interaction"""
    
    def __init__(self, model_name="llama3.1"):
        self.model_name = model_name
        self.google_calendar = GoogleCalendarService()
        self.outlook_calendar = OutlookCalendarService()
        self.therapy_appointment = None
        self.conversation_history = []
        
        # Enhanced system message with Outlook support
        self.conversation_history.append({
            'role': 'system',
            'content': '''You are a helpful AI assistant that helps therapists manage their calendars across multiple platforms.

You have access to these tools:
- sync_calendars: Blocks Google Calendar events on TherapyAppointment to prevent double-bookings
- get_upcoming_events: Shows what's on the Google Calendar
- get_outlook_events: Shows what's on the Outlook Calendar
- sync_outlook_to_google: Copies events from Outlook Calendar to Google Calendar (one-way sync)

IMPORTANT RULES:
1. ONLY use tools when the user explicitly requests calendar operations:
   - "sync my calendar", "block times", "update my schedule"
   - "show my events", "what's on my calendar", "check my schedule"
   - "sync outlook to google", "copy outlook events", "import from outlook"
   - "show outlook events", "what's on my outlook calendar"

2. For general questions, advice, or casual conversation, respond normally WITHOUT using tools.

3. When syncing calendars:
   - Confirm how many events were processed
   - Be specific about the time period and direction (Outlook → Google → TherapyAppointment)
   - Mention if any events failed to sync or were skipped (duplicates)

4. Be concise and natural. Don't over-explain or use excessive formatting.

5. If credentials are missing or errors occur, clearly explain what's needed.

6. When asked about "all calendars" or "everything", check both Google and Outlook calendars.'''
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
                    'description': 'Syncs Google Calendar events to TherapyAppointment by blocking out busy times.',
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
                    'description': 'Gets upcoming events from Google Calendar.',
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
            },
            {
                'type': 'function',
                'function': {
                    'name': 'get_outlook_events',
                    'description': 'Gets upcoming events from Outlook Calendar.',
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
            },
            {
                'type': 'function',
                'function': {
                    'name': 'sync_outlook_to_google',
                    'description': 'Syncs events from Outlook Calendar to Google Calendar. Copies Outlook events to Google, avoiding duplicates.',
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
                elif function_name == 'get_outlook_events':
                    result = self.get_outlook_events(**function_args)
                elif function_name == 'sync_outlook_to_google':
                    result = self.sync_outlook_to_google(**function_args)
                else:
                    result = {'success': False, 'message': f"Unknown function: {function_name}"}
                
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
            events = self.google_calendar.get_events(days_ahead)
            
            if not events:
                return {
                    'success': True,
                    'message': 'No events found to sync',
                    'events_synced': 0
                }
            
            print(f"✓ Found {len(events)} events to sync")
            print("🌐 Opening TherapyAppointment...")
            
            self.therapy_appointment = TherapyAppointmentAutomation()
            blocked_count = await self.therapy_appointment.block_multiple_times(events)
            
            return {
                'success': True,
                'message': f'Successfully synced {blocked_count} out of {len(events)} events from Google to TherapyAppointment',
                'events_synced': blocked_count,
                'total_events': len(events)
            }
            
        except Exception as e:
            print(f"❌ Error during sync: {e}")
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
                start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
                
                event_list.append({
                    'summary': event['summary'],
                    'start': start_dt.strftime('%B %d, %Y at %I:%M %p'),
                    'end': end_dt.strftime('%I:%M %p'),
                    'duration': f"{int((end_dt - start_dt).total_seconds() / 60)} minutes"
                })
            
            return {
                'success': True,
                'source': 'Google Calendar',
                'events': event_list,
                'count': len(event_list),
                'period': f'next {days_ahead} days'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting Google Calendar events: {str(e)}',
                'events': [],
                'count': 0
            }
    
    def get_outlook_events(self, days_ahead: int = 7) -> Dict:
        """Gets upcoming events from Outlook Calendar"""
        try:
            events = self.outlook_calendar.get_events(days_ahead)
            
            event_list = []
            for event in events:
                event_list.append({
                    'summary': event['subject'],
                    'start': event['start_formatted'],
                    'end': event['end_formatted'],
                    'duration': f"{event['duration_minutes']} minutes"
                })
            
            return {
                'success': True,
                'source': 'Outlook Calendar',
                'events': event_list,
                'count': len(event_list),
                'period': f'next {days_ahead} days'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting Outlook events: {str(e)}',
                'events': [],
                'count': 0
            }
    
    def sync_outlook_to_google(self, days_ahead: int = 7) -> Dict:
        """Syncs events from Outlook Calendar to Google Calendar"""
        try:
            print("📧 Fetching events from Outlook Calendar...")
            outlook_events = self.outlook_calendar.get_events(days_ahead)
            
            if not outlook_events:
                return {
                    'success': True,
                    'message': 'No Outlook events found to sync',
                    'events_synced': 0,
                    'events_skipped': 0
                }
            
            print(f"✓ Found {len(outlook_events)} Outlook events")
            print("📅 Checking Google Calendar for duplicates...")
            
            # Get existing Google events to avoid duplicates
            google_events = self.google_calendar.get_events(days_ahead)
            
            # Create a set of Google event signatures for duplicate checking
            google_signatures = set()
            for gevent in google_events:
                start_dt = datetime.fromisoformat(gevent['start'].replace('Z', '+00:00'))
                signature = f"{gevent['summary']}_{start_dt.strftime('%Y%m%d%H%M')}"
                google_signatures.add(signature)
            
            # Add Outlook events to Google Calendar
            added_count = 0
            skipped_count = 0
            
            for outlook_event in outlook_events:
                # Check for duplicate
                start_dt = datetime.fromisoformat(outlook_event['start'])
                signature = f"{outlook_event['subject']}_{start_dt.strftime('%Y%m%d%H%M')}"
                
                if signature in google_signatures:
                    print(f"⊘ Skipping duplicate: {outlook_event['subject']}")
                    skipped_count += 1
                    continue
                
                # Add to Google Calendar
                print(f"➕ Adding: {outlook_event['subject']}")
                success = self.google_calendar.add_event(
                    summary=outlook_event['subject'],
                    start_time=outlook_event['start'],
                    end_time=outlook_event['end'],
                    description=f"Synced from Outlook Calendar\n\n{outlook_event.get('body', '')}"
                )
                
                if success:
                    added_count += 1
                    google_signatures.add(signature)  # Add to set to avoid adding twice
            
            return {
                'success': True,
                'message': f'Synced {added_count} events from Outlook to Google Calendar, skipped {skipped_count} duplicates',
                'events_synced': added_count,
                'events_skipped': skipped_count,
                'total_events': len(outlook_events)
            }
            
        except Exception as e:
            print(f"❌ Error syncing Outlook to Google: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Error syncing Outlook to Google: {str(e)}',
                'events_synced': 0
            }


class GoogleCalendarService:
    """Handles Google Calendar API interactions"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']  # Changed to full access
    
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticates with Google Calendar API"""
        creds = None
        
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError(
                        "credentials.json not found! "
                        "Download from Google Cloud Console and place in project root."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('calendar', 'v3', credentials=creds)
    
    def get_events(self, days_ahead: int = 7) -> List[Dict]:
        """Gets events from Google Calendar"""
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
                
            start = event['start'].get('dateTime')
            end = event['end'].get('dateTime')
            
            formatted_events.append({
                'summary': event.get('summary', 'No Title'),
                'start': start,
                'end': end,
                'id': event['id']
            })
        
        return formatted_events
    
    def add_event(self, summary: str, start_time: str, end_time: str, description: str = "") -> bool:
        """Adds a new event to Google Calendar"""
        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC',
                },
            }
            
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            print(f"✓ Event created: {created_event.get('htmlLink')}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to create event: {e}")
            return False


class OutlookCalendarService:
    """Handles Outlook Calendar API interactions using Microsoft Graph"""
    
    def __init__(self):
        self.client_id = os.getenv('OUTLOOK_CLIENT_ID')
        self.tenant_id = os.getenv('OUTLOOK_TENANT_ID', 'common')
        
        if not self.client_id:
            raise ValueError(
                "Outlook credentials not set! "
                "Add OUTLOOK_CLIENT_ID to your .env file"
            )
        
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scopes = ['Calendars.Read', 'Calendars.ReadWrite', 'User.Read']
        
        # Use PublicClientApplication for device code flow (interactive login)
        self.app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority
        )
        
        self.token = self._get_token()
    
    def _get_token(self):
        """Gets access token for Microsoft Graph API"""
        # Try to get token from cache
        token_cache_file = 'outlook_token_cache.json'
        
        if os.path.exists(token_cache_file):
            with open(token_cache_file, 'r') as f:
                cache_data = json.load(f)
                if cache_data.get('access_token'):
                    # Check if token is still valid (simple check)
                    return cache_data['access_token']
        
        # Get new token using device code flow (interactive)
        flow = self.app.initiate_device_flow(scopes=["Calendars.Read"])
        
        if "user_code" not in flow:
            raise ValueError("Failed to create device flow")
        
        print("\n" + "="*60)
        print("🔐 OUTLOOK AUTHENTICATION REQUIRED")
        print("="*60)
        print(flow["message"])
        print("="*60 + "\n")
        
        # Wait for user to authenticate
        result = self.app.acquire_token_by_device_flow(flow)
        
        if "access_token" in result:
            # Save token to cache
            with open(token_cache_file, 'w') as f:
                json.dump(result, f)
            return result['access_token']
        else:
            raise ValueError(f"Failed to authenticate: {result.get('error_description')}")
    
    def get_events(self, days_ahead: int = 7) -> List[Dict]:
        """Gets events from Outlook Calendar"""
        now = datetime.now(dt.timezone.utc)
        end_time = now + timedelta(days=days_ahead)
        
        # Microsoft Graph API endpoint
        endpoint = "https://graph.microsoft.com/v1.0/me/calendar/events"
        
        # Query parameters
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
            
            data = response.json()
            events = data.get('value', [])
            
            formatted_events = []
            for event in events:
                start_str = event['start']['dateTime']
                end_str = event['end']['dateTime']
                
                # Parse times
                start_dt = datetime.fromisoformat(start_str)
                end_dt = datetime.fromisoformat(end_str)
                
                # Add timezone if not present
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=dt.timezone.utc)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=dt.timezone.utc)
                
                duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
                
                formatted_events.append({
                    'subject': event.get('subject', 'No Title'),
                    'start': start_dt.isoformat(),
                    'end': end_dt.isoformat(),
                    'start_formatted': start_dt.strftime('%B %d, %Y at %I:%M %p'),
                    'end_formatted': end_dt.strftime('%I:%M %p'),
                    'duration_minutes': duration_minutes,
                    'body': event.get('body', {}).get('content', '')
                })
            
            return formatted_events
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("Token expired, refreshing...")
                # Remove cached token and try again
                if os.path.exists('outlook_token_cache.json'):
                    os.remove('outlook_token_cache.json')
                self.token = self._get_token()
                return self.get_events(days_ahead)  # Retry
            raise


class TherapyAppointmentAutomation:
    """Handles TherapyAppointment browser automation using Playwright"""
    
    def __init__(self):
        self.email = os.getenv('THERAPY_APPOINTMENT_EMAIL')
        self.password = os.getenv('THERAPY_APPOINTMENT_PASSWORD')
        self.url = os.getenv('THERAPY_APPOINTMENT_URL', 'https://www.therapyappointment.com')
        
        if not self.email or not self.password:
            raise ValueError(
                "TherapyAppointment credentials not set! "
                "Add THERAPY_APPOINTMENT_EMAIL and THERAPY_APPOINTMENT_PASSWORD to your .env file"
            )
    
    async def block_multiple_times(self, events: List[Dict]) -> int:
        """Blocks multiple time slots in TherapyAppointment"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=500
            )
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()
            
            try:
                print("🔐 Logging in...")
                await self._login(page)
                
                print("📅 Navigating to calendar settings...")
                await self._navigate_to_availability(page)
                
                blocked_count = 0
                
                for i, event in enumerate(events, 1):
                    try:
                        print(f"\n⏰ [{i}/{len(events)}] Blocking: {event['summary']}")
                        success = await self._block_time_slot(page, event)
                        
                        if success:
                            blocked_count += 1
                            print(f"   ✓ Blocked successfully")
                        else:
                            print(f"   ✗ Failed to block")
                        
                        print("   📅 Returning to calendar...")
                        await self._navigate_to_availability(page)
                        
                    except Exception as e:
                        print(f"   ✗ Error: {e}")
                        await page.screenshot(path=f'error_event_{i}.png')
                        continue
                
                print(f"\n✅ Successfully blocked {blocked_count} out of {len(events)} time slots")
                await asyncio.sleep(2)
                
                return blocked_count
                
            except Exception as e:
                print(f"❌ Critical error: {e}")
                await page.screenshot(path='critical_error.png')
                raise
            finally:
                await browser.close()
    
    async def _login(self, page: Page):
        """Logs into TherapyAppointment"""
        await page.goto(f"{self.url}/login", wait_until='networkidle')
        
        try:
            await page.fill('#user_username', self.email)
            await page.fill('#user_password', self.password)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            print("✓ Login successful")
        except Exception as e:
            print(f"⚠️  Login failed: {e}")
            await page.screenshot(path='login_error.png')
            raise
    
    async def _navigate_to_availability(self, page: Page):
        """Navigates to the availability/calendar settings page"""
        try:
            await asyncio.sleep(1)
            await page.goto(
                'https://api.portal.therapyappointment.com/n/schedule',
                wait_until='domcontentloaded',
                timeout=60000
            )
            await page.wait_for_load_state('networkidle')
            print("✓ Navigated to schedule page")
        except Exception as e:
            print(f"Navigation error: {e}")
            await page.screenshot(path='navigation_error.png')
            raise
    
    async def _block_time_slot(self, page: Page, event: Dict) -> bool:
        """Blocks a specific time slot"""
        start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
        
        try:
            await page.click('text=Edit Availability')
            await asyncio.sleep(2)
            
            try:
                await page.get_by_role("button", name="Close dialog").click(timeout=2000)
            except:
                pass
            
            print(f"   Selecting 'Out of Office'")
            await page.click('button:has-text("Out Of Office")')
            await asyncio.sleep(2)
            
            await page.click('button:has-text("Let\'s do that")')
            await asyncio.sleep(2)
            
            date_str = start_dt.strftime('%m/%d/%Y')
            print(f"   Setting date: {date_str}")
            
            await page.click('#event_date')
            await asyncio.sleep(1)
            
            await self._navigate_calendar(page, start_dt)
            
            day_selector = f'td.day:not(.old):not(.new):has-text("{start_dt.day}")'
            await page.click(day_selector)
            await asyncio.sleep(1)
            
            start_time_str = start_dt.strftime('%H:%M')
            end_time_str = end_dt.strftime('%H:%M')
            
            print(f"   Setting time: {start_time_str} - {end_time_str}")
            await page.fill('#event_starttime', start_time_str)
            await asyncio.sleep(0.5)
            await page.fill('#event_endtime', end_time_str)
            await asyncio.sleep(0.5)
            
            await page.fill('#calendar_event_name', 'Unavailable')
            await asyncio.sleep(0.5)
            
            print(f"   Saving...")
            await page.click('button[type="submit"].btn-action')
            await asyncio.sleep(3)
            
            return True
            
        except Exception as e:
            print(f"   Error blocking time slot: {e}")
            await page.screenshot(path='block_error.png')
            return False
    
    async def _navigate_calendar(self, page: Page, target_date: datetime):
        """Navigate datepicker to the correct month"""
        target_month = target_date.month
        target_year = target_date.year
        
        max_attempts = 24
        for _ in range(max_attempts):
            try:
                combined = await page.text_content('th.datepicker-switch')
                parts = combined.split()
                month_name = parts[0]
                current_year = int(parts[1])
                
                current_month = datetime.strptime(month_name, '%B').month
                
                if current_year == target_year and current_month == target_month:
                    break
                elif (current_year < target_year) or (current_year == target_year and current_month < target_month):
                    await page.click('th.next')
                else:
                    await page.click('th.prev')
                
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"   Warning: Calendar navigation issue: {e}")
                break


async def main():
    """Main chat loop"""
    print("=" * 60)
    print("🤖 Multi-Calendar Sync AI Agent")
    print("=" * 60)
    print("\nI can help you sync calendars across:")
    print("  📧 Outlook Calendar")
    print("  📅 Google Calendar")
    print("  🗓️  TherapyAppointment")
    print("\nTry saying:")
    print("  • 'Show my Outlook events'")
    print("  • 'Sync Outlook to Google'")
    print("  • 'Sync everything to TherapyAppointment'")
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
    #asyncio.run(main())
    pass