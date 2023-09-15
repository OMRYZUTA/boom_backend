import os
import json
import smtplib
from datetime import datetime, timedelta
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.utils import formatdate
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi import FastAPI, Response
from pydantic import BaseModel
from ics import Calendar, Event, Todo
import gspread
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
import openai
import tiktoken
from fastapi.responses import PlainTextResponse

origins = [
    "chrome-extension://bgbmjebdlkdjellaaignohicblifofje",
]



app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
  return

@app.get("/privacy_policy", response_class=PlainTextResponse)
async def privacy_policy():
  privacy_policy = """
Effective Date:5/09/2023

Thank you for choosing the BOOM! Chrome Extension (the "Extension"). We value your privacy and are committed to protecting your personal information. This Privacy Policy explains how the BOOM! Extension collects, uses, and protects your data. By using the Extension, you agree to the practices described in this Privacy Policy.

1. Information We Collect

The BOOM! Chrome Extension uses the ChatGPT model to summarize chats within your WhatsApp web interface. It does not collect or save any private or personal information from your chats. We do not have access to your WhatsApp messages, contacts, or any other private data.

2. How We Use Your Information

We do not save or use any of your private data. The Extension's primary function is to summarize chats within your WhatsApp web interface for your convenience. The summarized information is generated on open ai servers on your device and is not stored on our servers.

3. Data Security

We take your privacy and data security seriously. The BOOM! Extension does not store any data related to your chats or personal information. All processing and summarization of chats are performed on your open ai servers and do not involve the transmission of data to external servers.

4. Third-Party Services

except open ai servers, The BOOM! Extension does not integrate with any third-party services or collect data from external sources. It solely operates within the WhatsApp web interface to provide chat summaries.

5. Cookies and Analytics

The BOOM! Extension does not use cookies or analytics tools to track your online activities. It does not monitor your browsing habits or collect any information beyond its intended functionality.

6. Children's Privacy

The BOOM! Extension is not intended for use by children under the age of 13. We do not knowingly collect or store personal information from children.

7. Updates and Changes

We may update this Privacy Policy from time to time to reflect changes in our practices or for other operational, legal, or regulatory reasons. We encourage you to review this Privacy Policy periodically.

8. Contact Us

If you have any questions, concerns, or requests related to your privacy or this Privacy Policy, please contact us at the following email addresses:

Tomerbenyehuda16@gmail.com
Omryzuta@gmail.com
By using the BOOM! Chrome Extension, you consent to the practices outlined in this Privacy Policy. Your continued use of the Extension signifies your acceptance of any changes to this policy.

Last updated: 15/09/2023

BOOM! Extensions Team
"""
  return privacy_policy


class SummarizeRequest(BaseModel):
  name: Optional[str] = None
  messages: Optional[str] = None
  mail: Optional[str] = None
  summaryType: Optional[str] = None


@app.post("/summarize")
async def summarize(request: SummarizeRequest):
  try:
    messages = request.dict()["messages"]
    print(request.dict()) 
    summary_type = request.dict()["summaryType"]
    user_mail = request.model_dump()["mail"]
    user_name = request.model_dump()["name"]

    content = messages.replace('"', '\\"')
    #if num_tokens_from_string > 800:
    # content = content[-2500:]

    answer = ''
    if (summary_type == "meeting"):
      answer = call_to_chatgpt(user_name, content, summary_type)
      print(answer)
      #match = re.search(r'\{.*\}', answer, re.DOTALL)
      #if match:

      response_dict = json.loads(answer)

      send_meeting_mail(user_mail, response_dict, summary_type)
    elif (summary_type == "task"):
      print("in task")
      answer = call_to_chatgpt(user_name, content, summary_type)
      response_dict = json.loads(answer)
      send_summary_mail(user_mail, response_dict, summary_type)
      print(answer)
    elif (summary_type == "suggestion"):
      print("in suggestion")
      answer = call_to_chatgpt(user_name, content, summary_type)
      print(answer)

    analytics(user_mail, summary_type, 'Success', answer)
    return {"answer": answer, "summary_type": summary_type}
  except Exception as e:
    print(f"An error occurred: {e}")
    analytics(request.dict()["mail"], summary_type, str(e), answer)


