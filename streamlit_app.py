import streamlit as st
import replicate
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from io import BytesIO
import base64

# App title
st.set_page_config(page_title="Smarter LGU")

# Initialize session state
if "pdf_generated" not in st.session_state:
    st.session_state.pdf_generated = False
if "pdf_buffer" not in st.session_state:
    st.session_state.pdf_buffer = None

# Replicate Credentials
with st.sidebar:
    st.title('Generative AI for LGU Notice of Meeting')
    st.write('This chatbot is created using the open-source Llama 2 LLM model from Meta.')
    
    if 'REPLICATE_API_TOKEN' in st.secrets:
        replicate_api = st.secrets['REPLICATE_API_TOKEN']
    else:
        replicate_api = st.text_input('Enter Replicate API token:', type='password')
        if not (replicate_api.startswith('r8_') and len(replicate_api) == 40):
            st.warning('Please enter your credentials!', icon='⚠️')
        else:
            st.success('Proceed to entering your prompt message!', icon='👉')
    
    os.environ['REPLICATE_API_TOKEN'] = replicate_api

    st.subheader('Models and parameters')
    selected_model = st.selectbox('Choose a Llama2 model', ['Llama2-7B', 'Llama2-13B'], key='selected_model')
    llm = 'a16z-infra/llama7b-v2-chat:4f0a4744c7295c024a1de15e1a63c880d3da035fa1f49bfd344fe076074c8eea' if selected_model == 'Llama2-7B' else 'a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5'
    
    temperature = st.slider('temperature', min_value=0.01, max_value=1.0, value=0.1, step=0.01)
    top_p = st.slider('top_p', min_value=0.01, max_value=1.0, value=0.9, step=0.01)
    max_length = st.slider('max_length', min_value=32, max_value=128, value=120, step=8)

# Function to create PDF
def create_pdf(notice_content):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Create a centered style for the title
    centered_style = ParagraphStyle(name='CenteredStyle', parent=styles['Heading1'], alignment=TA_CENTER)

    # Add the title
    story.append(Paragraph("Notice of Meeting", centered_style))
    story.append(Spacer(1, 12))

    # Add the content
    for line in notice_content.split('\n'):
        if line.strip():
            story.append(Paragraph(line, styles['BodyText']))
            story.append(Spacer(1, 6))

    doc.build(story)
    buffer.seek(0)
    return buffer

# Function to generate agenda and letter body using Llama2
def generate_agenda_and_body(purpose, invitees, offices, date):
    prompt = f"""
    Generate a formal agenda and letter body for a notice of meeting with the following details:
    - Purpose: {purpose}
    - Invitees: {invitees}
    - Calling Office: {offices}
    - Date: {date}

    The response should include:
    1. A list of 3-5 specific agenda items related to the purpose.
    2. A formal letter body inviting the attendees, explaining the purpose, and encouraging participation.

    Format the response as follows:
    AGENDA:
    1. [Agenda item 1]
    2. [Agenda item 2]
    3. [Agenda item 3]
    ...

    LETTER BODY:
    [Full letter body here]
    """

    response = replicate.run(llm, 
                             input={"prompt": prompt,
                                    "temperature": temperature, 
                                    "top_p": top_p, 
                                    "max_length": max_length, 
                                    "repetition_penalty": 1})
    
    return ''.join(response)

# Form for user input
with st.form(key='meeting_form'):
    st.write("Please fill in the details for the meeting notice:")
    invitees = st.text_input("Who are invited to the meeting?")
    offices = st.text_input("Which office is calling the meeting?")
    date = st.date_input("What is the date of the meeting?")
    purpose = st.text_area("What is the purpose of the meeting?")
    submit_button = st.form_submit_button(label='Generate Notice')

if submit_button:
    with st.spinner("Generating meeting notice..."):
        generated_content = generate_agenda_and_body(purpose, invitees, offices, date)
        
        # Split the generated content into agenda and letter body
        agenda, letter_body = generated_content.split("LETTER BODY:")
        
        notice_of_meeting = f"""
        **Notice of Meeting**

        **To:** {invitees}

        **From:** {offices}
        
        **Date:** {date}

        Dear {invitees},

        {letter_body.strip()}

        **Agenda:**
        {agenda.replace("AGENDA:", "").strip()}

        We look forward to your participation.

        Best regards,

        [Your Name]
        [Your Position]
        [Your Contact Information]
        """

        st.session_state.pdf_buffer = create_pdf(notice_of_meeting)
        st.session_state.pdf_generated = True

    st.success("Notice of Meeting generated successfully!")

# Display PDF and download button after generation
if st.session_state.pdf_generated and st.session_state.pdf_buffer is not None:
    pdf_base64 = base64.b64encode(st.session_state.pdf_buffer.getvalue()).decode()
    
    # Add download button for PDF
    st.download_button(
        label="Download Notice of Meeting PDF",
        data=st.session_state.pdf_buffer,
        file_name="notice_of_meeting.pdf",
        mime="application/pdf"
    )

    # Display PDF in the app
    st.markdown(f'<embed src="data:application/pdf;base64,{pdf_base64}" width="700" height="1000" type="application/pdf">', unsafe_allow_html=True)

st.write("To generate a new notice, simply fill out the form again.")
