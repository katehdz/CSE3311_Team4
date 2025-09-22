from flask import Flask, render_template, request, redirect, url_for, flash, jsonify


members = []
if club_id:
member_ids = db.reference(f"club_members/{club_id}").get() or {}
for mid in member_ids.keys():
m = db.reference(f"memberships/{mid}").get()
if not m:
continue
if role and m.get("role") != role:
continue
s = students.get(m.get("student_id"))
if s:
members.append({
"membership_id": mid,
"student": s,
"role": m.get("role"),
"join_date": m.get("join_date"),
})


# sort
if sort == "name":
members.sort(key=lambda x: x["student"]["name"].lower())
elif sort == "role":
members.sort(key=lambda x: x["role"])


if request.headers.get("Accept") == "application/json" or request.args.get("format") == "json":
# JSON API output
return jsonify({
"club": clubs.get(club_id) if club_id else None,
"members": members,
})


return render_template("roster.html", clubs=clubs, members=members, selected_club=club_id, selected_role=role, sort=sort)




# ---- Minimal JSON APIs (optional) ----
@app.get("/api/clubs")
def api_clubs():
return jsonify(db.reference("clubs").get() or {})


@app.get("/api/students")


def api_students():
return jsonify(db.reference("students").get() or {})




if __name__ == "__main__":
app.run(debug=True)