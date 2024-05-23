from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain.chains.question_answering import load_qa_chain
from docx import Document
import os
import subprocess

# Function to initialize the embeddings model and language model (LLM)
def get_initialize(api_response):
    # Set the OpenAI API key environment variable
    os.environ['OPENAI_API_KEY'] = api_response  
    # Initialize the embeddings model
    embeddings_model = OpenAIEmbeddings()
    # Initialize the language model with specified parameters
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=api_response, max_tokens=100)
    return embeddings_model, llm

# Function to ask a question using the initialized models
def ask_question(question, chat_id, api_key):
    # Initialize models
    embeddings_model, llm = get_initialize(api_key)
    # Load the Chroma vector database with the embedding function
    vectordb = Chroma(persist_directory=str(chat_id), embedding_function=embeddings_model)
    # Get a retriever object to fetch relevant documents
    retriever = vectordb.as_retriever(search_kwargs={"k": 3})
    # Load the question-answering chain
    chain = load_qa_chain(llm, chain_type="stuff")
    # Retrieve the context documents relevant to the question
    context = retriever.get_relevant_documents(question)
    # Generate an answer based on the retrieved context and input question
    answer = (chain({
        "input_documents": context,
        "question": f"You are a question-answering bot. The user will upload the document and ask questions about the uploaded document. You need to provide an answer. If the user says thank you then thank the user in return and tell them to reach out to us when they want any help with questions. If the answer has an incomplete sentence then remove the incomplete sentence from the response and try to cover it in the previous sentence. Here is the question: {question}"
    }, return_only_outputs=True))['output_text']
    return answer

# Function to add a PDF file to the database
def pdf_added_to_database(pdf_name, chat_id, api_key):
    pdf_path = os.path.join("user_pdf", pdf_name)
    embeddings_model, llm = get_initialize(api_key)
    # Load and split the PDF document
    loader = PyPDFLoader(pdf_path, extract_images=False)
    pages = loader.load_and_split()
    # Split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=20, length_function=len, add_start_index=True)
    chunks = text_splitter.split_documents(pages)
    if not chunks:
        # Handle scanned PDFs that couldn't be processed
        pdf_response = 'Your document is scanned. Please provide a document that is not scanned.'
    else:
        __import__('pysqlite3')
        # Create a Chroma vector database from document chunks and persist it
        db = Chroma.from_documents(chunks, embedding=embeddings_model, persist_directory=str(chat_id))
        db.persist()
        pdf_response = "Your PDF has been successfully uploaded and saved! You can now ask any questions you have. Let's get started!"
    return pdf_response

# Function to add a PDF from a URL to the database
def pdf_url_to_database(pdf_name, chat_id, api_key):
    pdf_path = os.path.join("user_pdf", f"{pdf_name}.pdf")
    embeddings_model, llm = get_initialize(api_key)
    # Load and split the PDF document from URL
    loader = PyPDFLoader(pdf_path, extract_images=False)
    pages = loader.load_and_split()
    # Split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=20, length_function=len, add_start_index=True)
    chunks = text_splitter.split_documents(pages)
    if not chunks:
        # Handle scanned PDFs that couldn't be processed
        pdf_response = 'Your document is scanned. Please provide a document that is not scanned.'
    else:
        __import__('pysqlite3')
        # Create a Chroma vector database from document chunks and persist it
        db = Chroma.from_documents(chunks, embedding=embeddings_model, persist_directory=str(chat_id))
        db.persist()
        pdf_response = "Your PDF has been successfully uploaded and saved! You can now ask any questions you have. Let's get started!"
    return pdf_response

# Function to add a DOCX file to the database
def docx_added_to_database(docx_name, chat_id, api_key):
    docx_path = os.path.join("user_pdf", docx_name)
    # Load the DOCX file
    doc = Document(docx_path)
    # Extract text from all paragraphs
    text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
    
    embeddings_model, llm = get_initialize(api_key)
    
    chunk_size = 4000
    chunk_overlap = 20
    # Split text into chunks
    chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size - chunk_overlap)]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len, add_start_index=True)
    main_chunks = text_splitter.create_documents(chunks)
    
    final_chunk = []
    for chunk in main_chunks:
        chunk.metadata["source"] = docx_name
        final_chunk.append(chunk)
    
    if len(text_content) < 100:
        txt_response = 'Your file does not contain enough content! Please provide another file.'
    else:
        # Create a Chroma vector database from document chunks and persist it
        db = Chroma.from_documents(final_chunk, embedding=embeddings_model, persist_directory=str(chat_id))
        db.persist()
        txt_response = "Your DOCX file has been successfully uploaded and saved! You can now ask any questions you have."
    
    return txt_response

