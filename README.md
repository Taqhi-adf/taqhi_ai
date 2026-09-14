# taqhi_ai
🤖 SQL Server AI Operations &amp; Alerting Center An enterprise-grade, local GenAI Operations Dashboard that turns natural language questions into safe SQL Server queries using Qwen3 (via Ollama), displays real-time database telemetry, and dispatches automated infrastructure health alerts via the WhatsApp Cloud API.

An industry-grade `README.md` for your GitHub repository tailored to present your project professionally for GenAI and Data Engineering roles.
Absolutely. I would keep your **Qwen3/Ollama SQL AI Agent** and **SQL Server → WhatsApp Alert** as two separate services, then bring both into one professional Streamlit dashboard.

A good industry-style structure is:

```text
SQL_WHATSAPP_AI/
│
├── app.py                    ← Streamlit dashboard
├── sql_whatsapp_alert.py     ← SQL + WhatsApp service
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

Your Streamlit application will have:

* 🟢 SQL Server connection/status
* 📱 WhatsApp configuration/status
* 🤖 Qwen3 4B natural-language → SQL
* 🔐 Read-only SQL safety validation
* 📊 Query results in a dataframe
* 📲 Send WhatsApp alert manually
* 🕐 SQL Server time/status
* 📋 Generated SQL display
* 📈 Basic system metrics
* Professional sidebar/navigation
* Secrets kept in `.env`

## 1. Replace `app.py` with this

````python
import os
from datetime import datetime

import pandas as pd
import pyodbc
import requests
import streamlit as st

from dotenv import load_dotenv
from langchain_ollama import ChatOllama


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SQL AI + WhatsApp Monitor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# 3. APPLICATION SETTINGS
# ============================================================

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_TO = os.getenv("WHATSAPP_TO")

OLLAMA_MODEL = "qwen3:4b"


# ============================================================
# 4. CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 36px;
        font-weight: 700;
        margin-bottom: 0px;
    }

    .subtitle {
        font-size: 16px;
        opacity: 0.75;
        margin-bottom: 25px;
    }

    .status-card {
        padding: 18px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 10px;
    }

    .online {
        font-weight: 700;
    }

    .section-title {
        font-size: 23px;
        font-weight: 650;
        margin-top: 15px;
        margin-bottom: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 5. SESSION STATE
# ============================================================

if "generated_sql" not in st.session_state:
    st.session_state.generated_sql = ""

if "query_result" not in st.session_state:
    st.session_state.query_result = None

if "last_server_name" not in st.session_state:
    st.session_state.last_server_name = None

if "last_database_name" not in st.session_state:
    st.session_state.last_database_name = None

if "last_server_time" not in st.session_state:
    st.session_state.last_server_time = None

if "whatsapp_response" not in st.session_state:
    st.session_state.whatsapp_response = None


# ============================================================
# 6. SQL CONNECTION
# ============================================================

def get_sql_connection():

    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USERNAME};"
        f"PWD={SQL_PASSWORD};"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(
        connection_string,
        timeout=5
    )


# ============================================================
# 7. CHECK SQL SERVER
# ============================================================

def check_sql_server():

    connection = None
    cursor = None

    try:

        connection = get_sql_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                @@SERVERNAME AS ServerName,
                DB_NAME() AS DatabaseName,
                GETDATE() AS ServerTime
            """
        )

        row = cursor.fetchone()

        return {
            "status": True,
            "server_name": row.ServerName,
            "database_name": row.DatabaseName,
            "server_time": row.ServerTime,
            "error": None,
        }

    except Exception as e:

        return {
            "status": False,
            "server_name": None,
            "database_name": None,
            "server_time": None,
            "error": str(e),
        }

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# 8. WHATSAPP MESSAGE
# ============================================================

def send_whatsapp_message(
    server_name,
    database_name,
    server_time
):

    if not WHATSAPP_ACCESS_TOKEN:
        return False, "WHATSAPP_ACCESS_TOKEN is missing."

    if not WHATSAPP_PHONE_NUMBER_ID:
        return False, "WHATSAPP_PHONE_NUMBER_ID is missing."

    if not WHATSAPP_TO:
        return False, "WHATSAPP_TO is missing."

    url = (
        "https://graph.facebook.com/"
        f"v23.0/"
        f"{WHATSAPP_PHONE_NUMBER_ID}"
        "/messages"
    )

    message = (
        "SQL SERVER ALERT\n\n"
        "SQL Server is ONLINE.\n\n"
        f"Server: {server_name}\n"
        f"Database: {database_name}\n"
        f"Time: {server_time}\n\n"
        "Status: ONLINE"
    )

    payload = {
        "messaging_product": "whatsapp",
        "to": WHATSAPP_TO,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message,
        },
    }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.ok:

            return True, response.text

        return False, response.text

    except requests.exceptions.RequestException as e:

        return False, str(e)


# ============================================================
# 9. INITIALIZE QWEN3
# ============================================================

@st.cache_resource
def get_llm():

    return ChatOllama(
        model=OLLAMA_MODEL,
        temperature=0,
    )


# ============================================================
# 10. DATABASE SCHEMA
# ============================================================

SCHEMA = """
Database: uber

Table: Employees

Columns:

EmployeeID INT
Name NVARCHAR(100)
Department NVARCHAR(100)
Salary DECIMAL(10,2)
"""


# ============================================================
# 11. GENERATE SQL
# ============================================================

def generate_sql(question):

    llm = get_llm()

    prompt = f"""
You are an expert Microsoft SQL Server engineer.

Database schema:

{SCHEMA}

Convert the user's natural-language question
into ONE valid SQL Server SELECT query.

User question:
{question}

Rules:

1. Return ONLY SQL.
2. The query must start with SELECT.
3. SELECT queries only.
4. Do not use INSERT.
5. Do not use UPDATE.
6. Do not use DELETE.
7. Do not use DROP.
8. Do not use ALTER.
9. Do not use CREATE.
10. Do not use TRUNCATE.
11. Do not use EXEC.
12. Do not use EXECUTE.
13. Do not use MERGE.
14. Do not use stored procedures.
15. Do not use multiple SQL statements.
16. Do not include markdown.
"""

    response = llm.invoke(prompt)

    sql = response.content.strip()

    sql = sql.replace("```sql", "")
    sql = sql.replace("```SQL", "")
    sql = sql.replace("```", "")

    return sql.strip()


