# Club House System Setup

## Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# Firebase Configuration
# Option 1: Use service account file path
FIREBASE_SERVICE_ACCOUNT_PATH=path/to/your/serviceAccountKey.json

# Option 2: Use service account key as JSON string (recommended for production)
# FIREBASE_SERVICE_ACCOUNT_KEY={"type":"service_account","project_id":"your-project-id",...}

# Flask Configuration
FLASK_SECRET_KEY=your-super-secret-key-here-change-this-in-production

# Development Settings
FLASK_ENV=development
FLASK_DEBUG=True
```

## Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Go to Project Settings > Service Accounts
4. Generate a new private key (downloads a JSON file)
5. Either:
   - Save the JSON file in your project and set `FIREBASE_SERVICE_ACCOUNT_PATH`
   - Copy the JSON content and set `FIREBASE_SERVICE_ACCOUNT_KEY`

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Features

- ✅ Create, read, update, delete clubs
- ✅ Search clubs by name or description
- ✅ View club rosters and member details
- ✅ Add/remove members from clubs
- ✅ Manage student records
- ✅ Responsive modern UI
- ✅ Real-time Firebase integration

## Database Schema

The application uses the following Firebase Firestore structure:

```json
{
  "clubs": {
    "club_id": {
      "name": "string",
      "description": "string", 
      "created_at": "ISO_8601_timestamp",
      "member_count": "number (computed/cached)"
    }
  },
  "students": {
    "student_id": {
      "name": "string",
      "email": "string",
      "created_at": "ISO_8601_timestamp"
    }
  },
  "memberships": {
    "membership_id": {
      "club_id": "string",
      "student_id": "string", 
      "role": "Member|Officer|President|Vice President|Treasurer|Secretary",
      "join_date": "ISO_8601_timestamp"
    }
  },
  "club_members": {
    "club_id": {
      "student_id": {
        "membership_id": "string",
        "role": "string",
        "join_date": "ISO_8601_timestamp"
      }
    }
  },
  "student_memberships": {
    "student_id": {
      "club_id": {
        "membership_id": "string",
        "role": "string", 
        "join_date": "ISO_8601_timestamp"
      }
    }
  }
}
```
