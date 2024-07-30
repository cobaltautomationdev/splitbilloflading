import requests
import time
import zipfile
import io
import streamlit as st
import json

def get_access_token(username, password, client_id, client_secret):
    url = "https://vantage-au.abbyy.com/auth2/connect/token"
    data = {
        "grant_type": "password",
        "scope": "openid permissions global.wildcard",
        "username": username,
        "password": password,
        "client_id": client_id,
        "client_secret": client_secret
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("Error:", response.status_code, response.text)
        return None

def create_transaction(access_token):
    api_url = 'https://vantage-au.abbyy.com/api/publicapi/v1/transactions'
    data = {
        "skillId": "e9e6517a-7a19-4f73-b2e4-857227f904f4",
        "generateMobileInputLink": False,
        "registrationParameters": []
    }
    headers = {'accept': 'text/plain', 'Authorization': f'Bearer {access_token}'}
    response = requests.post(api_url, headers=headers, json=data)
    return response.json()['transactionId']

def upload_file(transaction_id, access_token, file):
    api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transaction_id}/files'
    headers = {'accept': '*/*', 'Authorization': f'Bearer {access_token}'}
    model = {'Model': (None, '{"files": [{"index": 0,"imageProcessingOptions": {"autoCrop": "Default","autoOrientation": "Default"},"registrationParameters": []}]}' )}
    file_data = {
        'file': (file.name, file.read(), 'application/pdf')
    }
    response = requests.post(api_url, headers=headers, data=model, files=file_data)
    return response

def start_transactions(transaction_id, access_token):
    api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transaction_id}/start'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.post(api_url, headers=headers)
    return response

def wait_for_processing(transaction_id, access_token):
    api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transaction_id}'
    headers = {'Authorization': f'Bearer {access_token}'}
    while True:
        response = requests.get(api_url, headers=headers)
        status = response.json()['status']
        if status == 'Processed':
            break
        time.sleep(5)

def download_processed_files(transaction_id, access_token):
    api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transaction_id}'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(api_url, headers=headers)
    documents = response.json()['documents']
    return documents

def get_bill_of_lading(result):
    try:
        return result['Fields']['Bill of Lading']
    except KeyError:
        print(f"Warning: 'Bill of Lading' field not found.")
        return "not bill of lading"

def download_file(file_id, transaction_id, access_token):
    api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transaction_id}/files/{file_id}/download'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        print("Error:", response.status_code, response.text)
        return None

def process_pdf_file(uploaded_file):
    access_token = get_access_token(st.secrets["username_abby"], st.secrets["password_abby"],
                                    st.secrets["CLIENT_ID"], st.secrets["CLIENT_SECRET"])
    if not access_token:
        st.error("Failed to get access token.")
        return

    transaction_id = create_transaction(access_token)
    if not transaction_id:
        st.error("Failed to create transaction.")
        return

    response = upload_file(transaction_id, access_token, uploaded_file)
    if response.status_code != 200:
        st.error(f"Failed to upload file: {response.status_code} - {response.text}")
        return

    start_transactions(transaction_id, access_token)

    wait_for_processing(transaction_id, access_token)

    documents = download_processed_files(transaction_id, access_token)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for document in documents:
            file_id_json = document['resultFiles'][0]['fileId']
            json_content = download_file(file_id_json, transaction_id, access_token)
            if json_content:
                result = json.loads(json_content)
                bill_of_lading = get_bill_of_lading(result)

            file_id_pdf = document['resultFiles'][1]['fileId']
            pdf_content = download_file(file_id_pdf, transaction_id, access_token)
            if pdf_content:
                zip_file.writestr(f"{bill_of_lading}.pdf", pdf_content)

    zip_buffer.seek(0)
    return zip_buffer

def process_pdf_files(uploaded_files):
    if len(uploaded_files) == 1:
        zip_filename = uploaded_files[0].name.replace(".pdf", ".zip")
        zip_buffer = process_pdf_file(uploaded_files[0])
        st.download_button(
            label=f"Download '{zip_filename}' file",
            data=zip_buffer.getvalue(),
            file_name=zip_filename,
            mime="application/zip"
        )
    else:
        zip_buffer_all = io.BytesIO()
        with zipfile.ZipFile(zip_buffer_all, 'w', zipfile.ZIP_DEFLATED) as zip_file_all:
            for i, uploaded_file in enumerate(uploaded_files):
                zip_buffer = process_pdf_file(uploaded_file)
                if zip_buffer:
                    zip_filename = uploaded_file.name.replace(".pdf", ".zip")
                    zip_file_all.writestr(zip_filename, zip_buffer.getvalue())

        zip_filename = "all_zips.zip"
        st.download_button(
            label="Download All ZIPs",
            data=zip_buffer_all.getvalue(),
            file_name=zip_filename,
            mime="application/zip"
        )


import hmac
import streamlit as st


def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False


if not check_password():
    st.stop()

st.set_page_config(page_title="Split pdf files by bill of lading No", layout="wide")
st.sidebar.header("Split pdf files by bill of lading No")

with st.sidebar.form("pdfselectForm", clear_on_submit=True):
    uploaded_files = st.file_uploader("Choose PDF files", accept_multiple_files=True, type="pdf")
    submit_button = st.form_submit_button("Split pdf files")

if submit_button and uploaded_files:
    process_pdf_files(uploaded_files)