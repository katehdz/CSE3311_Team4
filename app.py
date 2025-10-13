import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv
from logger import get_logger
from firebase_config import FirebaseDB
from utils.validators import valid_email, normalize_email, validate_name, validate_role

load_dotenv()
logger = get_logger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

db = FirebaseDB()

# ---------------- WEB ROUTES ----------------
@app.route("/")
def index():
    search_query = request.args.get("search", "")
    try:
        clubs = db.search_clubs(search_query) if search_query else db.get_all_clubs()
        return render_template("index.html", clubs=clubs, search_query=search_query)
    except Exception as e:
        logger.exception("Error loading index")
        flash("Error loading clubs", "error")
        return render_template("index.html", clubs=[], search_query=search_query)

@app.route("/students")
def students():
    try:
        students = db.get_students_with_memberships()  # This gets students with their memberships info
        clubs = db.get_all_clubs()  # for filter checkboxes
        return render_template("students.html", students=students, clubs=clubs)
    except Exception as e:
        logger.exception("Error loading students")
        flash("Error loading students", "error")
        return redirect(url_for("index"))
    


@app.route("/clubs/<club_id>/roster")
def club_roster(club_id):
    try:
        club = db.get_club(club_id)
        if not club:
            flash("Club not found", "error")
            return redirect(url_for("index"))

        members = db.get_club_members(club_id)
        selected_role = request.args.get("role", "")
        selected_sort = request.args.get("sort", "")

        if selected_role:
            members = [m for m in members if m.get("role") == selected_role]

        if selected_sort == "name":
            members.sort(key=lambda m: (m.get("name") or "").lower())
        elif selected_sort == "join_date":
            members.sort(key=lambda m: m.get("join_date", ""), reverse=True)

        # Get only students that are not already members of this club
        all_students = db.get_all_students()
        member_ids = {m.get("id") for m in members}
        students = [s for s in all_students if s.get("id") not in member_ids]
        
        # Debug logging to help troubleshoot
        logger.info(f"Club {club_id} has {len(members)} members")
        for m in members[:3]:  # Log first 3 members
            logger.info(f"Member: {m.get('name')}, Role: {m.get('role')}")
        
        return render_template("roster.html", club=club, members=members, students=students,
                               selected_role=selected_role, selected_sort=selected_sort)
    except Exception as e:
        logger.exception("Error loading roster")
        flash("Error loading roster", "error")
        return redirect(url_for("index"))

# ---------------- API - CLUBS ----------------
@app.route("/api/clubs", methods=["GET"])
def api_get_clubs():
    try:
        search_query = request.args.get("search", "")
        clubs = db.search_clubs(search_query) if search_query else db.get_all_clubs()
        return jsonify({"success": True, "clubs": clubs})
    except Exception as e:
        logger.exception("Error getting clubs")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clubs", methods=["POST"])
def api_create_club():
    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        desc = (data.get("description") or "").strip()
        if not name or not desc:
            return jsonify({"success": False, "error": "Name and description required"}), 400
        if any(((c.get("name") or "").lower() == name.lower()) for c in db.get_all_clubs()):
            return jsonify({"success": False, "error": "Club name already exists"}), 400

        club_id = db.create_club({"name": name, "description": desc})
        return jsonify({"success": True, "club_id": club_id, "message": "Club created"}), 201
    except Exception as e:
        logger.exception("Error creating club")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clubs/<club_id>", methods=["GET"])
def api_get_club(club_id):
    try:
        club = db.get_club(club_id)
        if not club:
            return jsonify({"success": False, "error": "Club not found"}), 404
        return jsonify({"success": True, "club": club})
    except Exception as e:
        logger.exception("Error fetching club")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clubs/<club_id>", methods=["PUT"])
def api_update_club(club_id):
    try:
        data = request.get_json() or {}
        new_name = (data.get("name") or "").strip()
        new_desc = (data.get("description") or "").strip()
        if not new_name or not new_desc:
            return jsonify({"success": False, "error": "Name and description required"}), 400
        club = db.get_club(club_id)
        if not club:
            return jsonify({"success": False, "error": "Club not found"}), 404

        if any(c["id"] != club_id and ((c.get("name") or "").lower() == new_name.lower()) for c in db.get_all_clubs()):
            return jsonify({"success": False, "error": "Another club already uses that name"}), 400

        db.update_club(club_id, {"name": new_name, "description": new_desc})
        return jsonify({"success": True, "message": "Club updated"})
    except Exception as e:
        logger.exception("Error updating club")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clubs/<club_id>", methods=["DELETE"])
