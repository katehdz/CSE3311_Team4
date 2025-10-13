import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def initialize_firebase():
    if not firebase_admin._apps:
        key_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
        if key_json:
            service_account_info = json.loads(key_json)
            cred = credentials.Certificate(service_account_info)
        else:
            path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
            cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def get_db():
    return initialize_firebase()

class FirebaseDB:
    def __init__(self):
        self.db = get_db()

    # -------------------- CLUBS --------------------
    def create_club(self, club_data):
        data = dict(club_data)
        data.setdefault("created_at", datetime.now().isoformat())
        data.setdefault("member_count", 0)
        doc_ref = self.db.collection("clubs").document()
        doc_ref.set(data)
        return doc_ref.id

    def get_all_clubs(self):
        clubs = []
        docs = self.db.collection("clubs").stream()
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            clubs.append(d)
        return clubs

    def get_club(self, club_id):
        doc = self.db.collection("clubs").document(club_id).get()
        if doc.exists:
            d = doc.to_dict()
            d["id"] = doc.id
            return d
        return None

    def update_club(self, club_id, club_data):
        self.db.collection("clubs").document(club_id).update(club_data)
        return True

    def delete_club(self, club_id):
        # Delete main club doc
        self.db.collection("clubs").document(club_id).delete()
        # Delete memberships for this club
        memberships = self.db.collection("memberships").where("club_id", "==", club_id).stream()
        batch = self.db.batch()
        for mem in memberships:
            batch.delete(mem.reference)
        batch.commit()
        # Delete denormalized club_members doc
        cm_ref = self.db.collection("club_members").document(club_id)
        if cm_ref.get().exists:
            cm_ref.delete()
        # Remove club keys from all student_memberships
        sms = self.db.collection("student_memberships").stream()
        for sdoc in sms:
            if club_id in (sdoc.to_dict() or {}):
                self.db.collection("student_memberships").document(sdoc.id).update({club_id: firestore.DELETE_FIELD})
        return True

    def search_clubs(self, query):
        if not query:
            return self.get_all_clubs()
        q = query.lower()
        clubs = self.get_all_clubs()
        result = []
        for c in clubs:
            name = (c.get("name") or "").lower()
            desc = (c.get("description") or "").lower()
            if q in name or q in desc:
                result.append(c)
        return result
    
    def delete_club(self, club_id):
        """
        Cascade delete a club:
        - Delete memberships where club_id == club_id
        - Delete club_members/{club_id}
        - Remove club_id key from student_memberships/{student_id} for affected students
        - Delete clubs/{club_id}
        - Recalculate member_count not needed for deleted club
        """
        # ensure club exists
        club_ref = self.db.collection('clubs').document(club_id)
        if not club_ref.get().exists:
            raise ValueError("Club not found")

        # collect membership docs and affected student ids
        membership_q = self.db.collection('memberships').where('club_id', '==', club_id).stream()
        membership_docs = list(membership_q)
        affected_students = {md.to_dict().get('student_id') for md in membership_docs if md.to_dict().get('student_id')}

        # Use a batch to delete membership docs and the club_members doc and the club doc
        batch = self.db.batch()
        for md in membership_docs:
            batch.delete(md.reference)

        # delete denormalized club_members doc
        club_members_ref = self.db.collection('club_members').document(club_id)
        if club_members_ref.get().exists:
            batch.delete(club_members_ref)

        # delete the club doc
        batch.delete(club_ref)

        # commit batch (deletes membership docs, club_members doc, club doc)
        batch.commit()

        # Now remove the club key from each student's student_memberships doc (one by one)
        for student_id in affected_students:
            if not student_id:
                continue
            sm_ref = self.db.collection('student_memberships').document(student_id)
            sm_snap = sm_ref.get()
            if sm_snap.exists and club_id in (sm_snap.to_dict() or {}):
                # update to delete the field
                sm_ref.update({club_id: firestore.DELETE_FIELD})

        return True

    # -------------------- STUDENTS --------------------
    def create_student(self, student_data):
        data = dict(student_data)
        if "email" in data and data["email"]:
            data["email"] = data["email"].strip().lower()
        data.setdefault("created_at", datetime.now().isoformat())
        doc_ref = self.db.collection("students").document()
        doc_ref.set(data)
        return doc_ref.id

    def get_all_students(self):
        students = []
        docs = self.db.collection("students").stream()
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            students.append(d)
        return students

    def get_student(self, student_id):
        doc = self.db.collection("students").document(student_id).get()
        if doc.exists:
            d = doc.to_dict()
            d["id"] = doc.id
            return d
        return None

    def get_student_by_email(self, email: str):
        if not email:
            return None
        docs = self.db.collection("students").where("email", "==", email).limit(1).stream()
        for d in docs:
            val = d.to_dict()
            val["id"] = d.id
            return val
        return None

    def update_student(self, student_id, data):
        if "email" in data and data["email"]:
            data["email"] = data["email"].strip().lower()
        self.db.collection("students").document(student_id).update(data)
        return True
    
    def delete_student(self, student_id: str) -> bool:
        """
        Delete a student and cascade-remove their memberships and denormalized data.

        Steps:
        - Query memberships where student_id == student_id
        - Batch-delete membership docs
        - Batch-update club_members docs to remove the student key
        - Delete student_memberships/{student_id} document (if exists)
        - Delete students/{student_id} document
        - Recalculate member_count for affected clubs (best-effort)
        """
        # confirm student exists
        student_ref = self.db.collection("students").document(student_id)
        if not student_ref.get().exists:
            raise ValueError("Student not found")

        # find membership docs for this student
        memberships_q = self.db.collection("memberships").where("student_id", "==", student_id).stream()
        membership_docs = list(memberships_q)

        # collect affected clubs
        affected_clubs = set()
        for m in membership_docs:
            md = m.to_dict()
            if md and md.get("club_id"):
                affected_clubs.add(md["club_id"])

        # prepare a batch for deletes/updates
        batch = self.db.batch()

        # delete membership docs and remove from club_members map
        for m in membership_docs:
            # delete membership doc
            batch.delete(m.reference)
        # remove student from club_members for each affected club
        for club_id in affected_clubs:
            club_members_ref = self.db.collection("club_members").document(club_id)
            # update with DELETE_FIELD
            batch.update(club_members_ref, {student_id: firestore.DELETE_FIELD})

        # delete student_memberships doc if exists
        student_memberships_ref = self.db.collection("student_memberships").document(student_id)
        batch.delete(student_memberships_ref)

        # delete student doc
        batch.delete(student_ref)

        # commit batch (may raise)
        batch.commit()

        # Recompute member_count for each affected club (best-effort)
        for club_id in affected_clubs:
            try:
                self.update_club_member_count(club_id)
            except Exception:
                # ignore individual failures but continue
                pass

        return True

    # -------------------- MEMBERSHIPS (atomic ops) --------------------
    def add_member_to_club(self, club_id, student_id, role="Member"):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Adding member {student_id} to club {club_id} with role {role}")
        
        # First check if membership already exists (outside transaction)
        existing_check = self.db.collection("memberships") \
            .where("club_id", "==", club_id) \
            .where("student_id", "==", student_id) \
            .limit(1) \
            .get()
        
        if any(True for _ in existing_check):
            logger.warning(f"Student {student_id} is already a member of club {club_id}")
            raise ValueError("Student is already a member of this club")
            
        # Check if club_members document already has this student (outside transaction)
        club_members_ref = self.db.collection("club_members").document(club_id)
        cm_snap = club_members_ref.get()
        if cm_snap.exists:
            cm = cm_snap.to_dict() or {}
            if student_id in cm:
                logger.warning(f"Student {student_id} already in club_members for {club_id}")
                raise ValueError("Student is already a member of this club")
        
        # If we get here, we can add the membership
        membership_ref = self.db.collection("memberships").document()
        real_join = datetime.now().isoformat()
        membership_data = {"club_id": club_id, "student_id": student_id, "role": role, "join_date": real_join}
        entry = {"membership_id": membership_ref.id, "role": role, "join_date": real_join}
        
        # Use batch instead of transaction to avoid read-after-write issues
        batch = self.db.batch()
        
        # Create membership document
        batch.set(membership_ref, membership_data)
        
        # Update club_members document
        if cm_snap.exists:
            batch.update(club_members_ref, {student_id: entry})
        else:
            batch.set(club_members_ref, {student_id: entry})
        
        # Update student_memberships document
        sm_ref = self.db.collection("student_memberships").document(student_id)
        batch.set(sm_ref, {club_id: entry}, merge=True)
        
        # Update club's member count
        club_ref = self.db.collection("clubs").document(club_id)
        club_snap = club_ref.get()
        current_count = 0
        if club_snap.exists:
            current_count = club_snap.to_dict().get("member_count", 0) or 0
        batch.update(club_ref, {"member_count": current_count + 1})
        
        # Commit all changes
        batch.commit()
        logger.info(f"Successfully added member {student_id} to club {club_id}")
        
        return membership_ref.id

    def remove_member_from_club(self, club_id, student_id):
        transaction = self.db.transaction()

        @firestore.transactional
        def txn_remove(transaction):
            q = self.db.collection("memberships").where("club_id", "==", club_id).where("student_id", "==", student_id).limit(1)
            docs = list(q.get(transaction=transaction))
            if not docs:
                raise ValueError("Membership not found")
            for d in docs:
                transaction.delete(d.reference)

            club_members_ref = self.db.collection("club_members").document(club_id)
            cm_snap = club_members_ref.get(transaction=transaction)
            if cm_snap.exists:
                transaction.update(club_members_ref, {student_id: firestore.DELETE_FIELD})

            sm_ref = self.db.collection("student_memberships").document(student_id)
            sm_snap = sm_ref.get(transaction=transaction)
            if sm_snap.exists:
                transaction.update(sm_ref, {club_id: firestore.DELETE_FIELD})

            club_ref = self.db.collection("clubs").document(club_id)
            club_snap = club_ref.get(transaction=transaction)
            current_count = 0
            if club_snap.exists:
                current_count = club_snap.to_dict().get("member_count", 0) or 0
            new_count = max(0, current_count - 1)
            transaction.update(club_ref, {"member_count": new_count})

        txn_remove(transaction)
        return True

    def get_club_members(self, club_id):
        """
        Return list of member dicts: id, name, email, role, join_date, membership_id
        Safely handles missing student records and None fields.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Getting members for club {club_id}")
        
        club_members_doc = self.db.collection('club_members').document(club_id).get()
        if not club_members_doc.exists:
            logger.warning(f"No club_members document for club {club_id}")
            return []

        cm = club_members_doc.to_dict() or {}
        logger.info(f"Club {club_id} has {len(cm)} members in document")
        
        members = []
        for student_id, member_info in cm.items():
            logger.info(f"Processing student {student_id}, info: {member_info}")
            student = self.get_student(student_id)
            if not student:
                logger.warning(f"Student {student_id} not found, skipping")
                # Skip if student record missing
                continue
            # Merge student data with membership info
            merged = dict(student)
            merged.update({
                'role': member_info.get('role'),
                'join_date': member_info.get('join_date'),
                'membership_id': member_info.get('membership_id')
            })
            logger.info(f"Added member {merged.get('name')} with role {merged.get('role')}")
            members.append(merged)

        # Default sort by name (safe)
        members.sort(key=lambda m: (m.get('name') or '').lower())
        logger.info(f"Returning {len(members)} members for club {club_id}")
        return members

    def update_member_role(self, club_id, student_id, new_role):
        allowed = {"Member", "Officer", "President", "Vice President", "Treasurer", "Secretary"}
        if new_role not in allowed:
            raise ValueError("Invalid role")
        transaction = self.db.transaction()

        @firestore.transactional
        def txn_update(transaction):
            q = self.db.collection("memberships").where("club_id", "==", club_id).where("student_id", "==", student_id).limit(1)
            docs = list(q.get(transaction=transaction))
            if not docs:
                raise ValueError("Membership not found")
            for d in docs:
                transaction.update(d.reference, {"role": new_role})

            club_members_ref = self.db.collection("club_members").document(club_id)
            cm_snap = club_members_ref.get(transaction=transaction)
            if not cm_snap.exists:
                raise ValueError("Denormalized club_members missing")
            transaction.update(club_members_ref, {f"{student_id}.role": new_role})

            sm_ref = self.db.collection("student_memberships").document(student_id)
            sm_snap = sm_ref.get(transaction=transaction)
            if not sm_snap.exists:
                raise ValueError("Denormalized student_memberships missing")
            transaction.update(sm_ref, {f"{club_id}.role": new_role})

        txn_update(transaction)
        return True

    def update_club_member_count(self, club_id):
        members = self.get_club_members(club_id)
        count = len(members)
        self.db.collection("clubs").document(club_id).update({"member_count": count})
        return count
    
    
    # ----- helper: all clubs as map id -> name
    def get_all_clubs_map(self):
        m = {}
        for c in self.get_all_clubs():
            m[c["id"]] = c.get("name") or ""
        return m

    # ----- students with memberships filtered by club_ids and/or role
    def get_students_with_memberships(self, club_ids=None, role=None):
        """
        Return list of students each with memberships list:
        [
          {
            id, name, email,
            memberships: [ { club_id, club_name, role, join_date } ]
          }, ...
        ]
        Filters:
          - club_ids: list of club IDs to include
          - role: membership role to include
        """
        clubs_map = self.get_all_clubs_map()
        result = []

        # stream all student_memberships docs
        sm_stream = self.db.collection("student_memberships").stream()

        for sm_doc in sm_stream:
            student_id = sm_doc.id
            sm_data = sm_doc.to_dict() or {}
            # build list of membership entries that pass filter
            entries = []
            for cid, info in sm_data.items():
                if club_ids and cid not in club_ids:
                    continue
                info_role = info.get("role")
                if role and info_role != role:
                    continue
                entries.append({
                    "club_id": cid,
                    "club_name": clubs_map.get(cid, ""),
                    "role": info_role,
                    "join_date": info.get("join_date"),
                })

            # If filters provided, include only students with at least one matching entry
            if club_ids or role:
                if not entries:
                    continue

            student = self.get_student(student_id)
            if not student:
                # if student doc missing, skip
                continue

            # If no filters were provided, include all memberships (even empty)
            if not (club_ids or role):
                # Expand all memberships
                entries = []
                for cid, info in (sm_data.items()):
                    entries.append({
                        "club_id": cid,
                        "club_name": clubs_map.get(cid, ""),
                        "role": info.get("role"),
                        "join_date": info.get("join_date"),
                    })

            result.append({
                "id": student["id"],
                "name": student.get("name"),
                "email": student.get("email"),
                "memberships": entries
            })

        # Optionally include students with no memberships when no filters:
        if not (club_ids or role):
            # add remaining students not in student_memberships
            present_ids = {s["id"] for s in result}
            for s in self.get_all_students():
                if s["id"] in present_ids:
                    continue
                result.append({
                    "id": s["id"],
                    "name": s.get("name"),
                    "email": s.get("email"),
                    "memberships": []
                })

        # Sort result by student name
        result.sort(key=lambda s: (s.get("name") or "").lower())
        return result