import fitz
from fitz import Rect
from paddleocr import PaddleOCR
import re
from io import BytesIO
import zipfile
import streamlit as st

ocr = PaddleOCR(use_angle_cls=True, lang='en',show_log = False)

def extract_bol_number(page):
    texts = page.get_text()
    bol=""
    if len(texts)>0:
        r=page.search_for("Bill Of Lading Number:",)
        if r:
            x0=r[0][0]
            y0=r[0][1]
            x1=r[0][2]
            y1=r[0][3]
            bol = page.get_textbox(Rect(x1,y0,x1+100,y1)).strip()
        else:
            bol=""
    else:
        img =page.get_pixmap(dpi=300)
        result = ocr.ocr(img.tobytes(), cls=True,)
        if result[0] is not None:
            page_text = ' '.join([line[1][0] for line in result[0]])
            
            pattern = r'Bill Of Lading Number:\s*[^0-9]*(\d+)'
            match = re.search(pattern, page_text, re.IGNORECASE)

            if match:
                bill_of_lading_number = match.group(1)
                bol= bill_of_lading_number
            else:
                bol=""
    return bol

 
def save_pdf(bol_pages, pdf_document):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for bol_number, pages in bol_pages.items():
            new_document = fitz.open()
            for page in pages:
                new_document.insert_pdf(pdf_document, from_page=page, to_page=page, start_at=-1)
            if bol_number:
                # 使用BytesIO保存文件到内存中
                pdf_bytes = BytesIO()
                new_document.save(pdf_bytes)
                # 将BytesIO设置为读模式
                pdf_bytes.seek(0)
                # 添加到ZIP文件中
                zip_file.writestr(f"{bol_number}.pdf", pdf_bytes.getvalue())
    # 将ZIP缓冲区设置为读模式
    zip_buffer.seek(0)
    return zip_buffer


def split_pdf_by_bol_number(input_pdf):
    bol_pages = {}
    with fitz.open(stream=input_pdf.getvalue()) as pdf_document:
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            bol_number = extract_bol_number(page)
            if bol_number not in bol_pages:
                bol_pages[bol_number] = [page_num]
            else:
                bol_pages[bol_number].append(page_num)
        
        # 保存PDF文件到ZIP缓冲区
        zip_buffer = save_pdf(bol_pages, pdf_document)
        # 提供给用户下载
        st.download_button(
            label="Download ZIP",
            data=zip_buffer,
            file_name="split_pdfs.zip",
            mime="application/zip"
        )
                
st.set_page_config(page_title="Split pdf file by bill of lading No", layout="wide",page_icon="icon\cobalt_logo.png") 
st.sidebar.header("Split pdf file by bill of lading No")
    
with st.sidebar.form("pdfselectForm",clear_on_submit=True):
    uploaded_file  = st.file_uploader("Choose PDF file(s)",accept_multiple_files=False, type="pdf")
    submit_button = st.form_submit_button("Split pdf file(s)")

if submit_button and uploaded_file:
    split_pdf_by_bol_number(uploaded_file)
