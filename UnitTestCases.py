import unittest
from unittest.mock import MagicMock, patch
from EmailService import move_mail_to_label
from EmailService import authentication, fetch_emails, fetch_email_content_by_id, process_emails

class UnitTestCases(unittest.TestCase):

    def setUp(self):
        self.mockService = MagicMock()

    def save_data_db(self):
        data = [
            {
            "id": "18e2952c355437e2", 
            "labelIds": ["UNREAD", "IMPORTANT", "STARRED", "CATEGORY_UPDATES", "INBOX"], 
            "date": "1710090273000", 
            "from": "GitHub <noreply@github.com>",
            "subject": "[GitHub] Please verify your device", 
            "to": "Kshitij Bhatnagar <bhatnagarkshitij20@gmail.com>", 
            "body": "SGV5IGtibmljazIwIQ0KDQpBIHNpZ24gaW="}
            ]

    def test_process_emails(self):
        email = {
            'id': '123456',
            'from': 'from@gmail.com',
            'to': 'to@gmail.com',
            'subject': 'Subject',
            'date': '2024-02-07 10:00:00',
            'labelIds': ['INBOX'],
            'createdAt': '2024-03-07 10:00:00'
        }
        rules = {
            "Conditions": {
                "From": {
                    "Contains": "random@gmail.com"
                },
                "Subject": {
                    "Contains": "Random"
                },
                "To": {
                    "Contains":  "bhatnagarkshitij20@gmail.com"
                },
                "Date": {
                    "Less than": "2022-01-01"
                },
                "ACTION":{
                    "read": True,
                    "move_lable": [True, "SENT"]
                }
            },
            "Predicate": "All"
        }
        self.mock_service.users().messages().modify.return_value.execute.return_value = {'id': '123456'}
        process_emails(self.mock_service, [email], rules)


if __name__ == "__main__":
    unittest.main()