# CSE3311_Team4

Github repository for  CSE 3311-002 Team 4

Members:  
Mohammad Hasibur Rahman  
Ariston Stitt  
Joshua Thomas  
Kaitlynn Hernandez  

Project Overview  
Our project is a simple database-driven system that helps students manage and track campus club memberships. The system allows users to add students and clubs, join students to clubs, and view membership lists.  

Problem: Current available platforms/methods for tracking club memberships are inefficient or too overwhelming/complicated. Students and club officers often rely on manual, disparate systems like paper sign-up sheets, spreadsheets, or informal group chats. This leads to inaccurate data, wasted time, and difficulty in communicating with all members. The platforms that do exist have overcomplicated features, making students stray away from wanting to use it to learn more about campus organizations.   

Goal: The goal is to provide a clear and easy-to-use platform that demonstrates basic database operations like creating, reading, updating, and deleting records, all within a context that is highly relatable to students.  

Compile & Run  

Club House System Setup
Environment Configuration
1.	Create a .env file in the project root with the following variables:

Firebase Configuration  
Option 1: Use service account file path  
FIREBASE_SERVICE_ACCOUNT_PATH=path/to/your/serviceAccountKey.json  
Option 2: Use service account key as JSON string (recommended for production)
FIREBASE_SERVICE_ACCOUNT_KEY={"type":"service_account","project_id":"your-project-id",...}    

Flask Configuration  
FLASK_SECRET_KEY=your-super-secret-key-here-change-this-in-production

Firebase Setup
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Go to Project Settings > Service Accounts
4. Generate a new private key (downloads a JSON file)
5. Either:
   - Save the JSON file in your project and set FIREBASE_SERVICE_ACCOUNT_PATH
   - Copy the JSON content and set FIREBASE_SERVICE_ACCOUNT_KEY
     
Installation
1.	Create a virtual environment
python3 –m venv venv
Source venv/bin/activate
2.	Install dependencies:
pip install -r requirements.txt
3.	 Run the application:
python app.py
The application will be available at http://localhost:5000

Features
- Create, read, update, delete clubs
- Search clubs by name or description
- View club rosters and member details
- Add/remove members from clubs



