import os
from urllib.request import urlopen
import openai
import requests
from flask import Flask, request, Response, session
import re
from test_pdf_reader import doc_added, docx_added_to_database, pdf_added_to_database, ask_question, check_user, get_all_documents, delete_document, text_added_to_database, txt_added_to_database
from flask_sqlalchemy import SQLAlchemy
from newsfetch.news import newspaper
from urllib.parse import urlparse

TOKEN = '<Your telegram bot token>'
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = "super secret key"
app.config['SQLALCHEMY_DATABASE_URI'] = '<Your mysql database>'
db = SQLAlchemy(app)

# Database with table name "user_details"
class userDetails(db.Model):
    __tablename__ = "user_details"
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer)
    user_first_name = db.Column(db.String(60), index=True)
    user_create_date = db.Column(db.TIMESTAMP, default=db.func.now())
    user_entry_date = db.Column(db.TIMESTAMP, default=db.func.now())
    user_login_date = db.Column(db.TIMESTAMP)
    user_api_token = db.Column(db.String(60), index=True)
    no_of_questions = db.Column(db.Integer, default=0)
    no_of_documents = db.Column(db.Integer, default=0)
    is_user = db.Column(db.Boolean, default=False)
    is_limit_reached = db.Column(db.Boolean, default=False)
    
# For scraping content from the url
def scrap_article(url):
  news = newspaper(url)
  heading= news.headline
  body=news.article
  text_content=f'Title: {heading}\ncontent: {body}'
  return text_content,heading

# for downloading the pdf from the url
def download_pdf_from_url(url,pdf_name):
    try:
        response = requests.get(url)
        pdf_name = os.path.basename(urlparse(url).path)
        file_path = os.path.join('user_pdf', pdf_name)
        with open(file_path, 'wb') as pdf_file:
            pdf_file.write(response.content)
        print("PDF downloaded successfully!")
    except Exception as e:
        print("Error downloading PDF:", e)

# for downloading txt file from url
def download_txt_from_url(url,txt_name):
    try:
        response = requests.get(url)
        txt_name = os.path.basename(urlparse(url).path)
        file_path = os.path.join('user_pdf', txt_name)
        with open(file_path, 'wb') as txt_file:
            txt_file.write(response.content)
        print("TXT downloaded successfully!")
    except Exception as e:
        print("Error downloading PDF:", e)
        
def parse_message(message):
    txt = ""
    file_type = ""
    button_response = ""
    url_response = ''
    chat_id = ''
    pdf_name = None
    pdf_file_id = None
    file_size = ""
    first_name = ""
    txt_path = ""
    if "my_chat_member" in message:
        chat_id = message['my_chat_member']['chat']['id']
    elif 'callback_query' in message:
        chat_id = message["callback_query"]['message']['chat']['id']
        button_response = message["callback_query"]["data"]
        inline_keyboard = message["callback_query"]["message"]['reply_markup']["inline_keyboard"]
        for data in inline_keyboard:
            if data[0]["callback_data"] == button_response:
                button_response = data[0]["text"]
        
    elif "link_preview_options" in message["message"]:
        if 'is_disabled' in message['message']['link_preview_options']:
            txt_path = message['message']['text']
            print('>>>>>>',txt_path)
            chat_id = message['message']['chat']['id']
            
        else:
            url_response = message['message']['link_preview_options']['url']
            print('>>>>>',url_response)
            chat_id = message['message']['chat']['id']

        
    elif 'callback_query' not in message:
        chat_id = message['message']['chat']['id']
        if 'text' in message["message"]:
            txt = message['message']['text']
            first_name = message['message']['from']['first_name']
        if 'document' in message['message']:
            pdf_name = message['message']['document']['file_name']
            pdf_file_id = message['message']['document']['file_id']
            file_type = message['message']['document']['mime_type'] 
            file_size = message['message']['document']['file_size'] 
    
    return chat_id, txt,first_name, file_type, file_size, pdf_name, pdf_file_id, button_response, url_response, txt_path