def send_meeting_mail(receiver, answer, summary_type):
  print(answer)
  port = 587
  smtp_server = "smtp.gmail.com"
  sender_email = os.environ['sender_email']
  password = os.environ['email_password']
  # Create a calendar with an event
  cal = Calendar()
  if (summary_type == "meeting"):
    e = Event()
    cal_str = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:ics.py - http://boom.com
BEGIN:VEVENT
DURATION:PT2H
DTSTART:{answer["date"].replace("-","")}T{answer["hour"].replace(":","")}00Z
SUMMARY:{answer["summary"]}
UID:5c740ad5-ca3a-4460-adcb-50e718f221ae@5c74.org
END:VEVENT
END:VCALENDAR"""
    print(cal_str)

  e.name = answer["title"]
  e.begin = datetime.now() + timedelta(days=1) 
  print(datetime.now() + timedelta(days=1))
  e.duration = timedelta(hours=1) 
  cal.events.add(e)
  print(e)

  # Create email
  msg = MIMEMultipart("mixed")
  msg["Subject"] = answer["title"]
  msg["From"] = sender_email
  msg["To"] = receiver
  mime_text = MIMEText(answer["title"], "plain")
  mime_event = MIMEText(cal_str, "calendar; method=REQUEST")

  msg.attach(mime_text)
  msg.attach(mime_event)

  with smtplib.SMTP(smtp_server, port) as smtp:
    smtp.starttls()
    smtp.login(sender_email, password)
    smtp.send_message(msg)  # send the email



def analytics(user, type, status, answer):
  #which google app we will use
  scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
  ]

  #json file
  credentials_info = {
    "type": "service_account",
    "project_id": "glassy-polymer-330314",
    "private_key_id":  os.environ['google_private_key_id'],
    "private_key": os.environ['google_private_key'],
    "client_email": "google@glassy-polymer-330314.iam.gserviceaccount.com",
    "client_id": "102305634558703647584",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url":
    "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url":
    "https://www.googleapis.com/robot/v1/metadata/x509/google%40glassy-polymer-330314.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
  }

  credentials = service_account.Credentials.from_service_account_info(
    credentials_info, scopes=scopes)

  gc = gspread.authorize(credentials)

  worksheet = gc.open_by_url(
    "https://docs.google.com/spreadsheets/d/1-390qKUMwDCPOnks_NJa-X6AMiy2z9AyvCJL7zexZ0g/edit?usp=sharing"
  ).sheet1

  current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

  new_row_data = [user, type, status, answer, current_timestamp]

  worksheet.append_row(new_row_data)


def call_to_chatgpt(user_name, content, task, model='gpt-3.5-turbo'):
  my_secret = os.environ['open_api_secret']
  openai.organization = "org-FlPmmJsUwf4QAxXa8sVk8xz0"
  openai.api_key = my_secret

  if task == 'meeting':
    response = openai.ChatCompletion.create(
      model=model,
      messages=[{
        "role": "system",
        "content": "you are precise meeting dictionary generator"
      }, {
        "role":
        "user",
        "content":
        f"you are doing it for {user_name}, from the messages and their dates extract the hour of the meeting, the date of the meeting, and give a title for the summary in the dictionary subtract 3 hours, in english only for example:messages: [\"[22:20, 07/08/2023] Omry Zuta: v\n[22:20, 07/08/2023] Omry Zuta: בוא נקבע למחר בשעה שש בערב בקפה של חיים, נדבר על הוקי קרח\"]\n"
      }, {
        "role":
        "assistant",
        "content":
        "{\"title\": \"water discussion\", \"hour\": \"1500\", \"date\": \"20230808\", \"summary\": \"Discussion about water at Moshe's cafe.\"}"
      }, {
        "role":
        "user",
        "content":
        f"""you are doing it for {user_name}, extract the hour of the meeting, the date, and give a title for the summary in the dictionary subtract 3 hours, in english only from the following:{str(content)}"]"""
      }],
      temperature=0,
      max_tokens=1024,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0)
  elif task == 'task':
    response = openai.ChatCompletion.create(
      model=model,
      messages=[{
        "role": "system",
        "content": "You are smart meetings summarizer"
      }, {
        "role":
        "user",
        "content":
        f"""you are doing it for {user_name}. extract people, dates, action items and important inforamtion from the following: [14:42, 12/08/2023] Omry Zuta: בעיה אחרת,
ווואצאפ שוב שינו את הdom, יותר בעיה לשלוף את התאריך מכל הודעה..
[14:42, 12/08/2023] Tomer: מההה
[14:42, 12/08/2023] Tomer: לא מתאים להם
[14:42, 12/08/2023] Tomer: מעניין איך ג'וני עובד
[14:43, 12/08/2023] Omry Zuta: כן, מעניין איך הוא עובד באמת,
לרוץ ככה על הdom, דורש תחזוק"""
      }, {
        "role":
        "assistant",
        "content":
        "{\"title\": \"Dom manipulation\",\"People\": \"Omry Zuta, Tomer\", \"hour\": \"14:43\", \"date\": \"12/08/2023\", \"summary\": \"Tomer and Omry raised their concerns regarding dom manipulation\", \"action_item\": \"investigate dom manipulation\"}"
      }, {
        "role":
        "user",
        "content":
        f"""you are doing it for {user_name}. extract title, people, date, action item and important inforamtion from the following:{str(content)}"]"""
      }],
      temperature=0,
      max_tokens=1024,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0)
  elif task == 'suggestion':
    response = openai.ChatCompletion.create(
      model=model,
      messages=[{
        "role": "system",
        "content": "you are a whatsapp messages generator"
      }, {
        "role":
        "user",
        "content":
        f"you are doing it for {user_name}. please provide the next message (up to 3 words) to this conversation in the same language:\n[20:30, 27/08/2023] אסתר היפה שלי: סיוט\n[21:00, 27/08/2023] Omry Zuta: אוי לולי\n[21:01, 27/08/2023] Omry Zuta: אצלנו הכל דבש\nהתעוררה, אכלה 100 וחזרה לישון\n[21:01, 27/08/2023] אסתר היפה שלי: מגזימן 😑"
      }, {
        "role": "assistant",
        "content": "הכל בסדר"
      }, {
        "role":
        "user",
        "content":
        f"you are doing it for {user_name}. please provide the next message(up to 3 words)  to this conversation in the same language: [19:55, 27/08/2023] אורנה השפיצית: רוצים לקבוע ארוחת צהריים בוטקאמפית, בסימן \"שרדנו עוד אוגוסט\"?\n[20:02, 27/08/2023] Weaam Riskfield: בעד\n"
      }, {
        "role": "assistant",
        "content": "מצוין"
      }, {
        "role":
        "user",
        "content":
        f"you are doing it for {user_name}. please provide the next message (up to 3 words) to this conversation in the same language:[21:01, 24/08/2023] אורלי הקטנה: יש מתעניינת ראשונה לגבי הדירה בגדרה. \nמבקשת תמונות נוספות, ולדעת מה התשלום החודשי עבור ארנונה ו-ועד\n[21:03, 24/08/2023] אורלי הקטנה: היא תעביר את הנתונים במרוכז לבן שלה ואז יבדקו אם רלוונטי"
      }, {
        "role": "assistant",
        "content": "תודה על המידע."
      }, {
        "role":
        "user",
        "content":
        f"""you are doing it for {user_name}. please provide the next message (up to 3 words) to this conversation in the same language:{str(content)}"]"""
      }],
      temperature=1,
      max_tokens=256,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0)

  print(response.choices[0].message.content)
  return response.choices[0].message.content


def num_tokens_from_string(string: str, encoding_name: str) -> int:
  """Returns the number of tokens in a text string."""
  encoding = tiktoken.get_encoding(encoding_name)
  num_tokens = len(encoding.encode(string))
  return num_tokens


def send_summary_mail(receiver, resposne_dict, summary_type):
  port = 587
  smtp_server = "smtp.gmail.com"
  sender_email = os.environ['sender_email']
  password = os.environ['email_password']

  subject = resposne_dict.get('title', '')

  body = f"""\
    Title: {resposne_dict.get('title', '')}
    People: {resposne_dict.get('People', '')}
    Dates: {resposne_dict.get('date', '')}
    Summary: {resposne_dict.get('summary', '')}
    Action Items: {resposne_dict.get('action_item', '')}"""
  msg = MIMEMultipart()
  msg['From'] = sender_email
  msg['To'] = receiver
  msg['Subject'] = subject
  msg.attach(MIMEText(body, 'plain'))

  server = smtplib.SMTP(smtp_server, port)
  server.starttls()  # Enable security
  server.login(sender_email, password)  # Login Credentials
  server.sendmail(sender_email, receiver, msg.as_string())
  server.quit()
