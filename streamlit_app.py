import requests
import time

import zipfile
import io

import streamlit as st


def split_pdf_by_bol_number(uploaded_file):

    username = st.secrets["username_abby"]
    password =st.secrets["password_abby"]

    client_id = st.secrets["CLIENT_ID"]
    client_secret =st.secrets["CLIENT_SECRET"]
    
    # get access token
    url = "https://vantage-au.abbyy.com/auth2/connect/token"
    data = {"grant_type":"password","scope":"openid permissions global.wildcard",
            "username":{username},
            "password":{password},
            "client_id":{client_id},
            "client_secret":{client_secret}}
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        get_access_token = response.json()["access_token"]
    else:
        print("Error:", response.status_code, response.text)
      
    # get transaction id  
    api_url = 'https://vantage-au.abbyy.com/api/publicapi/v1/transactions'
    data = {"skillId": "e9e6517a-7a19-4f73-b2e4-857227f904f4",
            "generateMobileInputLink": False,
            "registrationParameters": [
                            {
                                "key": "string",
                                "value": "string"
                            }
                                    ]
    }

    headers = {'accept': 'text/plain','Authorization':'Bearer '+ get_access_token}
    response = requests.post(api_url,headers=headers,json=data)
    transactionID = response.json()['transactionId']

    # upload pdf file
    api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transactionID}/files'
    headers = { 'accept': '*/*','Authorization':'Bearer '+ get_access_token}
    model = {'Model':(None, 
            '{"files": [{"index": 0,"imageProcessingOptions": {"autoCrop": "Default","autoOrientation": "Default"},"registrationParameters": [{"key": "string","value": "string"}]}]}')}
    
    file = {
        'file': (uploaded_file.name, uploaded_file.read(), 'application/pdf')
    }
    response = requests.post(api_url,headers=headers,data = model,files=file,)

    # start transactions
    api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transactionID}/start'
    response = requests.post(api_url,headers=headers,)
     
    # check if the transaction is processed
    api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transactionID}'
    response = requests.get(api_url,headers=headers,)
    status = response.json()['status']

    while status != 'Processed':
        time.sleep(5)
        response = requests.get(api_url,headers=headers,)
        status = response.json()['status']
    
    headers = { 'accept': 'application/octet-stream','Authorization':'Bearer '+ get_access_token}
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for document in response.json()['documents']:
            file_id_json = document['resultFiles'][0]['fileId']
            api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transactionID}/files/{file_id_json}/download'
            response_json = requests.get(api_url,headers=headers,)
            result = response_json.json()
            try:
                bill_of_lading = result['Fields']['Bill of Lading']
            except KeyError:
                # Handle error: if there is an issue with the field, use the default value
                print(f"Warning: 'Bill of Lading' field not found for document with fileId: {file_id_json}")
                bill_of_lading = "not bill of lading"  # Use the default value
                
            file_id_pdf = document['resultFiles'][1]['fileId']
            api_url = f'https://vantage-au.abbyy.com/api/publicapi/v1/transactions/{transactionID}/files/{file_id_pdf}/download'
            response_pdf = requests.get(api_url,headers=headers,)
            zip_file.writestr(f"{bill_of_lading}.pdf", response_pdf.content)
            
    zip_filename = uploaded_file.name.replace(".pdf", ".zip")
    # 将 ZIP 文件的内容提供给 Streamlit 用于下载
    st.download_button(
        label="Download All PDFs",
        data=zip_buffer.getvalue(),
        file_name=zip_filename,
        mime="application/zip"
    )
          
               
st.set_page_config(page_title="Split pdf file by bill of lading No", layout="wide",page_icon="icon\cobalt_logo.png") 
st.sidebar.header("Split pdf file by bill of lading No")
    
with st.sidebar.form("pdfselectForm",clear_on_submit=True):
    uploaded_file  = st.file_uploader("Choose PDF file(s)",accept_multiple_files=False, type="pdf")
    submit_button = st.form_submit_button("Split pdf file(s)")

if submit_button and uploaded_file:
    split_pdf_by_bol_number(uploaded_file)