# ============================================================
# 12. SQL SAFETY VALIDATION
# ============================================================

def validate_sql(sql):

    if not sql:
        return False, "Empty SQL query."

    sql_upper = sql.upper().strip()

    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT queries are allowed."

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
        "MERGE",
    ]

    for command in dangerous_commands:

        if command in sql_upper:

            return (
                False,
                f"Dangerous SQL command detected: {command}"
            )

    # Prevent multiple statements.
    if ";" in sql_upper.rstrip(";"):

        return (
            False,
            "Multiple SQL statements are not allowed."
        )

    return True, "SQL query passed safety validation."


# ============================================================
# 13. EXECUTE SQL
# ============================================================

def execute_sql(sql):

    connection = None

    try:

        connection = get_sql_connection()

        dataframe = pd.read_sql_query(
            sql,
            connection
        )

        return True, dataframe, None

    except Exception as e:

        return False, None, str(e)

    finally:

        if connection:
            connection.close()


# ============================================================
# 14. SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🤖 SQL AI Platform")

    st.caption(
        "SQL Server + Qwen3 + WhatsApp"
    )

    st.divider()

    st.markdown("### ⚙️ Configuration")

    st.write(
        f"**SQL Server:** `{SQL_SERVER or 'Not configured'}`"
    )

    st.write(
        f"**Database:** `{SQL_DATABASE or 'Not configured'}`"
    )

    st.write(
        f"**AI Model:** `{OLLAMA_MODEL}`"
    )

    st.divider()

    st.markdown("### 📱 WhatsApp")

    if WHATSAPP_ACCESS_TOKEN:
        st.success("Access Token: Configured")
    else:
        st.error("Access Token: Missing")

    if WHATSAPP_PHONE_NUMBER_ID:
        st.success("Phone Number ID: Configured")
    else:
        st.error("Phone Number ID: Missing")

    if WHATSAPP_TO:
        st.success("Recipient: Configured")
    else:
        st.error("Recipient: Missing")

    st.divider()

    st.caption(
        "Read-only SQL AI Assistant"
    )