def api_delete_club(club_id):
    try:
        club = db.get_club(club_id)
        if not club:
            return jsonify({'success': False, 'error': 'Club not found'}), 404
        db.delete_club(club_id)
        return jsonify({'success': True, 'message': 'Club deleted successfully'}), 200
    except ValueError as ve:
        logger.warning("Delete club validation: %s", ve)
        return jsonify({'success': False, 'error': str(ve)}), 400
    except Exception as e:
        logger.exception("Error deleting club")
        return jsonify({'success': False, 'error': 'Server error'}), 500

# ---------------- API - MEMBERSHIPS ----------------
@app.route('/api/clubs/<club_id>/members', methods=['GET'])
def api_get_club_members(club_id):
    try:
        role = request.args.get('role', '')
        sort = request.args.get('sort', '')
        
        logger.info(f"Getting members for club {club_id}, role filter: {role}")
        
        members = db.get_club_members(club_id)
        logger.info(f"Club {club_id} has {len(members)} members initially")
        
        if role:
            members = [m for m in members if m.get('role') == role]
            logger.info(f"After role filter '{role}': {len(members)} members")
            
        if sort == 'name':
            members.sort(key=lambda m: (m.get('name') or '').lower())
        elif sort == 'join_date':
            members.sort(key=lambda m: m.get('join_date', ''), reverse=True)
        
        # Debug log first few members
        for m in members[:3]:
            logger.info(f"Member: {m.get('name')}, Role: {m.get('role')}")
            
        return jsonify({'success': True, 'members': members})
    except Exception as e:
        logger.exception("Error getting club members")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/api/clubs/<club_id>/members", methods=["POST"])
def api_add_member(club_id):
    try:
        data = request.get_json() or {}
        student_id = data.get("student_id")
        role = data.get("role")
        if not student_id:
            return jsonify({"success": False, "error": "Student ID is required"}), 400
        if not role:
            return jsonify({"success": False, "error": "Role is required"}), 400
        if not validate_role(role):
            return jsonify({"success": False, "error": "Invalid role"}), 400

        club = db.get_club(club_id)
        if not club:
            return jsonify({"success": False, "error": "Club not found"}), 404
        student = db.get_student(student_id)
        if not student:
            return jsonify({"success": False, "error": "Student not found"}), 404

        membership_id = db.add_member_to_club(club_id, student_id, role)
        return jsonify({"success": True, "membership_id": membership_id, "message": "Member added"}), 201
    except ValueError as ve:
        logger.warning("Validation error adding member: %s", ve)
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.exception("Error adding member")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clubs/<club_id>/members/<student_id>", methods=["PUT"])
def api_update_member_role(club_id, student_id):
    try:
        data = request.get_json() or {}
        new_role = (data.get("role") or "").strip()
        if not new_role:
            return jsonify({"success": False, "error": "Role is required"}), 400
        if not validate_role(new_role):
            return jsonify({"success": False, "error": "Invalid role"}), 400
        if not db.get_club(club_id):
            return jsonify({"success": False, "error": "Club not found"}), 404
        if not db.get_student(student_id):
            return jsonify({"success": False, "error": "Student not found"}), 404
        db.update_member_role(club_id, student_id, new_role)
        return jsonify({"success": True, "message": "Member role updated"})
    except ValueError as ve:
        logger.warning("Validation error updating role: %s", ve)
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.exception("Error updating role")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clubs/<club_id>/members/<student_id>", methods=["DELETE"])
def api_remove_member(club_id, student_id):
    try:
        if not db.get_club(club_id):
            return jsonify({"success": False, "error": "Club not found"}), 404
        members = db.get_club_members(club_id)
        if not any(m.get("id") == student_id for m in members):
            return jsonify({"success": False, "error": "Student is not a member of this club"}), 404
        db.remove_member_from_club(club_id, student_id)
        return jsonify({"success": True, "message": "Member removed"})
    except ValueError as ve:
        logger.warning("Validation error removing member: %s", ve)
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.exception("Error removing member")
        return jsonify({"success": False, "error": str(e)}), 500

# ---------------- API - STUDENTS ----------------
@app.route("/api/students", methods=["GET"])
def api_get_students():
    try:
        students = db.get_all_students()
        return jsonify({"success": True, "students": students})
    except Exception as e:
        logger.exception("Error getting students")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/students", methods=["POST"])
