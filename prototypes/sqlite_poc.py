import sqlite3
import json

connection = sqlite3.connect('prototypes/poc.db')
cursor = connection.cursor()

cursor.execute('''
   CREATE TABLE IF NOT EXISTS chunks (
               id INTEGER PRIMARY KEY,
               content TEXT,
               embedding TEXT
    )
''')
connection.commit()
print('Database and table ready.')

sample_text = 'Foundry Local runs models on your own device.'
sample_vector = [0.11, 0.22, 0.33, 0.44]

vector_as_text = json.dumps(sample_vector)

cursor.execute(
    'INSERT INTO chunks (content, embedding) VALUES (?, ?)',
    (sample_text, vector_as_text)
)
connection.commit()
print('Row inserted.')

cursor.execute('SELECT id, content, embedding FROM chunks')
rows = cursor.fetchall()

print()
print('=== ROWS IN DATABASE ===')
for row in rows:
    row_id, content, embedding_text = row
    embedding = json.loads(embedding_text)
    print(f'id={row_id} content="{content}" vector={embedding}')
print('=============================')

connection.close()
print('Connection closed. Done.')