# ============================================================
# 15. HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    '🤖 SQL Server AI Operations Center'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Natural Language → Qwen3 → SQL Server → Results '
    '| SQL Monitoring → WhatsApp Alerts'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# 16. TOP STATUS CARDS
# ============================================================

sql_status = check_sql_server()

col1, col2, col3, col4 = st.columns(4)


with col1:

    if sql_status["status"]:

        st.metric(
            "SQL Server",
            "ONLINE"
        )

    else:

        st.metric(
            "SQL Server",
            "OFFLINE"
        )


with col2:

    st.metric(
        "Database",
        SQL_DATABASE or "N/A"
    )


with col3:

    st.metric(
        "AI Model",
        OLLAMA_MODEL
    )


with col4:

    whatsapp_ready = (
        bool(WHATSAPP_ACCESS_TOKEN)
        and bool(WHATSAPP_PHONE_NUMBER_ID)
        and bool(WHATSAPP_TO)
    )

    st.metric(
        "WhatsApp",
        "READY" if whatsapp_ready else "NOT READY"
    )


# ============================================================
# 17. REFRESH BUTTON
# ============================================================

if st.button(
    "🔄 Refresh SQL Server Status",
    use_container_width=False
):

    st.rerun()


# ============================================================
# 18. TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(
    [
        "🤖 AI SQL Assistant",
        "📊 SQL Server Monitor",
        "📱 WhatsApp Alert",
    ]
)


# ============================================================
# TAB 1 — AI SQL ASSISTANT
# ============================================================

