"""
Firebase Configuration Module

This module handles all Firebase Firestore database operations for the Club House System.
It provides a centralized interface for managing clubs, students, and memberships.

Key Features:
- Firebase Admin SDK initialization
- CRUD operations for clubs and students
- Membership management with role-based permissions
- Search functionality for clubs
- Automatic member count tracking

Database Schema:
- clubs: Club information with metadata
- students: Student information
- memberships: Individual membership records
- club_members: Denormalized club membership data
- student_memberships: Denormalized student membership data
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def initialize_firebase():
    """
    Initialize Firebase Admin SDK with service account credentials.
    
    Supports two authentication methods:
    1. Service account key as JSON string (production)
    2. Service account file path (development)
    
    Returns:
        firestore.Client: Initialized Firestore client
    """
    # Prevent multiple initializations
    if not firebase_admin._apps:
        # Production: Use service account key as JSON string from environment
        if os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY'):
            import json
            service_account_info = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY'))
            cred = credentials.Certificate(service_account_info)
        else:
            # Development: Use service account file path
            service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'serviceAccountKey.json')
            cred = credentials.Certificate(service_account_path)
        
        # Initialize Firebase app with credentials
        firebase_admin.initialize_app(cred)
    
    return firestore.client()

def get_db():
    """
    Get Firestore database instance.
    
    Returns:
        firestore.Client: Firestore database client
    """
    return initialize_firebase()

class FirebaseDB:
    """
    Firebase Database Operations Handler
    
    This class provides all database operations for the Club House System,
    including CRUD operations for clubs, students, and membership management.
    
    Attributes:
        db (firestore.Client): Firestore database client instance
    """
    def __init__(self):
        """Initialize FirebaseDB with database connection."""
        self.db = get_db()
    
    # ==================== CLUB OPERATIONS ====================
    
    def create_club(self, club_data):
        """
        Create a new club in the database.
        
        Args:
            club_data (dict): Club information containing name, description, etc.
            
        Returns:
            str: The generated club document ID
            
        Side Effects:
            - Adds created_at timestamp
            - Initializes member_count to 0
        """
        from datetime import datetime
        
        # Add metadata to club data
        club_data['created_at'] = datetime.now().isoformat()
        club_data['member_count'] = 0  # Initialize with zero members
        
        # Create new document with auto-generated ID
        doc_ref = self.db.collection('clubs').document()
        doc_ref.set(club_data)
        return doc_ref.id
    
    def get_all_clubs(self):
        """
        Retrieve all clubs from the database.
        
        Returns:
            list: List of club dictionaries with 'id' field added
        """
        clubs = []
        docs = self.db.collection('clubs').stream()
        
        # Convert Firestore documents to Python dictionaries
        for doc in docs:
            club_data = doc.to_dict()
            club_data['id'] = doc.id  # Add document ID to data
            clubs.append(club_data)
            
        return clubs
    
    def get_club(self, club_id):
        """
        Retrieve a specific club by ID.
        
        Args:
            club_id (str): The club document ID
            
        Returns:
            dict|None: Club data with ID, or None if not found
        """
        doc = self.db.collection('clubs').document(club_id).get()
        
        if doc.exists:
            club_data = doc.to_dict()
            club_data['id'] = doc.id
            return club_data
        return None
    
    def update_club(self, club_id, club_data):
        """
        Update an existing club's information.
        
        Args:
            club_id (str): The club document ID
            club_data (dict): Updated club information
            
        Returns:
            bool: True if successful
        """
        doc_ref = self.db.collection('clubs').document(club_id)
        doc_ref.update(club_data)
        return True
    
    def delete_club(self, club_id):
        """
        Delete a club and all associated data.
        
        This is a cascading delete operation that removes:
        1. The club document
        2. All membership records for this club
        3. Club member denormalized data
        4. Student membership denormalized data
        
        Args:
            club_id (str): The club document ID to delete
            
        Returns:
            bool: True if successful
            
        Note:
            This operation cannot be undone. Use with caution.
        """
        # Step 1: Delete the main club document
        self.db.collection('clubs').document(club_id).delete()
        
        # Step 2: Delete all membership records for this club
        memberships = self.db.collection('memberships').where('club_id', '==', club_id).stream()
        for membership in memberships:
            membership.reference.delete()
        
        # Step 3: Delete denormalized club_members data
        if self.db.collection('club_members').document(club_id).get().exists:
            self.db.collection('club_members').document(club_id).delete()
        
        # Step 4: Remove club references from student_memberships
        student_memberships = self.db.collection('student_memberships').stream()
        for student_doc in student_memberships:
            student_data = student_doc.to_dict()
            if club_id in student_data:
                # Remove this club from the student's membership list
                self.db.collection('student_memberships').document(student_doc.id).update({
                    club_id: firestore.DELETE_FIELD
                })
        
        return True
    
    def search_clubs(self, query):
        """
        Search clubs by name or description.
        
        Performs case-insensitive search across club names and descriptions.
        
        Args:
            query (str): Search term to look for
            
        Returns:
            list: Filtered list of clubs matching the search query
            
        Note:
            Returns all clubs if query is empty or None.
            Uses client-side filtering since Firestore doesn't support
            full-text search natively.
        """
        clubs = self.get_all_clubs()
        
        # Return all clubs if no search query provided
        if not query:
            return clubs
        
        # Perform case-insensitive search
        query = query.lower()
        filtered_clubs = []
        
        for club in clubs:
            club_name = club.get('name', '').lower()
            club_description = club.get('description', '').lower()
            
            # Check if query matches name or description
            if query in club_name or query in club_description:
                filtered_clubs.append(club)
                
        return filtered_clubs
    
    # ==================== STUDENT OPERATIONS ====================
    def create_student(self, student_data):
        """
        Create a new student record.
        
        Args:
            student_data (dict): Student information (name, email, etc.)
            
        Returns:
            str: The generated student document ID
            
        Side Effects:
            - Adds created_at timestamp
        """
        from datetime import datetime
        
        # Add creation timestamp
        student_data['created_at'] = datetime.now().isoformat()
        
        # Create new document with auto-generated ID
        doc_ref = self.db.collection('students').document()
        doc_ref.set(student_data)
        return doc_ref.id
    
    def get_all_students(self):
        """
        Retrieve all students from the database.
        
        Returns:
            list: List of student dictionaries with 'id' field added
        """
        students = []
        docs = self.db.collection('students').stream()
        
        # Convert Firestore documents to Python dictionaries
        for doc in docs:
            student_data = doc.to_dict()
            student_data['id'] = doc.id  # Add document ID to data
            students.append(student_data)
            
        return students
    
    def get_student(self, student_id):
        """
        Retrieve a specific student by ID.
        
        Args:
            student_id (str): The student document ID
            
        Returns:
            dict|None: Student data with ID, or None if not found
        """
        doc = self.db.collection('students').document(student_id).get()
        
        if doc.exists:
            student_data = doc.to_dict()
            student_data['id'] = doc.id
            return student_data
        return None
    
    # ==================== MEMBERSHIP OPERATIONS ====================
    def add_member_to_club(self, club_id, student_id, role="Member"):
        """
        Add a student to a club with specified role.
        
        This creates membership records in multiple collections for efficient queries:
        1. memberships: Individual membership records
        2. club_members: Denormalized data for club-centric queries
        3. student_memberships: Denormalized data for student-centric queries
        
        Args:
            club_id (str): The club document ID
            student_id (str): The student document ID
            role (str): Member role (default: "Member")
                       Options: Member, Officer, President, Vice President, 
                               Treasurer, Secretary
            
        Returns:
            str: The generated membership document ID
            
        Side Effects:
            - Updates club member count
            - Creates denormalized data in multiple collections
        """
        from datetime import datetime
        
        # Create the main membership record
        membership_data = {
            'club_id': club_id,
            'student_id': student_id,
            'role': role,
            'join_date': datetime.now().isoformat()
        }
        
        # Store membership record with auto-generated ID
        membership_ref = self.db.collection('memberships').document()
        membership_ref.set(membership_data)
        membership_id = membership_ref.id
        
        # Prepare denormalized membership data
        club_member_data = {
            'membership_id': membership_id,
            'role': role,
            'join_date': membership_data['join_date']
        }
        
        # Update club_members collection (club-centric view)
        self.db.collection('club_members').document(club_id).set({
            student_id: club_member_data
        }, merge=True)
        
        # Update student_memberships collection (student-centric view)
        self.db.collection('student_memberships').document(student_id).set({
            club_id: club_member_data
        }, merge=True)
        
        # Update the club's member count
        self.update_club_member_count(club_id)
        
        return membership_id
    
    def remove_member_from_club(self, club_id, student_id):
        """
        Remove a student from a club.
        
        This removes membership records from all related collections:
        1. memberships: Delete the individual membership record
        2. club_members: Remove from club's member list
        3. student_memberships: Remove from student's membership list
        
        Args:
            club_id (str): The club document ID
            student_id (str): The student document ID
            
        Returns:
            bool: True if successful
            
        Side Effects:
            - Updates club member count
            - Removes denormalized data from multiple collections
        """
        # Step 1: Find and delete the main membership record
        memberships = self.db.collection('memberships').where('club_id', '==', club_id).where('student_id', '==', student_id).stream()
        for membership in memberships:
            membership.reference.delete()
        
        # Step 2: Remove from club_members denormalized data
        club_members_ref = self.db.collection('club_members').document(club_id)
        club_members_ref.update({
            student_id: firestore.DELETE_FIELD
        })
        
        # Step 3: Remove from student_memberships denormalized data
        student_memberships_ref = self.db.collection('student_memberships').document(student_id)
        student_memberships_ref.update({
            club_id: firestore.DELETE_FIELD
        })
        
        # Step 4: Update the club's member count
        self.update_club_member_count(club_id)
        
        return True
    
    def get_club_members(self, club_id):
        """
        Get all members of a specific club.
        
        Retrieves member information by combining student data with
        membership details (role, join_date) from denormalized data.
        
        Args:
            club_id (str): The club document ID
            
        Returns:
            list: List of student dictionaries enhanced with membership info
                  Each dict contains: student data + role + join_date + membership_id
                  
        Note:
            Returns empty list if club has no members or doesn't exist.
        """
        # Get denormalized club member data
        club_members_doc = self.db.collection('club_members').document(club_id).get()
        if not club_members_doc.exists:
            return []
        
        members = []
        club_members_data = club_members_doc.to_dict()
        
        # Combine student data with membership information
        for student_id, member_info in club_members_data.items():
            student = self.get_student(student_id)
            if student:
                # Merge student data with membership details
                student.update(member_info)
                members.append(student)
        
        return members
    
    def update_club_member_count(self, club_id):
        """
        Update the cached member count for a club.
        
        This maintains denormalized member count data in the clubs collection
        for efficient queries without having to count members each time.
        
        Args:
            club_id (str): The club document ID
            
        Returns:
            int: The updated member count
            
        Side Effects:
            - Updates the 'member_count' field in the club document
        """
        members = self.get_club_members(club_id)
        member_count = len(members)
        
        # Update the cached count in the club document
        self.db.collection('clubs').document(club_id).update({
            'member_count': member_count
        })
        
        return member_count
