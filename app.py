import os
import pyodbc

from dotenv import load_dotenv
from langchain_ollama import ChatOllama


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# 2. OLLAMA / QWEN3
# ============================================================

llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0
)


# ============================================================
# 3. SQL SERVER CONNECTION
# ============================================================

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")


connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USERNAME};"
    f"PWD={SQL_PASSWORD};"
    "TrustServerCertificate=yes;"
)


# ============================================================
# 4. CONNECT TO SQL SERVER
# ============================================================

try:

    conn = pyodbc.connect(
        connection_string,
        timeout=5
    )

    print("\nSQL Server connected successfully.")

except Exception as e:

    print("\nSQL Server connection failed.")

    print(e)

    raise SystemExit


# ============================================================
# 5. DATABASE SCHEMA
# ============================================================

schema = """
Table: Employees

Columns:
EmployeeID INT
Name NVARCHAR(100)
Department NVARCHAR(100)
Salary DECIMAL(10,2)
"""


# ============================================================
# 6. GET USER QUESTION
# ============================================================

question = input(
    "\nAsk your database question: "
)


# ============================================================
# 7. PROMPT
# ============================================================

prompt = f"""
You are a SQL Server expert.

Database schema:

{schema}

Convert the following natural-language question
into ONE SQL Server SELECT query.

User question:
{question}

Rules:

- Only generate SELECT
- Do not generate INSERT
- Do not generate UPDATE
- Do not generate DELETE
- Do not generate DROP
- Do not generate ALTER
- Do not generate CREATE
- Do not generate TRUNCATE
- Return only SQL
"""


# ============================================================
# 8. CALL llama3.2:3b
# ============================================================

response = llm.invoke(prompt)


# ============================================================
# 9. EXTRACT SQL
# ============================================================

sql = response.content.strip()

sql = sql.replace("```sql", "")
sql = sql.replace("```SQL", "")
sql = sql.replace("```", "")
sql = sql.strip()


print("\n==============================")

print("Generated SQL")

print("==============================")

print(sql)


# ============================================================
# 10. BASIC READ-ONLY SAFETY CHECK
# ============================================================

sql_upper = sql.upper().strip()


dangerous_commands = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "EXEC",
    "EXECUTE",
    "MERGE"
]


if not sql_upper.startswith("SELECT"):

    print("\nERROR: Only SELECT queries are allowed.")

    conn.close()

    raise SystemExit


for command in dangerous_commands:

    if command in sql_upper:

        print(
            f"\nERROR: Dangerous SQL command detected: "
            f"{command}"
        )

        conn.close()

        raise SystemExit


# ============================================================
# 11. EXECUTE SQL
# ============================================================

try:

    cursor = conn.cursor()

    cursor.execute(sql)

    rows = cursor.fetchall()

except Exception as e:

    print("\nSQL execution failed.")

    print(e)

    conn.close()

    raise SystemExit


# ============================================================
# 12. DISPLAY RESULT
# ============================================================

print("\n==============================")

print("Result")

print("==============================")


if not rows:

    print("No records found.")

else:

    for row in rows:

        print(row)


# ============================================================
# 13. CLOSE CONNECTION
# ============================================================

cursor.close()

conn.close()

print("\nDatabase connection closed.")