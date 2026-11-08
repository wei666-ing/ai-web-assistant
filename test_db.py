import sqlite3

with sqlite3.connect('chat_history.db') as conn:
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT
        )
    ''')
    cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("user", "你好，测试数据库"))
    conn.commit()

    cursor.execute("SELECT * FROM messages")
    for row in cursor.fetchall():
        print(row)