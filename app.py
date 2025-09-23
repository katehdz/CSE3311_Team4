"""
Club House System - Flask Web Application

A comprehensive club management system built with Flask and Firebase Firestore.
This application allows users to manage student clubs, including:

Features:
- Club CRUD operations (Create, Read, Update, Delete)
- Student management
- Club membership management with roles
- Search functionality for clubs
- Responsive web interface
- RESTful API endpoints
- Real-time data synchronization with Firebase

Technology Stack:
- Backend: Flask (Python web framework)
- Database: Firebase Firestore (NoSQL document database)
- Frontend: HTML5, CSS3, JavaScript
- Authentication: Firebase Admin SDK
- Environment: Python-dotenv for configuration

API Endpoints:
- GET /api/clubs - Retrieve all clubs (with optional search)
- POST /api/clubs - Create a new club
- PUT /api/clubs/<id> - Update a club
- DELETE /api/clubs/<id> - Delete a club
- GET /api/students - Retrieve all students
- POST /api/students - Create a new student
- POST /api/clubs/<id>/members - Add member to club
- DELETE /api/clubs/<club_id>/members/<student_id> - Remove member from club

Authors: CSE3311 Team 4
Version: 2.0
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from firebase_config import FirebaseDB
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Configure Flask secret key for session management and security
# This key is used for encrypting cookies, session data, and CSRF protection
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here-change-this-in-production')

# Initialize Firebase database connection
# This creates a singleton instance for all database operations
db = FirebaseDB()

# ==================== WEB ROUTES ====================

@app.route('/')
def index():
    """
    Main homepage route displaying all clubs with optional search functionality.
    
    Query Parameters:
        search (str, optional): Search term to filter clubs by name or description
        
    Returns:
        str: Rendered HTML template with clubs data
        
    Template Variables:
        clubs (list): List of club dictionaries to display
        search_query (str): Current search query for form persistence
    """
    # Get search query from URL parameters
    search_query = request.args.get('search', '')
    
    # Fetch clubs based on search query
    if search_query:
        clubs = db.search_clubs(search_query)
    else:
        clubs = db.get_all_clubs()
    
    # Render main page with clubs and search query
    return render_template('index.html', clubs=clubs, search_query=search_query)

# ==================== API ENDPOINTS - CLUBS ====================

@app.route('/api/clubs', methods=['GET'])
def get_clubs():
    """
    API endpoint to retrieve all clubs with optional search functionality.
    
    Query Parameters:
        search (str, optional): Search term to filter clubs
        
    Returns:
        JSON response with structure:
        {
            "success": bool,
            "clubs": [
                {
                    "id": str,
                    "name": str,
                    "description": str,
                    "created_at": str (ISO format),
                    "member_count": int
                },
                ...
            ]
        }
        
    Error Response:
        {
            "success": false,
            "error": str
        }
        Status Code: 500
    """
    try:
        # Extract search query from request parameters
        search_query = request.args.get('search', '')
        
        # Fetch clubs based on search criteria
        if search_query:
            clubs = db.search_clubs(search_query)
        else:
            clubs = db.get_all_clubs()
        
        # Return successful JSON response
        return jsonify({'success': True, 'clubs': clubs})
        
    except Exception as e:
        # Handle any database or processing errors
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs', methods=['POST'])
def create_club():
    """
    API endpoint to create a new club.
    
    Request Body (JSON):
        {
            "name": str (required) - Club name
            "description": str (required) - Club description
            "category": str (optional) - Club category
            "meeting_time": str (optional) - Meeting schedule
        }
        
    Returns:
        Success Response:
        {
            "success": true,
            "club_id": str,
            "message": str
        }
        Status Code: 201
        
        Error Response:
        {
            "success": false,
            "error": str
        }
        Status Code: 400 (validation error) or 500 (server error)
    """
    try:
        # Parse JSON request body
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('name') or not data.get('description'):
            return jsonify({
                'success': False, 
                'error': 'Name and description are required'
            }), 400
        
        # Prepare club data with sanitized input
        club_data = {
            'name': data['name'].strip(),
            'description': data['description'].strip()
        }
        
        # Add optional fields if provided
        if data.get('category'):
            club_data['category'] = data['category'].strip()
        if data.get('meeting_time'):
            club_data['meeting_time'] = data['meeting_time'].strip()
        
        # Create club in database
        club_id = db.create_club(club_data)
        
        # Return success response with club ID
        return jsonify({
            'success': True, 
            'message': 'Club created successfully',
            'club_id': club_id
        })
    
    except Exception as e:
        # Handle database or processing errors
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs/<club_id>', methods=['GET'])
def get_club(club_id):
    """
    API endpoint to retrieve a specific club by ID.
    
    URL Parameters:
        club_id (str): The unique club identifier
        
    Returns:
        Success Response:
        {
            "success": true,
            "club": {
                "id": str,
                "name": str,
                "description": str,
                "created_at": str,
                "member_count": int,
                ... (other club fields)
            }
        }
        Status Code: 200
        
        Error Response:
        {
            "success": false,
            "error": "Club not found"
        }
        Status Code: 404
    """
    try:
        # Fetch club from database
        club = db.get_club(club_id)
        
        # Check if club exists
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        # Return club data
        return jsonify({'success': True, 'club': club})
    except Exception as e:
        # Handle database or processing errors
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs/<club_id>', methods=['PUT'])
def update_club(club_id):
    """
    API endpoint to update an existing club.
    
    URL Parameters:
        club_id (str): The unique club identifier
        
    Request Body (JSON):
        {
            "name": str (optional) - Updated club name
            "description": str (optional) - Updated description
            "category": str (optional) - Updated category
            "meeting_time": str (optional) - Updated meeting time
        }
        
    Returns:
        Success Response:
        {
            "success": true,
            "message": "Club updated successfully"
        }
        Status Code: 200
        
        Error Responses:
        - 400: No data provided or no valid fields to update
        - 404: Club not found
        - 500: Server error
    """
    try:
        # Parse JSON request body
        data = request.get_json()
        
        # Validate request contains data
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Verify club exists before updating
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        # Prepare update data with only provided fields
        update_data = {}
        if 'name' in data and data['name']:
            update_data['name'] = data['name'].strip()
        if 'description' in data and data['description']:
            update_data['description'] = data['description'].strip()
        if 'category' in data:
            update_data['category'] = data['category'].strip() if data['category'] else None
        if 'meeting_time' in data:
            update_data['meeting_time'] = data['meeting_time'].strip() if data['meeting_time'] else None
        
        # Ensure at least one valid field is being updated
        if not update_data:
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
        
        # Perform the update operation
        db.update_club(club_id, update_data)
        
        # Return success response
        return jsonify({
            'success': True, 
            'message': 'Club updated successfully'
        })
    
    except Exception as e:
        # Handle database or processing errors
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs/<club_id>', methods=['DELETE'])
def delete_club(club_id):
    """
    API endpoint to permanently delete a club and all associated data.
    
    URL Parameters:
        club_id (str): The unique club identifier
        
    Returns:
        Success Response:
        {
            "success": true,
            "message": "Club deleted successfully"
        }
        Status Code: 200
        
        Error Responses:
        - 404: Club not found
        - 500: Server error
        
    Warning:
        This operation is irreversible and will delete:
        - The club record
        - All membership records
        - All associated denormalized data
    """
    try:
        # Verify club exists before deletion
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        # Perform cascading delete operation
        db.delete_club(club_id)
        
        # Return success response
        return jsonify({
            'success': True, 
            'message': 'Club deleted successfully'
        })
    
    except Exception as e:
        # Handle database or processing errors
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== WEB ROUTES - CLUB MANAGEMENT ====================

@app.route('/clubs/<club_id>/roster')
def club_roster(club_id):
    """
    Web route to display club roster management page.
    
    URL Parameters:
        club_id (str): The unique club identifier
        
    Returns:
        str: Rendered HTML template for roster management
        
    Template Variables:
        club (dict): Club information
        members (list): Current club members with roles
        students (list): All students for adding new members
        
    Redirects:
        - To index page if club not found or error occurs
    """
    try:
        # Fetch club information
        club = db.get_club(club_id)
        if not club:
            flash('Club not found', 'error')
            return redirect(url_for('index'))
        
        # Get current club members and all students
        members = db.get_club_members(club_id)
        students = db.get_all_students()  # For the add member dropdown
        
        # Render roster management page
        return render_template('roster.html', club=club, members=members, students=students)
    
    except Exception as e:
        # Handle errors and redirect with flash message
        flash(f'Error loading roster: {str(e)}', 'error')
        return redirect(url_for('index'))

# ==================== API ENDPOINTS - MEMBERSHIP MANAGEMENT ====================

@app.route('/api/clubs/<club_id>/members', methods=['POST'])
def add_member_to_club(club_id):
    """
    API endpoint to add a student to a club as a member.
    
    URL Parameters:
        club_id (str): The unique club identifier
        
    Request Body (JSON):
        {
            "student_id": str (required) - Student to add as member
            "role": str (optional) - Member role, defaults to "Member"
                    Options: "Member", "Officer", "President", "Vice President",
                            "Treasurer", "Secretary"
        }
        
    Returns:
        Success Response:
        {
            "success": true,
            "message": "Member added successfully",
            "membership_id": str
        }
        Status Code: 201
        
        Error Responses:
        - 400: Missing student_id or student already a member
        - 404: Club or student not found
        - 500: Server error
    """
    try:
        # Parse request data
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('student_id'):
            return jsonify({'success': False, 'error': 'Student ID is required'}), 400
        
        student_id = data['student_id']
        role = data.get('role', 'Member')  # Default role is Member
        
        # Verify club exists
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        # Verify student exists
        student = db.get_student(student_id)
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        # Check for duplicate membership
        members = db.get_club_members(club_id)
        for member in members:
            if member['id'] == student_id:
                return jsonify({
                    'success': False, 
                    'error': 'Student is already a member of this club'
                }), 400
        
        # Add student to club with specified role
        membership_id = db.add_member_to_club(club_id, student_id, role)
        
        # Return success response with membership ID
        return jsonify({
            'success': True,
            'message': 'Member added successfully',
            'membership_id': membership_id
        })
    
    except Exception as e:
        # Handle database or processing errors
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs/<club_id>/members/<student_id>', methods=['DELETE'])
def remove_member_from_club(club_id, student_id):
    """
    API endpoint to remove a student from a club.
    
    URL Parameters:
        club_id (str): The unique club identifier
        student_id (str): The unique student identifier
        
    Returns:
        Success Response:
        {
            "success": true,
            "message": "Member removed successfully"
        }
        Status Code: 200
        
        Error Responses:
        - 404: Club, student, or membership not found
        - 500: Server error
        
    Side Effects:
        - Removes membership record
        - Updates club member count
        - Removes denormalized membership data
    """
    try:
        # Verify club exists
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        # Verify student is actually a member of this club
        members = db.get_club_members(club_id)
        is_member = False
        for member in members:
            if member['id'] == student_id:
                is_member = True
                break
        
        if not is_member:
            return jsonify({
                'success': False, 
                'error': 'Student is not a member of this club'
            }), 404
        
        # Remove student from club
        db.remove_member_from_club(club_id, student_id)
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Member removed successfully'
        })
    
    except Exception as e:
        # Handle database or processing errors
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== WEB ROUTES - STUDENT MANAGEMENT ====================

@app.route('/students')
def students():
    """
    Web route to display student management page.
    
    Returns:
        str: Rendered HTML template with all students
        
    Template Variables:
        students (list): List of all student records
        
    Redirects:
        - To index page if error occurs
    """
    try:
        # Fetch all students from database
        students = db.get_all_students()
        return render_template('students.html', students=students)
    except Exception as e:
        # Handle errors and redirect with flash message
        flash(f'Error loading students: {str(e)}', 'error')
        return redirect(url_for('index'))

# ==================== API ENDPOINTS - STUDENTS ====================

@app.route('/api/students', methods=['GET'])
def get_students():
    """
    API endpoint to retrieve all students.
    
    Returns:
        JSON response with structure:
        {
            "success": bool,
            "students": [
                {
                    "id": str,
                    "name": str,
                    "email": str,
                    "created_at": str (ISO format)
                },
                ...
            ]
        }
        
    Error Response:
        {
            "success": false,
            "error": str
        }
        Status Code: 500
    """
    try:
        # Fetch all students from database
        students = db.get_all_students()
        return jsonify({'success': True, 'students': students})
    except Exception as e:
        # Handle database or processing errors
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/students', methods=['POST'])
def create_student():
    """
    API endpoint to create a new student record.
    
    Request Body (JSON):
        {
            "name": str (required) - Student's full name
            "email": str (required) - Student's email address
            "student_id": str (optional) - Student ID number
            "major": str (optional) - Student's major
        }
        
    Returns:
        Success Response:
        {
            "success": true,
            "message": "Student created successfully",
            "student_id": str
        }
        Status Code: 201
        
        Error Response:
        {
            "success": false,
            "error": str
        }
        Status Code: 400 (validation error) or 500 (server error)
    """
    try:
        # Parse JSON request body
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('name') or not data.get('email'):
            return jsonify({
                'success': False, 
                'error': 'Name and email are required'
            }), 400
        
        # Prepare student data with sanitized input
        student_data = {
            'name': data['name'].strip(),
            'email': data['email'].strip()
        }
        
        # Add optional fields if provided
        if data.get('student_id'):
            student_data['student_id'] = data['student_id'].strip()
        if data.get('major'):
            student_data['major'] = data['major'].strip()
        
        # Create student record in database
        student_id = db.create_student(student_data)
        
        # Return success response with student ID
        return jsonify({
            'success': True,
            'message': 'Student created successfully',
            'student_id': student_id
        })
    
    except Exception as e:
        # Handle database or processing errors
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== UTILITY ENDPOINTS ====================

@app.route('/api/create-sample-data', methods=['POST'])
def create_sample_data():
    """
    API endpoint to create sample data for testing and demonstration.
    
    This endpoint populates the database with:
    - 6 sample students with university email addresses
    - 6 sample clubs with detailed descriptions
    - Random membership assignments with various roles
    
    Returns:
        Success Response:
        {
            "success": true,
            "message": str,
            "students_created": int,
            "clubs_created": int
        }
        Status Code: 200
        
        Error Response:
        {
            "success": false,
            "error": str
        }
        Status Code: 500
        
    Note:
        This is intended for development and testing purposes only.
        Should be removed or protected in production environments.
    """
    try:
        # Sample students
        students_data = [
            {'name': 'Alice Johnson', 'email': 'alice.johnson@university.edu'},
            {'name': 'Bob Smith', 'email': 'bob.smith@university.edu'},
            {'name': 'Charlie Brown', 'email': 'charlie.brown@university.edu'},
            {'name': 'Diana Prince', 'email': 'diana.prince@university.edu'},
            {'name': 'Edward Wilson', 'email': 'edward.wilson@university.edu'},
            {'name': 'Fiona Davis', 'email': 'fiona.davis@university.edu'},
        ]
        
        # Sample clubs
        clubs_data = [
            {
                'name': 'Chess Club',
                'description': 'Strategic thinking meets friendly competition. Weekly tournaments and lessons for players of all skill levels.'
            },
            {
                'name': 'Computer Science Club',
                'description': 'A community for students passionate about programming, algorithms, and technology. We organize coding competitions, tech talks, and workshops.'
            },
            {
                'name': 'Debate Society',
                'description': 'Sharpen your argumentation skills and engage in intellectual discourse on current events and philosophical topics.'
            },
            {
                'name': 'Drama Club',
                'description': 'Express yourself through theater! We produce plays, organize workshops, and welcome actors, directors, and crew members.'
            },
            {
                'name': 'Environmental Action Group',
                'description': 'Dedicated to promoting sustainability and environmental awareness on campus through events, cleanups, and advocacy.'
            },
            {
                'name': 'Literary Society',
                'description': 'Explore literature through book clubs, poetry readings, and creative writing workshops. All literature lovers welcome!'
            }
        ]
        
        # Create students
        created_students = []
        for student_data in students_data:
            student_id = db.create_student(student_data)
            created_students.append(student_id)
        
        # Create clubs
        created_clubs = []
        for club_data in clubs_data:
            club_id = db.create_club(club_data)
            created_clubs.append(club_id)
        
        # Create random membership assignments
        import random
        available_roles = ['Member', 'Officer', 'Member', 'Member', 'Secretary', 'Member']
        
        for club_id in created_clubs:
            # Assign 2-4 random students to each club
            num_members = random.randint(2, 4)
            selected_students = random.sample(created_students, num_members)
            
            for i, student_id in enumerate(selected_students):
                # Assign roles with some randomness
                role = available_roles[i] if i < len(available_roles) else 'Member'
                
                # 50% chance first member becomes President
                if i == 0 and random.random() > 0.5:
                    role = 'President'
                
                try:
                    # Add member to club with assigned role
                    db.add_member_to_club(club_id, student_id, role)
                except Exception as e:
                    # Skip if student is already in this club (shouldn't happen with random sampling)
                    pass
        
        return jsonify({
            'success': True,
            'message': f'Sample data created: {len(created_students)} students, {len(created_clubs)} clubs',
            'students_created': len(created_students),
            'clubs_created': len(created_clubs)
        })
    
    except Exception as e:
        # Handle any errors during sample data creation
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """
    Handle 404 Not Found errors.
    
    Args:
        error: The error object
        
    Returns:
        tuple: (rendered template, status code)
    """
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 Internal Server errors.
    
    Args:
        error: The error object
        
    Returns:
        tuple: (rendered template, status code)
    """
    return render_template('500.html'), 500

# ==================== APPLICATION STARTUP ====================

if __name__ == '__main__':
    """
    Application entry point.
    
    Configures and starts the Flask development server with:
    - Debug mode based on FLASK_DEBUG environment variable
    - Host: 0.0.0.0 (accessible from all network interfaces)
    - Port: 5001 (avoiding conflicts with macOS AirPlay on port 5000)
    
    Environment Variables:
        FLASK_DEBUG: Set to 'true' to enable debug mode
        FLASK_SECRET_KEY: Secret key for session management
        FIREBASE_SERVICE_ACCOUNT_PATH: Path to Firebase service account key
    """
    # Read debug mode from environment variable
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Start Flask development server
    # Note: Using port 5001 to avoid conflict with macOS AirPlay service on port 5000
    app.run(debug=debug_mode, host='0.0.0.0', port=5001)
