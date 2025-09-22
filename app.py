from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from firebase_config import FirebaseDB
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here-change-this-in-production')

# Initialize Firebase database
db = FirebaseDB()

@app.route('/')
def index():
    """Main page showing all clubs"""
    search_query = request.args.get('search', '')
    
    if search_query:
        clubs = db.search_clubs(search_query)
    else:
        clubs = db.get_all_clubs()
    
    return render_template('index.html', clubs=clubs, search_query=search_query)

@app.route('/api/clubs', methods=['GET'])
def get_clubs():
    """API endpoint to get all clubs"""
    try:
        search_query = request.args.get('search', '')
        
        if search_query:
            clubs = db.search_clubs(search_query)
        else:
            clubs = db.get_all_clubs()
        
        return jsonify({'success': True, 'clubs': clubs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs', methods=['POST'])
def create_club():
    """API endpoint to create a new club"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('description'):
            return jsonify({'success': False, 'error': 'Name and description are required'}), 400
        
        club_data = {
            'name': data['name'].strip(),
            'description': data['description'].strip()
        }
        
        club_id = db.create_club(club_data)
        
        return jsonify({
            'success': True, 
            'message': 'Club created successfully',
            'club_id': club_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs/<club_id>', methods=['GET'])
def get_club(club_id):
    """API endpoint to get a specific club"""
    try:
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        return jsonify({'success': True, 'club': club})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs/<club_id>', methods=['PUT'])
def update_club(club_id):
    """API endpoint to update a club"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Check if club exists
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        # Prepare update data
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name'].strip()
        if 'description' in data:
            update_data['description'] = data['description'].strip()
        
        if not update_data:
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
        
        db.update_club(club_id, update_data)
        
        return jsonify({
            'success': True, 
            'message': 'Club updated successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs/<club_id>', methods=['DELETE'])
def delete_club(club_id):
    """API endpoint to delete a club"""
    try:
        # Check if club exists
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        db.delete_club(club_id)
        
        return jsonify({
            'success': True, 
            'message': 'Club deleted successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clubs/<club_id>/roster')
def club_roster(club_id):
    """Page showing club roster"""
    try:
        club = db.get_club(club_id)
        if not club:
            flash('Club not found', 'error')
            return redirect(url_for('index'))
        
        members = db.get_club_members(club_id)
        students = db.get_all_students()  # For adding new members
        
        return render_template('roster.html', club=club, members=members, students=students)
    
    except Exception as e:
        flash(f'Error loading roster: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/api/clubs/<club_id>/members', methods=['POST'])
def add_member_to_club(club_id):
    """API endpoint to add a member to a club"""
    try:
        data = request.get_json()
        
        if not data or not data.get('student_id'):
            return jsonify({'success': False, 'error': 'Student ID is required'}), 400
        
        student_id = data['student_id']
        role = data.get('role', 'Member')
        
        # Check if club exists
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        # Check if student exists
        student = db.get_student(student_id)
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        # Check if student is already a member
        members = db.get_club_members(club_id)
        for member in members:
            if member['id'] == student_id:
                return jsonify({'success': False, 'error': 'Student is already a member'}), 400
        
        membership_id = db.add_member_to_club(club_id, student_id, role)
        
        return jsonify({
            'success': True,
            'message': 'Member added successfully',
            'membership_id': membership_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clubs/<club_id>/members/<student_id>', methods=['DELETE'])
def remove_member_from_club(club_id, student_id):
    """API endpoint to remove a member from a club"""
    try:
        # Check if club exists
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        
        # Check if student is a member
        members = db.get_club_members(club_id)
        is_member = False
        for member in members:
            if member['id'] == student_id:
                is_member = True
                break
        
        if not is_member:
            return jsonify({'success': False, 'error': 'Student is not a member of this club'}), 404
        
        db.remove_member_from_club(club_id, student_id)
        
        return jsonify({
            'success': True,
            'message': 'Member removed successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/students')
def students():
    """Page showing all students"""
    try:
        students = db.get_all_students()
        return render_template('students.html', students=students)
    except Exception as e:
        flash(f'Error loading students: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/api/students', methods=['GET'])
def get_students():
    """API endpoint to get all students"""
    try:
        students = db.get_all_students()
        return jsonify({'success': True, 'students': students})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/students', methods=['POST'])
def create_student():
    """API endpoint to create a new student"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('email'):
            return jsonify({'success': False, 'error': 'Name and email are required'}), 400
        
        student_data = {
            'name': data['name'].strip(),
            'email': data['email'].strip()
        }
        
        student_id = db.create_student(student_data)
        
        return jsonify({
            'success': True,
            'message': 'Student created successfully',
            'student_id': student_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.route('/api/create-sample-data', methods=['POST'])
def create_sample_data():
    """Create sample data for testing"""
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
        
        # Add some members to clubs
        import random
        roles = ['Member', 'Officer', 'Member', 'Member', 'Secretary', 'Member']
        
        for club_id in created_clubs:
            # Add 2-4 random members to each club
            num_members = random.randint(2, 4)
            selected_students = random.sample(created_students, num_members)
            
            for i, student_id in enumerate(selected_students):
                role = roles[i] if i < len(roles) else 'Member'
                if i == 0 and random.random() > 0.5:  # 50% chance first member is President
                    role = 'President'
                
                try:
                    db.add_member_to_club(club_id, student_id, role)
                except Exception as e:
                    # Student might already be in this club, skip
                    pass
        
        return jsonify({
            'success': True,
            'message': f'Sample data created: {len(created_students)} students, {len(created_clubs)} clubs',
            'students_created': len(created_students),
            'clubs_created': len(created_clubs)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
