import sqlite3

DB_NAME = "marketing.db"

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

# View existing users
print("BEFORE UPDATE:")
for row in cur.execute("SELECT email, role FROM users"):
    print(row)

# Update roles (change emails as needed)
cur.execute("UPDATE users SET role = 'admin' WHERE email = 'admin@gmail.com'")
cur.execute("UPDATE users SET role = 'marketer' WHERE email = 'marketer@gmail.com'")
cur.execute("UPDATE users SET role = 'staff' WHERE email = 'staff@gmail.com'")

conn.commit()

print("\nAFTER UPDATE:")
for row in cur.execute("SELECT email, role FROM users"):
    print(row)

conn.close()

import sqlite3

conn = sqlite3.connect("marketing.db")
cur = conn.cursor()

cur.execute("SELECT name, engagement_score, preferred_channel FROM customers")
rows = cur.fetchall()

print("\nCUSTOMERS DATA:")
for row in rows:
    print(row)

conn.close()