with tab1:

    st.markdown(
        '<div class="section-title">'
        'Natural Language SQL Assistant'
        '</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Ask a question about the Employees table. "
        "Qwen3 will generate a read-only SELECT query."
    )

    question = st.text_area(
        "Enter your database question",
        placeholder=(
            "Example: Show all employees "
            "with salary greater than 50000"
        ),
        height=120,
    )

    generate_button = st.button(
        "🚀 Generate SQL & Execute",
        type="primary",
        use_container_width=True,
    )

    if generate_button:

        if not question.strip():

            st.warning(
                "Please enter a database question."
            )

        elif not sql_status["status"]:

            st.error(
                "SQL Server is not available."
            )

        else:

            with st.spinner(
                "Qwen3 is generating SQL..."
            ):

                try:

                    sql = generate_sql(
                        question
                    )

                    st.session_state.generated_sql = sql

                except Exception as e:

                    st.error(
                        "Ollama/Qwen3 error:"
                    )

                    st.code(str(e))

                    st.stop()

            # ----------------------------------------
            # Safety validation
            # ----------------------------------------

            valid, validation_message = (
                validate_sql(sql)
            )

            if not valid:

                st.error(
                    f"SQL blocked: {validation_message}"
                )

                st.code(sql, language="sql")

            else:

                st.success(
                    validation_message
                )

                # ------------------------------------
                # Show SQL
                # ------------------------------------

                st.markdown("### Generated SQL")

                st.code(
                    sql,
                    language="sql"
                )

                # ------------------------------------
                # Execute
                # ------------------------------------

                with st.spinner(
                    "Executing query on SQL Server..."
                ):

                    success, dataframe, error = (
                        execute_sql(sql)
                    )

                if success:

                    st.session_state.query_result = dataframe

                    st.success(
                        f"Query executed successfully. "
                        f"{len(dataframe)} rows returned."
                    )

                else:

                    st.error(
                        "SQL execution failed."
                    )

                    st.code(
                        error
                    )

    # ========================================================
    # DISPLAY PREVIOUS SQL
    # ========================================================

    if st.session_state.generated_sql:

        st.markdown(
            "### 📋 Last Generated SQL"
        )

        st.code(
            st.session_state.generated_sql,
            language="sql"
        )

    # ========================================================
    # DISPLAY RESULT
    # ========================================================

    if st.session_state.query_result is not None:

        st.markdown(
            "### 📊 Query Result"
        )

        dataframe = st.session_state.query_result

        st.dataframe(
            dataframe,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# TAB 2 — SQL SERVER MONITOR
# ============================================================

with tab2:

    st.markdown(
        '<div class="section-title">'
        'SQL Server Health Monitor'
        '</div>',
        unsafe_allow_html=True,
    )

    if sql_status["status"]:

        st.success(
            "🟢 SQL Server is ONLINE"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Server",
                sql_status["server_name"]
            )

        with c2:

            st.metric(
                "Database",
                sql_status["database_name"]
            )

        with c3:

            st.metric(
                "Server Time",
                str(sql_status["server_time"])
            )

        st.divider()

        st.markdown("### Connection Details")

        details = pd.DataFrame(
            {
                "Property": [
                    "SQL Server",
                    "Database",
                    "Connection Status",
                    "Server Time",
                    "Checked At",
                ],
                "Value": [
                    sql_status["server_name"],
                    sql_status["database_name"],
                    "ONLINE",
                    str(sql_status["server_time"]),
                    str(datetime.now()),
                ],
            }
        )

        st.dataframe(
            details,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.error(
            "🔴 SQL Server is OFFLINE or unreachable."
        )

        st.code(
            sql_status["error"]
        )


# ============================================================
# TAB 3 — WHATSAPP ALERT
# ============================================================

with tab3:

    st.markdown(
        '<div class="section-title">'
        'WhatsApp Alert Center'
        '</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Send a WhatsApp notification containing "
        "the current SQL Server status."
    )

    c1, c2 = st.columns(2)

    with c1:

        if WHATSAPP_ACCESS_TOKEN:

            st.success(
                "✅ Access Token configured"
            )

        else:

            st.error(
                "❌ Access Token missing"
            )

    with c2:

        if WHATSAPP_PHONE_NUMBER_ID:

            st.success(
                "✅ Phone Number ID configured"
            )

        else:

            st.error(
                "❌ Phone Number ID missing"
            )

    st.write(
        f"Recipient: `{WHATSAPP_TO or 'Not configured'}`"
    )

    st.divider()

    if st.button(
        "📲 Send SQL Server WhatsApp Alert",
        type="primary",
        use_container_width=True,
    ):

        if not sql_status["status"]:

            st.error(
                "Cannot send alert because "
                "SQL Server is offline."
            )

        else:

            with st.spinner(
                "Sending WhatsApp message..."
            ):

                success, response = (
                    send_whatsapp_message(
                        sql_status["server_name"],
                        sql_status["database_name"],
                        sql_status["server_time"],
                    )
                )

            if success:

                st.success(
                    "WhatsApp alert sent successfully."
                )

                st.session_state.whatsapp_response = response

            else:

                st.error(
                    "WhatsApp alert failed."
                )

                st.code(
                    response
                )

    if st.session_state.whatsapp_response:

        st.markdown(
            "### WhatsApp API Response"
        )

        st.code(
            st.session_state.whatsapp_response
        )


# ============================================================
# 19. FOOTER
# ============================================================

st.divider()

st.caption(
    "SQL Server AI Operations Center | "
    "Qwen3 + Ollama + PyODBC + Streamlit + "
    "WhatsApp Cloud API"
)
````

---

# 2. Your `sql_whatsapp_alert.py`

Keep your separate alert script. It is useful for automation later.

There is one improvement I strongly recommend: change:

```python
load_dotenv()
```

to:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)
```

This makes your program reliably locate the `.env` next to the Python file.

---

# 3. Recommended `.env`

Use:

```env
SQL_SERVER=DESKTOP-611CV49
SQL_DATABASE=uber
SQL_USERNAME=sa
SQL_PASSWORD=YOUR_NEW_SQL_PASSWORD

WHATSAPP_ACCESS_TOKEN=YOUR_META_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID=YOUR_PHONE_NUMBER_ID
WHATSAPP_TO=916300084418

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=SQL-WhatsApp-Agent
```

Don't paste the actual token/password into chat.

---

# 4. Install everything

From:

```text
C:\Users\DELL\Desktop\taqhi_ai
```

run:

```powershell
.venv\Scripts\activate
```

Then:

```powershell
pip install -r requirements.txt
```

Check Ollama:

```powershell
ollama list
```

You should see:

```text
qwen3:4b
```

If not:

```powershell
ollama pull qwen3:4b
```

Then test:

```powershell
ollama run qwen3:4b
```

Type:

```text
Hello
```

If Qwen responds, exit Ollama with:

```text
/bye
```

---

# 5. Check SQL Server separately

Before Streamlit, run:

```powershell
python sql_whatsapp_alert.py
```

You want:

```text
SQL Server is ONLINE
```

If this works, your database connection is good.

---

# 6. Start Streamlit

Now run:

```powershell
streamlit run app.py
```

You should see something similar to:

```text
Local URL: http://localhost:8501
```

Open the displayed address in your browser.

---

# 7. What the application will look like

The dashboard will have:

```text
┌─────────────────────────────────────────────────────────────┐
│ 🤖 SQL Server AI Operations Center                          │
│ Natural Language → Qwen3 → SQL Server → Results             │
│                                                             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│ │ SQL      │ │ Database │ │ Qwen3    │ │ WhatsApp │        │
│ │ ONLINE   │ │ uber     │ │ qwen3:4b │ │ READY    │        │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🤖 AI SQL Assistant                                     │ │
│ │                                                         │ │
│ │ Ask your database question:                             │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Show employees with salary above 50000              │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ │                                                         │ │
│ │       [ 🚀 Generate SQL & Execute ]                     │ │
│ │                                                         │ │
│ │ Generated SQL                                            │ │
│ │ SELECT * FROM Employees WHERE Salary > 50000             │ │
│ │                                                         │ │
│ │ Query Result                                             │ │
│ │ ┌─────────┬──────────┬────────────┬─────────┐           │ │
│ │ │ ID      │ Name     │ Department │ Salary  │           │ │
│ │ ├─────────┼──────────┼────────────┼─────────┤           │ │
│ │ │ 101     │ John     │ IT         │ 60000   │           │ │
│ │ └─────────┴──────────┴────────────┴─────────┘           │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

# 8. Your three main modules

The application is now divided logically into:

### 🤖 Module 1 — AI SQL Assistant

```text
User Question
      ↓
Qwen3 4B / Ollama
      ↓
SQL Generation
      ↓
SQL Safety Validation
      ↓
SQL Server
      ↓
Pandas DataFrame
      ↓
Streamlit
```

### 🖥️ Module 2 — SQL Server Monitor

```text
Streamlit
    ↓
PyODBC
    ↓
SQL Server
    ↓
@@SERVERNAME
DB_NAME()
GETDATE()
    ↓
ONLINE/OFFLINE
```

### 📱 Module 3 — WhatsApp Alert

```text
SQL Server
    ↓
Health Check
    ↓
Python
    ↓
WhatsApp Cloud API
    ↓
WhatsApp
    ↓
📱 Recipient
```

---

# 9. One important security improvement

Your current safety check:

```python
if "DELETE" in sql_upper:
```

is useful but **not a complete SQL security boundary**. For an interview/portfolio project, I would describe it as:

> **Application-level read-only SQL guardrail**

For a genuinely production database, use a **dedicated SQL login/user with SELECT-only permissions**.

For example, the AI application should eventually connect using a database account that cannot perform:

```text
INSERT
UPDATE
DELETE
DROP
ALTER
CREATE
```

Even if Qwen somehow generates a dangerous statement, the database account itself should reject it.

That gives you **defense in depth**:

```text
              Qwen3
                ↓
       SQL generation
                ↓
      Application guardrail
                ↓
        SELECT-only DB user
                ↓
          SQL Server
```

That's much more industry-grade than relying solely on an LLM prompt.

---

# 10. One more important distinction

Your current Streamlit **WhatsApp button** sends an alert when you click:

```text
📲 Send SQL Server WhatsApp Alert
```

It does **not yet mean**:

> "Every time SQL Server Windows service starts, automatically send WhatsApp."

For that, the final production architecture should be:

```text
Windows 11
     │
     ▼
SQL Server Windows Service
     │
     │ START
     ▼
Windows Task Scheduler
     │
     ▼
Python SQL Monitor
     │
     ├── SQL Server ONLINE
     │          ↓
     │    WhatsApp Cloud API
     │          ↓
     │       📱 Alert
     │
     └── SQL Server OFFLINE
                ↓
           Retry / Log
```

**That should be your next upgrade** if your actual goal is an automatic startup alert.

Also, because your project is intended as a GenAI portfolio project, I would eventually add **LangSmith tracing, structured logging, query audit history, login/authentication, role-based access, retry logic, health checks, and Docker deployment**. Those additions would make the project much stronger for a Machine Learning/GenAI Engineer interview.


---

# 🤖 SQL Server AI Operations & Alerting Center

An enterprise-grade, local GenAI Operations Dashboard that turns natural language questions into safe SQL Server queries using **Qwen3 (via Ollama)**, displays real-time database telemetry, and dispatches automated infrastructure health alerts via the **WhatsApp Cloud API**.

---

## 🌟 Key Features

* **🤖 Natural Language to SQL (NL2SQL):** Powered by `qwen3:4b` running locally via Ollama to construct queries from plain English prompts.
* **🛡️ Application-Level Read-Only Guardrails:** Lexical AST-style validation preventing multi-statement injection and destructive DDL/DML execution (`DROP`, `DELETE`, `UPDATE`, `INSERT`, etc.).
* **📊 SQL Server Telemetry Monitoring:** Direct ODBC link monitoring active instances, current database context, server clocks, and health status.
* **📲 Automated & Manual Alerts:** Direct integration with Meta's **WhatsApp Cloud API** for infrastructure alerting.
* **🎛️ Interactive Operations Dashboard:** Full-featured Streamlit frontend with modular tab navigation, caching, and state management.

---

## 🏗️ System Architecture

```
                                  +------------------------------------+
                                  |     Streamlit Operations Center    |
                                  +-----------------+------------------+
                                                    |
         +------------------------------------------+------------------------------------------+
         |                                          |                                          |
         v                                          v                                          v
+------------------+                      +------------------+                      +------------------+
| Module 1: AI SQL |                      | Module 2: Health |                      | Module 3: Alert  |
|    Assistant     |                      |     Monitor      |                      |     Center       |
+--------+---------+                      +--------+---------+                      +--------+---------+
         |                                          |                                          |
         v                                          v                                          v
  User Prompt (NL)                           PyODBC Query                             Meta Graph API
         |                               (@@SERVERNAME, DB_NAME)                               |
         v                                          |                                          v
    Ollama LLM                                      v                                 WhatsApp End-User
    (Qwen3:4b)                              SQL Server Online                                Alert
         |                                          |
         v                                          v
 Read-Only Guardrail                           Telemetry Data
         |
         v
    SQL Execution

```

---

## 📁 Repository Structure

```text
SQL_WHATSAPP_AI/
│
├── app.py                    # Main Streamlit Dashboard Application
├── sql_whatsapp_alert.py     # Standalone CLI Script for SQL & WhatsApp Alerts
├── requirements.txt          # Python Dependencies
├── .env                      # Environment Variables Configuration
├── .gitignore                # Git Exclusions
└── README.md                 # Project Documentation

```

---

## 🚀 Quick Start Guide

### 1. Prerequisites

* **Python**: `3.10` or higher
* **Ollama**: Installed and running locally ([ollama.com](https://ollama.com))
* **MS SQL Server**: Running locally or on a accessible network host
* **ODBC Driver**: ODBC Driver 17 for SQL Server

### 2. Environment Setup

Clone the repository and set up a Python virtual environment:

```bash
git clone https://github.com/your-username/SQL_WHATSAPP_AI.git
cd SQL_WHATSAPP_AI

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

```

### 3. Ollama Model Setup

Pull the required LLM locally:

```bash
ollama pull qwen3:4b

```

### 4. Environment Variables Configuration

Create a `.env` file in the root directory:

```env
# Database Credentials
SQL_SERVER=DESKTOP-XXXXXXX
SQL_DATABASE=uber
SQL_USERNAME=sa
SQL_PASSWORD=YourStrongPassword123

# WhatsApp Cloud API Configuration
WHATSAPP_ACCESS_TOKEN=EAAG...
WHATSAPP_PHONE_NUMBER_ID=1234567890
WHATSAPP_TO=91XXXXXXXXXX

# Optional Tracing (LangChain / LangSmith)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=SQL-WhatsApp-Agent

```

---

## 💻 Running the Application

### Test Standalone Infrastructure Monitor

Run the alert script to verify SQL connectivity and WhatsApp API integration:

```bash
python sql_whatsapp_alert.py

```

### Launch the Streamlit Operations Center

```bash
streamlit run app.py

```

Open `http://localhost:8501` in your browser.

---

## 🔒 Security & Guardrails

The system implements multiple security layers to protect the database layer:

1. **Strict Prompt Constraints:** System prompts explicitly mandate read-only SQL generation (`SELECT` queries only).
2. **Deterministic Validation Engine:** Input queries pass through an application-level parser enforcing:
* Mandatory `SELECT` prefix.
* Explicit blocking of DDL/DML keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`, `MERGE`).
* Prohibition of multi-statement injection via semicolon parsing.
Here is a high-impact, professional LinkedIn post layout designed to capture the attention of recruiters and hiring managers in GenAI and Data Engineering.

---

🚀 **Built a Production-Grade GenAI Operations & Infrastructure Alerting Center**

Bridging local LLMs with enterprise relational databases and automated messaging channels!

I developed a unified **SQL Server AI Operations Center** using **Streamlit**, **LangChain**, **Ollama (Llama 3.2)**, and **Meta’s WhatsApp Cloud API**. The system translates natural language business questions into precise, execution-ready SQL queries while continuously monitoring infrastructure health.

---

### Key Technical Highlights

* **🤖 Local NL2SQL Pipeline:** Integrated `llama3.2:3b` via Ollama and `langchain_ollama` to translate complex plain-English requests into targeted T-SQL queries.
* **🛡️ Application Guardrails & Defense-in-Depth:** Engineered custom lexical parsing logic (`validate_sql`) that statically analyzes generated SQL to block multi-statement injection and restrict operations strictly to read-only `SELECT` queries (preventing destructive DDL/DML execution like `DROP`, `DELETE`, or `UPDATE`).
* **📊 Database Telemetry & Dynamic UI:** Built live status monitoring over `pyodbc` to track SQL Server connectivity, server timestamps, dynamic schema contexts, and query result execution into Pandas dataframes.
* **📱 Real-time Infrastructure Alerting:** Integrated Meta’s **WhatsApp Cloud API** (`v23.0`) via RESTful payloads to send instant diagnostic system status updates to on-call engineering channels.
* **⚡ Optimized State Management:** Utilized Streamlit’s resource caching (`@st.cache_resource`) and session states to minimize LLM re-initialization and maintain seamless app navigation.

---

### 🛠 Tech Stack

**Languages & Frameworks:** Python | Streamlit | LangChain

**AI / LLM:** Ollama (`llama3.2:3b`)

**Database & Drivers:** MS SQL Server | PyODBC | Pandas

**Integrations & Tooling:** WhatsApp Cloud API | RESTful APIs | `python-dotenv`

---

💡 *Focusing on production safety, local privacy-first LLM inference, and automated incident alerting for modern Data & AI Operations.*

#GenerativeAI #Python #DataEngineering #LangChain #Ollama #SQLServer #Streamlit #LLM #SoftwareEngineering #TechInnovation
Here is a powerful, recruiter-optimized LinkedIn post that merges the technical depth, architecture, and professional polish from your previous drafts into one compelling announcement.

---

🚀 **Project Milestone: Built an Enterprise-Grade SQL AI Operations & Infrastructure Alerting Platform**

Over the past 4 weeks, I’ve been heads-down designing, implementing, and refining a production-oriented GenAI Operations platform. My goal was to move beyond basic API wrappers and build an end-to-end operational system that bridges **Local LLMs**, **Relational Databases**, and **Automated Messaging Systems**.

Today, I’m excited to share that the **SQL Server AI Operations Center** is fully functional, tested, and ready!

---

### 💡 What I Built

An enterprise-ready Streamlit dashboard designed around three core modules:

* **🤖 AI SQL Assistant (NL2SQL):** Converts complex natural language queries into valid T-SQL using **Llama 3.2 (3B)** and **Qwen3 (4B)** via **Ollama** and **LangChain**, making database interactions effortless for non-technical users.
* **🛡️ Application-Level Read-Only Guardrails:** Built a static lexical validation parser (`validate_sql`) that enforces strict `SELECT`-only execution. It actively blocks multi-statement injection and destructive DDL/DML operations (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `TRUNCATE`, `EXEC`).
* **📊 Database Telemetry & Monitoring:** Direct `pyodbc` integration that monitors active SQL Server instances, dynamic database contexts, live server timestamps, and outputs queries directly to Pandas DataFrames.
* **📱 Infrastructure Alerting via WhatsApp:** Integrated Meta’s **WhatsApp Cloud API** (`v23.0`) via RESTful payloads to dispatch real-time system status and telemetry alerts directly to on-call engineering teams.

---

### 🏗️ System Architecture

```
User Prompt (NL) ──> Ollama (Llama 3.2 / Qwen3) ──> Read-Only Guardrail ──> SQL Server Execution
                                                                                  │
Database Telemetry ──> PyODBC Query ──> Health Check Monitor ────────────────────┤
                                                                                  ▼
WhatsApp End-User Alert <── Meta Graph API <── Alert Center <── Streamlit Operations Center

```

---

### 🧰 Technology Stack

* **Languages & Frameworks:** Python | Streamlit | LangChain
* **Generative AI:** Ollama (`llama3.2:3b` / `qwen3:4b`)
* **Database & Data:** MS SQL Server | PyODBC | Pandas
* **Integrations & Security:** WhatsApp Cloud API | REST APIs | `python-dotenv` | Lexical AST Guardrails
* **Observability (Roadmap):** LangSmith Tracing

---

### 🧠 Key Engineering Takeaways

Building this project reinforced a fundamental truth: **Developing production GenAI systems isn't just about calling an LLM—it’s about system reliability, deterministic safety layers, state management, and real-world utility.**

This project marks a significant step in my transition from SQL Database Administration toward **AI/ML & GenAI Engineering**, combining my background in database systems with modern LLM tooling.

---

### 🔮 What’s Next on the Roadmap?

* Windows Task Scheduler integration for automated service startup alerts
* LangSmith evaluation pipelines & execution audit logging
* Role-based access control (RBAC) & Docker containerization

---

💬 **I’d love to connect!** If you are a Recruiter, Hiring Manager, or AI/ML professional interested in discussing the architectural trade-offs, security guardrails, or code implementation, let’s talk!

🔗 **GitHub Repository:** [github.com/Taqhi-adf](https://www.google.com/search?q=https://github.com/Taqhi-adf)

#GenerativeAI #GenAI #MachineLearning #Python #SQLServer #LangChain #Ollama #Streamlit #WhatsAppAPI #DataScience #AIAgents #GenAIEngineer #MachineLearningEngineer #OpenToWork #MLOps


3. **Defense-in-Depth Recommendation:** Assigning a SQL user account provisioned strictly with database-level `db_datareader` privileges.