# for downloading user uploaded pdf file
def download_pdf(file_id, pdf_name):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = requests.get(url)
    file_path = response.json()['result']['file_path']
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    response = requests.get(file_url)
    pdf_path = os.path.join('user_pdf', pdf_name)
    with open(pdf_path, 'wb') as f:
        f.write(response.content)

# for downloading user uploaded txt file
def download_txt(file_id, txt_name):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = requests.get(url)
    file_path = response.json()['result']['file_path']
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    response = requests.get(file_url)
    txt_path = os.path.join('user_pdf', txt_name)
    with open(txt_path, 'wb') as f:
        f.write(response.content)

# for extracting API key from user response
def extract_api_key(text):
    pattern = r'(?:api\s*key\s*:\s*)?(?:key\s*:\s*)?(sk-[a-zA-Z0-9]+)\b'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    else:
        return None
    
# for extracting pdf name from the url
def extract_pdf_name(url):
    match = re.search(r'/([^/]+)\.pdf$', url)
    if match:
        return match.group(1)
    else:
        return ""
    
# for extracting txt name
def extract_txt_name(text):
    match = re.search(r'/([^/]+)\.txt$', text)
    if match:
        return match.group(1)
    else:
        return ""

# for validating API key
def check_openai_api_key(api_key):
    client = openai.OpenAI(api_key=api_key)
    try:
        client.models.list()
    except openai.AuthenticationError:
        return False
    else:
        return True