# Function to convert a DOC file to text
def convert_doc_to_txt(doc_name):
    if not doc_name.lower().endswith('.doc'):
        raise ValueError("The provided file is not a .doc file.")
    
    temp_txt_name = os.path.join("user_pdf", doc_name.split(".")[0] + ".txt")
    
    try:
        # Convert DOC to TXT using LibreOffice
        subprocess.run(['libreoffice', '--headless', '--convert-to', 'txt', doc_name, '--outdir', os.path.dirname(temp_txt_name)], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to convert the document: {e}")
    
    with open(temp_txt_name, 'r', encoding='utf-8') as file:
        text_content = file.read()
    
    os.remove(temp_txt_name)
    
    return text_content

# Function to add a DOC file to the database
def doc_added(doc_name, chat_id, api_key):
    doc_path = os.path.join("user_pdf", doc_name)
    
    try:
        text_content = convert_doc_to_txt(doc_path)
    except Exception as e:
        return f"Failed to convert the document: {e}"
    
    embeddings_model, llm = get_initialize(api_key)
    
    chunk_size = 4000
    chunk_overlap = 20
    # Split text into chunks
    chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size - chunk_overlap)]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len, add_start_index=True)
    main_chunks = text_splitter.create_documents(chunks)
    
    final_chunk = []
    for chunk in main_chunks:
        chunk.metadata["source"] = doc_name
        final_chunk.append(chunk)
    
    if len(text_content) < 100:
        txt_response = 'Your file does not contain enough content! Please provide another file.'
    else:
        # Create a Chroma vector database from document chunks and persist it
        db = Chroma.from_documents(final_chunk, embedding=embeddings_model, persist_directory=str(chat_id))
        db.persist()
        txt_response = "Your DOC file has been successfully uploaded and saved! You can now ask any questions you have."
    
    return txt_response

# Function to add chunks of a TXT file to the database
def txt_added_to_database(pdf_name, chat_id, api_key):
    txt_path = os.path.join("user_pdf", pdf_name)
    with open(txt_path, 'r') as file:
        text_content = file.read()
    
    embeddings_model, llm = get_initialize(api_key)
    chunk_size = 4000
    chunk_overlap = 20
    # Split text into chunks
    chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size - chunk_overlap)]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len, add_start_index=True)
    main_chunks = text_splitter.create_documents(chunks)
    
    final_chunk = []
    for chunk in main_chunks:
        chunk.metadata["source"] = pdf_name
        final_chunk.append(chunk)
    
    if len(text_content) < 100:
        txt_response = 'Your Text file does not contain enough content! Please provide another file.'
    else:
        # Create a Chroma vector database from document chunks and persist it
        db = Chroma.from_documents(final_chunk, embedding=embeddings_model, persist_directory=str(chat_id))
        db.persist()
        txt_response = "Your file has been successfully uploaded and saved! You can now ask any questions you have."
    return txt_response

# Function to add chunks of a TXT file from a URL to the database
def txt_url_to_database(pdf_name, chat_id, api_key):
    text_path = os.path.join("user_pdf", f"{pdf_name}.txt")
    with open(text_path, 'r') as file:
        text_content = file.read()
    
    embeddings_model, llm = get_initialize(api_key)
    chunk_size = 4000
    chunk_overlap = 20
    # Split text into chunks
    chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size - chunk_overlap)]
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len, add_start_index=True)
    main_chunks = text_splitter.create_documents(chunks)
    
    final_chunk = []
    for chunk in main_chunks:
        chunk.metadata["source"] = pdf_name
        final_chunk.append(chunk)
    
    if len(text_content) < 100:
        txt_response = 'Your Text file does not contain enough content! Please provide another file.'
    else:
        # Create a Chroma vector database from document chunks and persist it
        db = Chroma.from_documents(final_chunk, embedding=embeddings_model, persist_directory=str(chat_id))
        db.persist()
        txt_response = "Your file has been successfully uploaded and saved! You can now ask any questions you have."
    return txt_response


# Function to add chunks of text content from a URL to the database
def text_added_to_database(text_content, heading, chat_id, api_key):
    embeddings_model, llm = get_initialize(api_key)
    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter( 
        chunk_size=4000,
        chunk_overlap=20,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_text(text_content)
    main_chunks = text_splitter.create_documents(chunks)
    
    final_chunk = []
    for chunk in main_chunks:
        chunk.metadata["source"] = heading
        final_chunk.append(chunk)
    
    if len(text_content) < 500:
        # Handle case where the content is restricted or subscription-based
        text_response = "Your URL contains the restricted or subscription-based data. Please try another URL."
    else:
        __import__('pysqlite3')
        # Create a Chroma vector database from document chunks and persist it
        db = Chroma.from_documents(final_chunk, embedding=embeddings_model, persist_directory=str(chat_id))
        db.persist()
        text_response = "Your text content has been successfully uploaded and saved! You can now ask any questions you have. Let's get started!"
    return text_response

# Function to retrieve the API key from the database
def get_api_from_database(chat_id):
    db = Chroma(persist_directory=str(chat_id))
    api_key = ""
    metadata = db.get()["metadatas"]
    for data in metadata:
        if 'api_key' in data:
            api_key = data["api_key"]
            break
    return api_key

# Function to check if a user exists based on chat_id
def check_user(chat_id):
    db = Chroma(persist_directory=str(chat_id))
    id_count = len(db.get()["ids"])
    return id_count

# Function to get all document names according to chat_id
def get_all_documents(chat_id):
    documents = []
    documents_set = set()
    db = Chroma(persist_directory=str(chat_id))
    metadata = db.get()["metadatas"]
    for data in metadata:
        documents_set.add(data["source"])
    
    for doc in documents_set:
        if len(doc) > 60:
            # Shorten document name if it's too long
            doc_new_name = f"{doc[:45]}..."
            documents.append([{'text': doc, 'callback_data': doc_new_name}])
        else:
            documents.append([{'text': doc, 'callback_data': doc}])
    
    return documents

# Function to delete a document from the database
def delete_document(chat_id, document_name):
    db = Chroma(persist_directory=str(chat_id))
    ids_to_delete = []
    metadata = db.get()["metadatas"]
    for index, data in enumerate(metadata):
        if "source" in data and data["source"] == document_name:
            ids_to_delete.append(db.get()["ids"][index])
    
    # Delete the document by its IDs
    if ids_to_delete:
        db.delete(ids=ids_to_delete)
        db.persist()
    
    return None
