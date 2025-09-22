import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK
def initialize_firebase():
    if not firebase_admin._apps:
        # For production, use service account key
        if os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY'):
            import json
            service_account_info = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY'))
            cred = credentials.Certificate(service_account_info)
        else:
            # For development, use service account file
            service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'serviceAccountKey.json')
            cred = credentials.Certificate(service_account_path)
        
        firebase_admin.initialize_app(cred)
    
    return firestore.client()

# Get Firestore database instance
def get_db():
    return initialize_firebase()

# Database helper functions
class FirebaseDB:
    def __init__(self):
        self.db = get_db()
    
    # Club operations
    def create_club(self, club_data):
        """Create a new club"""
        from datetime import datetime
        club_data['created_at'] = datetime.now().isoformat()
        club_data['member_count'] = 0
        
        doc_ref = self.db.collection('clubs').document()
        doc_ref.set(club_data)
        return doc_ref.id
    
    def get_all_clubs(self):
        """Get all clubs"""
        clubs = []
        docs = self.db.collection('clubs').stream()
        for doc in docs:
            club_data = doc.to_dict()
            club_data['id'] = doc.id
            clubs.append(club_data)
        return clubs
    
    def get_club(self, club_id):
        """Get a specific club"""
        doc = self.db.collection('clubs').document(club_id).get()
        if doc.exists:
            club_data = doc.to_dict()
            club_data['id'] = doc.id
            return club_data
        return None
    
    def update_club(self, club_id, club_data):
        """Update a club"""
        doc_ref = self.db.collection('clubs').document(club_id)
        doc_ref.update(club_data)
        return True
    
    def delete_club(self, club_id):
        """Delete a club and all associated memberships"""
        # Delete club document
        self.db.collection('clubs').document(club_id).delete()
        
        # Delete associated memberships
        memberships = self.db.collection('memberships').where('club_id', '==', club_id).stream()
        for membership in memberships:
            membership.reference.delete()
        
        # Delete from club_members
        if self.db.collection('club_members').document(club_id).get().exists:
            self.db.collection('club_members').document(club_id).delete()
        
        # Delete from student_memberships
        student_memberships = self.db.collection('student_memberships').stream()
        for student_doc in student_memberships:
            student_data = student_doc.to_dict()
            if club_id in student_data:
                self.db.collection('student_memberships').document(student_doc.id).update({
                    club_id: firestore.DELETE_FIELD
                })
        
        return True
    
    def search_clubs(self, query):
        """Search clubs by name"""
        clubs = self.get_all_clubs()
        if not query:
            return clubs
        
        query = query.lower()
        filtered_clubs = []
        for club in clubs:
            if query in club.get('name', '').lower() or query in club.get('description', '').lower():
                filtered_clubs.append(club)
        return filtered_clubs
    
    # Student operations
    def create_student(self, student_data):
        """Create a new student"""
        from datetime import datetime
        student_data['created_at'] = datetime.now().isoformat()
        
        doc_ref = self.db.collection('students').document()
        doc_ref.set(student_data)
        return doc_ref.id
    
    def get_all_students(self):
        """Get all students"""
        students = []
        docs = self.db.collection('students').stream()
        for doc in docs:
            student_data = doc.to_dict()
            student_data['id'] = doc.id
            students.append(student_data)
        return students
    
    def get_student(self, student_id):
        """Get a specific student"""
        doc = self.db.collection('students').document(student_id).get()
        if doc.exists:
            student_data = doc.to_dict()
            student_data['id'] = doc.id
            return student_data
        return None
    
    # Membership operations
    def add_member_to_club(self, club_id, student_id, role="Member"):
        """Add a student to a club"""
        from datetime import datetime
        
        # Create membership record
        membership_data = {
            'club_id': club_id,
            'student_id': student_id,
            'role': role,
            'join_date': datetime.now().isoformat()
        }
        
        membership_ref = self.db.collection('memberships').document()
        membership_ref.set(membership_data)
        membership_id = membership_ref.id
        
        # Update club_members
        club_member_data = {
            'membership_id': membership_id,
            'role': role,
            'join_date': membership_data['join_date']
        }
        self.db.collection('club_members').document(club_id).set({
            student_id: club_member_data
        }, merge=True)
        
        # Update student_memberships
        self.db.collection('student_memberships').document(student_id).set({
            club_id: club_member_data
        }, merge=True)
        
        # Update member count
        self.update_club_member_count(club_id)
        
        return membership_id
    
    def remove_member_from_club(self, club_id, student_id):
        """Remove a student from a club"""
        # Find and delete membership
        memberships = self.db.collection('memberships').where('club_id', '==', club_id).where('student_id', '==', student_id).stream()
        for membership in memberships:
            membership.reference.delete()
        
        # Remove from club_members
        club_members_ref = self.db.collection('club_members').document(club_id)
        club_members_ref.update({
            student_id: firestore.DELETE_FIELD
        })
        
        # Remove from student_memberships
        student_memberships_ref = self.db.collection('student_memberships').document(student_id)
        student_memberships_ref.update({
            club_id: firestore.DELETE_FIELD
        })
        
        # Update member count
        self.update_club_member_count(club_id)
        
        return True
    
    def get_club_members(self, club_id):
        """Get all members of a club"""
        club_members_doc = self.db.collection('club_members').document(club_id).get()
        if not club_members_doc.exists:
            return []
        
        members = []
        club_members_data = club_members_doc.to_dict()
        
        for student_id, member_info in club_members_data.items():
            student = self.get_student(student_id)
            if student:
                student.update(member_info)
                members.append(student)
        
        return members
    
    def update_club_member_count(self, club_id):
        """Update the member count for a club"""
        members = self.get_club_members(club_id)
        member_count = len(members)
        
        self.db.collection('clubs').document(club_id).update({
            'member_count': member_count
        })
        
        return member_count