# for sending response to telegram bot
def tel_send_message(chat_id, text,document_list,status = False):
    
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    if status:
        payload = {
            'chat_id': chat_id,
            'text': text,
            'reply_markup': {
                'inline_keyboard': document_list
            }
        }
    else:
        payload = {
            'chat_id': chat_id,
            'text': text
        }
    response = requests.post(url, json=payload)
    return response
        
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        api_key = ""
        document_list = ""
        response = ""
        msg = request.get_json()
        print(msg)
        chat_id, txt,first_name, file_type, file_size, pdf_name, pdf_file_id, button_response,url_response,txt_path = parse_message(msg)

        print(f"\n\n{chat_id}\n\n")
        print("text",txt)
        print('url:', url_response)
        print("Type:",type(txt))
            
        api_response=extract_api_key(txt)
        print('api_response: ', api_response)
        txt_response = extract_txt_name(txt_path)
        print('txt response',txt_response)
        
        if txt == "/start":         # if user start its conversation

            user = userDetails.query.filter_by(is_user=True).first()
            if user:
                api = user.user_api_token
                print(api)
            else:
                # adding details to database
                entry= userDetails(chat_id=chat_id, user_first_name=first_name,user_api_token="<Your Open AI key>")
                db.session.add(entry)
                db.session.commit()
            response = "Hi there! Ready to assist you. To start, just upload the PDF document you need help with. Let's get rolling!"
            tel_send_message(chat_id, response,document_list)
            
        elif txt.lower() == "hi" or txt.lower() == "hello":         # if user give response "hi" or "hello"
            id = check_user(chat_id)
            if id == 0:         # if the user is typing "hi" or "hello" without uploading the file
                response = "Hi there! Ready to assist you. To start, just upload the PDF document you need help with. Let's get rolling!"
            else:
                response = "Hello! You're welcome to ask more questions anytime."
            tel_send_message(chat_id, response,document_list)
            
        elif txt_response != '':        # if the response is the url of txt file
            user = userDetails.query.filter_by(is_user=True).first()
            if user:        # if the user provides API key 
                download_txt_from_url(txt_path, txt_response)
                try:
                    response = txt_added_to_database(txt_response, chat_id, user.user_api_token)
                except openai.RateLimitError as e:
                    response = "Your API key quota is over. Please provide another API key."
            else:           # if the user has not provided API key
                user = userDetails.query.filter_by(is_user=False, is_limit_reached=False).first()
                if user:    # check if the user has reached the user limit or not
                    download_txt_from_url(txt_path, txt_response)
                    response = txt_added_to_database(txt_response, chat_id, user.user_api_token)
                    user.no_of_documents +=1        # increment document count by 1 to the database
                    db.session.commit()
                else:
                    response = "You have reached the daily limit of today!\nYou can provide your Open AI key to access without any restriction."
            tel_send_message(chat_id, response, document_list) 
            
        elif pdf_file_id:
            user = userDetails.query.filter_by(is_user=True).first()
            if user:        # for the user who have provided the API key
                if file_type == "application/pdf":      # if the user upload pdf file
                    download_pdf(pdf_file_id, pdf_name)
                    try:
                        response = pdf_added_to_database(pdf_name,chat_id,user.user_api_token)
                    except openai.RateLimitError as e:  # if API key reached it's quota limit
                        response = "Your API key quota is over. Please provide another API key."
                        
                elif file_type == "text/plain":         # if the user upload txt file
                    download_txt(pdf_file_id, pdf_name)  
                    try:
                        response = txt_added_to_database(pdf_name, chat_id, user.user_api_token)
                    except openai.RateLimitError as e:
                        response = "Your API key quota is over. Please provide another API key."
                        
                elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':    # if the user upload docx file
                    download_pdf(pdf_file_id, pdf_name)
                    try: 
                        response=docx_added_to_database(pdf_name, chat_id, user.user_api_token)
                    except openai.RateLimitError as e:
                        response = "Your API key quota is over. Please provide another API key."
                        
                elif file_type == "application/msword":         # if the user upload doc file
                    download_pdf(pdf_file_id, pdf_name)
                    try:
                        response=doc_added(pdf_name, chat_id, user.user_api_token)
                    except openai.RateLimitError as e:
                            response = "Your API key quota is over. Please provide another API key."
                    
                else:   # for any other file format 
                    response = "Sorry for the inconvenience, but the file format you uploaded is unsupported. If you have any other format file, feel free to upload it, and I'll be happy to assist you further." 
            
            else:       # for the user who have not provided thier API key
                user = userDetails.query.filter_by(is_user=False, is_limit_reached=False).first()
                if user:
                    if file_type == "application/pdf":
                        if file_size > 1000000:   # Check if file size is greater than 1 MB
                            response = "Please upload a file that is smaller than 1 MB."
                        else:
                            download_pdf(pdf_file_id, pdf_name)
                            response = pdf_added_to_database(pdf_name,chat_id,user.user_api_token)
                            user.no_of_documents +=1        # incrementing the document number by 1 in database
                            db.session.commit()
                              
                    elif file_type == "text/plain":
                        if file_size > 1000000:  # Check if file size is greater than 1 MB
                            response = "Please upload a file that is smaller than 1 MB."
                        else:
                            download_txt(pdf_file_id, pdf_name)  
                            response = txt_added_to_database(pdf_name, chat_id, user.user_api_token)
                            user.no_of_documents +=1        # incrementing the document number by 1 in database
                            db.session.commit()
                            
                    elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                        download_pdf(pdf_file_id, pdf_name)
                        response=docx_added_to_database(pdf_name, chat_id, user.user_api_token)
                        user.no_of_documents +=1        # incrementing the document number by 1 in database
                        db.session.commit()
                        
                    elif file_type == "application/msword":
                        download_pdf(pdf_file_id, pdf_name)
                        response=doc_added(pdf_name, chat_id, user.user_api_token)
                        user.no_of_documents +=1        # incrementing the document number by 1 in database
                        db.session.commit()
                        
                    else:
                        response = "Sorry for the inconvenience, but only PDF format is supported for uploading documents. If you have a PDF file, feel free to upload it, and I'll be happy to assist you further." 
                        
                else:    # if the user reached its daily limits  
                    response = "You have reached the daily limit of today!\nYou can provide your Open AI key to access without any restriction."
            tel_send_message(chat_id, response,document_list)
            
        
        elif url_response != "":        # if the response format is url
            user = userDetails.query.filter_by(is_user=True).first()
            pdf_in_url=extract_pdf_name(url_response)
            if user:
                if pdf_in_url != '':        # if user give url of pdf
                    download_pdf_from_url(url_response,pdf_in_url)
                    try:
                        response = pdf_added_to_database(pdf_in_url,chat_id,user.user_api_token)
                    except openai.RateLimitError as e:
                        response = "Your API key quota is over. Please provide another API key."
                        
                else:
                    text_content,heading = scrap_article(url_response)      # scraping webpage to extract content
                    try:
                        response=text_added_to_database(text_content,heading, chat_id, user.user_api_token)
                    except openai.RateLimitError as e:
                        response = "Your API key quota is over. Please provide another API key"        
            else:
                user = userDetails.query.filter_by(is_user=False, is_limit_reached=False).first()
                pdf_in_url=extract_pdf_name(url_response)
                if user:
                    if pdf_in_url != '':
                        download_pdf_from_url(url_response,pdf_in_url)
                        response = pdf_added_to_database(pdf_in_url,chat_id,user.user_api_token)
                        user.no_of_documents +=1        
                        db.session.commit()
                        
                    else:
                        text_content,heading = scrap_article(url_response)      # scraping webpage to extract content
                        response=text_added_to_database(text_content,heading, chat_id, user.user_api_token)
                        user.no_of_documents +=1 
                        db.session.commit()
            
                else:
                    response = "You have reached the daily limit of today!\nYou can provide your Open AI key to access without any restriction."
            tel_send_message(chat_id, response, document_list)

        elif api_response != None:          # if user give API key in response
            if check_openai_api_key(api_response):
                response = "The API Key has been successfully added to the database. You can now provide the PDF file for further processing."
                user = userDetails.query.filter_by(chat_id=chat_id).first()
                try:
                    if user:
                        user.user_api_token = api_response
                        user.is_user=True       # updating is_user to 1 in database
                        db.session.commit()
                except:
                    response= 'Please give valid Key'
            else: 
                response= "Your API key has reached token limit!"
            tel_send_message(chat_id,response,document_list)
        
             
        elif txt.lower() == "delete":       # if user wants to delete the documents 
            document_list = get_all_documents(chat_id)
            if len(document_list) == 0:
                response = "Apologies, but it seems that no PDF files were found as they have all been deleted. If you have another PDF to upload, please proceed."
            else:
                response = "You can delete the PDF by simply clicking on it."
            tel_send_message(chat_id, response, document_list, status=True)
            
        elif button_response:
            response = "The PDF has been successfully deleted."
            print('button_response', button_response)
            delete_document(chat_id,button_response)        # calling delete function to delete the specify document
            tel_send_message(chat_id,response,document_list) 
            
        else:
            user = userDetails.query.filter_by(is_user=True).first()
            if user:
                document_list=get_all_documents(chat_id)
                if len(document_list) == 0:
                    response = "Please upload the PDF first before proceeding with any actions."
                elif txt:   # if any text then it ask to open AI for response
                    try:
                        response = ask_question(txt, chat_id,user.user_api_token)   # asking open AI for response
                    except openai.RateLimitError as e:
                        response = "Your API key quota is over. Please provide another API key."
                else:
                    response = "I'm sorry, it seems that the media you're trying to upload is not supported. Please ensure you're trying to upload a PDF file, as only PDF format is supported for document uploads."
                    
            else:
                user = userDetails.query.filter_by(is_user=False, is_limit_reached=False).first()
                if user:
                    document_list=get_all_documents(chat_id)
                    if len(document_list) == 0:
                        response = "Please upload the PDF first before proceeding with any actions."
                    elif txt:
                        response = ask_question(txt, chat_id,user.user_api_token)
                        user.no_of_questions +=1            # incrementing the question number by 1 in database
                        db.session.commit() 
                    
                    else:
                        response = "I'm sorry, it seems that the media you're trying to upload is not supported. Please ensure you're trying to upload a PDF file, as only PDF format is supported for document uploads."
                        
                else:
                    response = "You have reached the daily limit of today!\nYou can provide your Open AI key to access without any restriction."
            tel_send_message(chat_id, response,document_list)
            

        return Response('OK', status=200)
    else:
        return "<h1>Welcome!</h1>"              

if __name__ == '__main__':
   app.run(debug=True, port=8000)