def api_create_student():
    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        email_raw = (data.get("email") or "").strip()
        if not name or not email_raw:
            return jsonify({"success": False, "error": "Name and email required"}), 400
        if not validate_name(name):
            return jsonify({"success": False, "error": "Invalid name"}), 400
        email = normalize_email(email_raw)
        if not valid_email(email):
            return jsonify({"success": False, "error": "Invalid email format. Please provide a properly formatted email address."}), 400
        if db.get_student_by_email(email):
            return jsonify({"success": False, "error": "already registered"}), 400
        sid = db.create_student({"name": name, "email": email})
        return jsonify({"success": True, "message": "Student created", "student_id": sid}), 201
    except Exception as e:
        logger.exception("Error creating student")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/students/<student_id>", methods=["PUT"])
def api_update_student(student_id):
    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        email_raw = (data.get("email") or "").strip()
        if not name or not email_raw:
            return jsonify({"success": False, "error": "Both name and email required"}), 400
        if not validate_name(name):
            return jsonify({"success": False, "error": "Invalid name"}), 400
        email = normalize_email(email_raw)
        if not valid_email(email):
            return jsonify({"success": False, "error": "Invalid email format. Please provide a properly formatted email address."}), 400
        all_students = [s for s in db.get_all_students() if s.get("id") != student_id]
        if any(((s.get("email") or "").lower() == email.lower()) for s in all_students):
            return jsonify({"success": False, "error": "Email already used"}), 400
        db.update_student(student_id, {"name": name, "email": email})
        return jsonify({"success": True, "message": "Student updated"})
    except Exception as e:
        logger.exception("Error updating student")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/students/<student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    try:
        student = db.get_student(student_id)
        if not student:
            return jsonify({"success": False, "error": "Student not found"}), 404
        db.delete_student(student_id)
        return jsonify({"success": True, "message": "Student deleted"}), 200
    except ValueError as ve:
        logger.warning("Delete student validation: %s", ve)
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.exception("Error deleting student")
        return jsonify({"success": False, "error": "Server error"}), 500

# Email availability check (for inline client check)
@app.route('/api/students/check', methods=['GET'])
def api_check_student_email():
    try:
        email_raw = (request.args.get('email') or '').strip()
        exclude_id = request.args.get('exclude_id')
        if not email_raw:
            return jsonify({'success': False, 'error': 'email required'}), 400
        email = normalize_email(email_raw)
        student = db.get_student_by_email(email)
        exists = False
        if student:
            if exclude_id and student.get('id') == exclude_id:
                exists = False
            else:
                exists = True
        return jsonify({'success': True, 'exists': exists})
    except Exception as e:
        logger.exception("Error checking student email")
        return jsonify({'success': False, 'error': 'Server error'}), 500

# ---------------- API - Students with Membership Filters ----------------
@app.route('/api/students/memberships', methods=['GET'])
def api_get_students_with_memberships():
    try:
        club_ids_raw = request.args.get('club_id', '').strip()
        role = (request.args.get('role') or '').strip()
        club_ids = None
        if club_ids_raw:
            club_ids = [cid.strip() for cid in club_ids_raw.split(',') if cid.strip()]
            logger.info(f"Filtering students by club_ids: {club_ids}")
        
        if role:
            logger.info(f"Filtering students by role: {role}")
            
        students = db.get_students_with_memberships(club_ids=club_ids, role=role if role else None)
        logger.info(f"Found {len(students)} students with memberships")
        
        # Debug log the first few students
        for s in students[:3]:
            memberships = s.get('memberships', [])
            logger.info(f"Student {s.get('name')} has {len(memberships)} memberships")
            for m in memberships[:2]:
                logger.info(f"  - Club: {m.get('club_name')}, Role: {m.get('role')}")
        
        return jsonify({'success': True, 'students': students})
    except Exception as e:
        logger.exception("Error getting students with memberships")
        return jsonify({'success': False, 'error': 'Server error'}), 500

# ------------- Error handlers -------------
@app.errorhandler(404)
def not_found(e):
    try:
        return render_template("404.html"), 404
    except Exception as ex:
        logger.warning("404 template missing: %s", ex)
        return "404 Not Found", 404

@app.errorhandler(500)
def internal_error(e):
    try:
        return render_template("500.html"), 500
    except Exception as ex:
        logger.exception("500 template missing: %s", ex)
        return "500 Internal Server Error", 500

# ------------- Run -------------
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").strip().lower() == "true"
    app.run(debug=debug_mode, host="0.0.0.0", port=int(os.getenv("PORT", 5002)))