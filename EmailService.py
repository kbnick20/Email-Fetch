# imports
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import json
import datetime
import psycopg2
from urllib.parse import urlparse

# connection string to connect to database
conStr = "localhost://postgres:kshitij20@email_db:5432"
pg = urlparse(conStr)
pg_connect = {
    'dbname': pg.hostname,
    'user': pg.username,
    'password': pg.password,
    'port': pg.port,
    'host': pg.scheme
}

try:
    connection = psycopg2.connect(**pg_connect)
    print("Database Connected Successfully")
except psycopg2.Error as e:
    print("Error connecting to database..")

"""
function to create the table
Run only for the first time to create the table
"""
def create_table():
    db_cursor = connection.cursor()
    query = """
        CREATE TABLE IF NOT EXISTS emails(
        id SERIAL PRIMARY KEY,
        "from" VARCHAR(200),
        "to" VARCHAR(200),
        "subject" VARCHAR(200),
        "date" VARCHAR(200),
        "labelIds" JSONB
        "createdAt" TIMESTAMP
    )
    """
    db_cursor.execute(query)
    connection.commit()
# create_table()
    

def save_data_in_db(data):
    db_cursor = connection.cursor()
    query = """
       INSERT INTO emails ("from", "to", "subject", "date")
       VALUES (%s, %s, %s, %s) 
    """
    db_cursor.execute(query, (data[0]['from'], data[0]['to'], data[0]['subject'], data[0]['date']))
    connection.commit()


file_directory = os.getcwd() + '\credentials.json'

#defined scopes for the google oauth api.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

def authentication():
    app_flow = InstalledAppFlow.from_client_secrets_file(file_directory, SCOPES)
    credentials = app_flow.run_local_server(port=8081)
    service = build('gmail', 'v1', credentials = credentials)
    return service


def fetch_emails(service, user_id='me', query=''):
    try:
        response = service.users().messages().list(userId=user_id, q=query).execute()
        messages = response.get('messages', [])
        return messages
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def fetch_email_content_by_id(service, email_id):
    try:
        response = service.users().messages().get(userId = 'me', id = email_id).execute()
        return response
    except Exception as e:
        print(f"An Error Occurred: {e}")
        return None

filename = os.getcwd() + '\data.json'
# calling function for authentication
service = authentication()
# calling function to fetch emails
emails = fetch_emails(service)

final_messages = []
extracted_messages = []
for each in emails:
    email_content = fetch_email_content_by_id(service, each['id'])
    email_data = {}
    email_data['id'] = each['id']
    email_data['labelIds'] = email_content['labelIds']
    email_data['date'] = email_content['internalDate']
    email_data['from'] = next((header['value'] for header in email_content['payload']['headers'] if header['name'] == 'From'), None)
    email_data['subject'] = next((header['value'] for header in email_content['payload']['headers'] if header['name'] == 'Subject'), None)
    email_data['to'] = next((header['value'] for header in email_content['payload']['headers'] if header['name'] == 'To'), None)

    payload = email_content['payload']
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                email_data['body'] = part['body']['data']
                break
    else:
        email_data['body'] = payload['body']['data']
    extracted_messages.append(email_data)

    # function to save data in Database table.
    save_data_in_db(extracted_messages)
    # final_messages.append(extracted_messages)
    with open(filename, "a") as file:
        json.dump(extracted_messages, file)
        file.write('\n')
    break

# to save all the messages
# for file in final_messages:
#     with open(filename, "a") as file:
#         json.dump(final_messages, file)
#         file.write('\n')

def process_emails(service, emails, rules):
    for email in emails:
        for rule_name, rule in rules.items():
            if evaluate_rule(email, rule):
                readUnreadMails(service, email['id'], rule)
                move_mail_to_label(service, email['id'], 'STARRED')


def evaluate_rule(email, rule):
    """
    Function to evaluate if an email matches a rule
    """
    predicate = rule['Predicate']
    conditions = rule['Conditions']
    if predicate == 'All':
        return all(check_condition(email, field, condition) for field, condition in conditions.items())
    elif predicate == 'Any':
        return any(check_condition(email, field, condition) for field, condition in conditions.items())


def check_condition(email, field, condition):
    """
    function to check the conditions (defined in rules.json)
    """
    if condition.get('Contains'):
        value = condition['Contains']
    else:
        value = condition['NotEquals']
    
    if field == 'From':
        return value in email['from']
    elif field == 'Subject':
        return value in email['subject']
    elif field == 'To':
        return value in email['to']
    elif field == 'Date':
        email_date = datetime.datetime.strptime(email['received_datetime'], '%Y-%m-%d %H:%M:%S')
        condition_date = datetime.datetime.strptime(condition['Less than'], '%Y-%m-%d')
        return email_date < condition_date 


def readUnreadMails(service, email_id, rules):
    """
        function to execute action (mark as read/unread)
    """
    try:
        email = service.users().messages().get(userId = 'me', id = email_id).execute()
        labels = email['labelIds']
        read_action = rules['Conditions']['ACTION']
        if_unread = 'UNREAD' in labels
        if read_action['read'] and if_unread:
            body = {'removeLabelIds': ['UNREAD']}
            service.users().messages().modify(userId='me', id=email['id'], body=body).execute()
        elif not read_action['read'] and not if_unread:
            body = {'addLabelIds': ['UNREAD']}
            service.users().messages().modify(userId='me', id=email['id'], body=body).execute()
        else:
            print("NO CHANGES")
    
    except Exception as e:
        print("Exception Occurred", e)


def move_mail_to_label(service, email_id, label_name):
    """
        function to move a mail to a label.
    """
    try:
        labels = service.users().labels().list(userId='me').execute()
        print("LE", labels)
        label_id = None
        for label in labels['labels']:
            if label['name'] == label_name:
                label_id = label['id']
                break
        if label_id:
            service.users().messages().modify(userId='me', id=email_id, body={'addLabelIds': [label_id]}).execute()
            print(f"Email moved to label")
        else:
            print("No Label Found")
        
    except Exception as e:
        print(f"An error occurred")
        

def load_rules(rule_json_filename):
    with open(rule_json_filename, "r") as file:
        rules = json.load(file)
    return rules


def load_email_data(filename):
    with open(filename, "r") as file:
        email_data = json.load(file)
    return email_data

rule_json_filename = os.path.join(os.getcwd(), 'rules.json')

# calling function to load rules (from rules.json)
rules = load_rules(rule_json_filename)
# calling function to load email data from data.json
email_data = load_email_data(filename)
process_emails(service, email_data, rules)


