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

OLLAMA_MODEL = "llama3.2:3b"


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
# 9. INITIALIZE llama3.2:3b
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
    "llama3.2:3b + Ollama + PyODBC + Streamlit + "
    "WhatsApp Cloud API"
)
