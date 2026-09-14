import os
import pyodbc
import requests

from dotenv import load_dotenv


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# 2. READ SQL SERVER SETTINGS
# ============================================================

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")


# ============================================================
# 3. READ WHATSAPP SETTINGS
# ============================================================

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_TO = os.getenv("WHATSAPP_TO")


# ============================================================
# 4. CHECK REQUIRED ENVIRONMENT VARIABLES
# ============================================================

def check_environment():

    required_variables = {
        "SQL_SERVER": SQL_SERVER,
        "SQL_DATABASE": SQL_DATABASE,
        "SQL_USERNAME": SQL_USERNAME,
        "SQL_PASSWORD": SQL_PASSWORD,
        "WHATSAPP_ACCESS_TOKEN": WHATSAPP_ACCESS_TOKEN,
        "WHATSAPP_PHONE_NUMBER_ID": WHATSAPP_PHONE_NUMBER_ID,
        "WHATSAPP_TO": WHATSAPP_TO,
    }

    missing = []

    for name, value in required_variables.items():

        if not value:
            missing.append(name)

    if missing:

        print("\nERROR: Missing environment variables:")

        for variable in missing:
            print(f"  - {variable}")

        return False

    return True


# ============================================================
# 5. CREATE SQL SERVER CONNECTION
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

    connection = pyodbc.connect(
        connection_string,
        timeout=5
    )

    return connection


# ============================================================
# 6. CHECK SQL SERVER
# ============================================================

def check_sql_server():

    connection = None
    cursor = None

    try:

        print("\nChecking SQL Server connection...")

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

        server_name = row.ServerName
        database_name = row.DatabaseName
        server_time = row.ServerTime

        print("\nSQL Server is ONLINE")

        print(f"Server   : {server_name}")
        print(f"Database : {database_name}")
        print(f"Time     : {server_time}")

        return True, server_name, database_name, server_time

    except Exception as e:

        print("\nSQL Server connection FAILED")

        print("Error:")
        print(e)

        return False, None, None, None

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# 7. SEND WHATSAPP MESSAGE
# ============================================================

def send_whatsapp_message(
    server_name,
    database_name,
    server_time
):

    print("\nSending WhatsApp alert...")

    url = (
        "https://graph.facebook.com/"
        "v23.0/"
        f"{WHATSAPP_PHONE_NUMBER_ID}"
        "/messages"
    )

    message = (
        "SQL SERVER ALERT\n\n"
        "SQL Server has started successfully.\n\n"
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
            "body": message
        }
    }

    headers = {

        "Authorization":
            f"Bearer {WHATSAPP_ACCESS_TOKEN}",

        "Content-Type":
            "application/json"
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        print("\nWhatsApp API Response")
        print("----------------------------")

        print("Status Code:", response.status_code)

        print("Response:")
        print(response.text)

        if response.ok:

            print("\nWhatsApp message sent successfully.")

            return True

        else:

            print("\nWhatsApp message FAILED.")

            return False

    except requests.exceptions.RequestException as e:

        print("\nWhatsApp request failed.")

        print("Error:", e)

        return False


# ============================================================
# 8. MAIN PROGRAM
# ============================================================

def main():

    print("=" * 60)

    print("SQL SERVER ---> WHATSAPP ALERT")

    print("=" * 60)

    # ----------------------------------------
    # Check .env
    # ----------------------------------------

    if not check_environment():

        return

    # ----------------------------------------
    # Check SQL Server
    # ----------------------------------------

    status, server_name, database_name, server_time = (
        check_sql_server()
    )

    # ----------------------------------------
    # SQL Server ONLINE
    # ----------------------------------------

    if status:

        print("\nSQL Server status: ONLINE")

        # ------------------------------------
        # Send WhatsApp alert
        # ------------------------------------

        send_whatsapp_message(
            server_name,
            database_name,
            server_time
        )

    else:

        print("\nSQL Server is OFFLINE.")

        print("WhatsApp alert was not sent.")


# ============================================================
# 9. PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()