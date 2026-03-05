import streamlit as st
from xai_sdk import Client
from xai_sdk.chat import user, system

# Ensure prompt exists in session state
if 'prompt' not in st.session_state:
    st.session_state.prompt = ""

# Ensure messages list exists for rolling chat display
if 'messages' not in st.session_state:
    st.session_state.messages = []
# Load API key from .env
API_KEY = st.secrets["GROK_API_KEY"]

# Test
client = Client(
    api_key=API_KEY,
    timeout=3600, # Override default timeout with longer timeout for reasoning models
)

st.markdown("# Welcome to the SAIL Lab!")
st.markdown("Are you ready to build democratic skills?")

# Input
# Sliders
row1 = st.columns([2.5,1])
row2 = st.columns([2.5,1])
row3 = st.columns([2.5,1])
# Define callback to update beliefs based on the new mode
def update_beliefs_text():
    new_mode = st.session_state.mode_slider
    with open("Beliefs/" + new_mode + ".txt", 'r', encoding='utf-8') as file:
        st.session_state.beliefs = file.read()

mode = row1[0].select_slider(
    'Pick a Mode:', 
    ['Left', 'Lean-Left', 'Center', 'Lean-Right', 'Right'], 
    value="Right",
    key="mode_slider",
    on_change=update_beliefs_text
)

persuasive = row2[0].slider('Pick the persuasion amount:', 0, 5)
intensity = row3[0].slider('Pick how intense the conversation is:', 0, 100, value=15)
# Session state for button toggles
if "edit_beliefs" not in st.session_state:
    st.session_state.edit_beliefs = False
# if "edit_persuasion" not in st.session_state:
#     st.session_state.edit_persuasion = False
# if "edit_intensity" not in st.session_state:
#     st.session_state.edit_intensity = False
if "edit_prompt" not in st.session_state:
    st.session_state.edit_prompt = False

# Buttons & Text Boxes
beliefs = None
if row1[1].button("Edit Beliefs"):
    st.session_state.edit_beliefs = not st.session_state.edit_beliefs
if st.session_state.edit_beliefs:
    with open("Beliefs/" + mode + ".txt", 'r', encoding='utf-8') as file:
        beliefs = file.read()
    beliefs = row1[0].text_area("Edit Beliefs", beliefs, height="content", key="beliefs")

# if row2[1].button("Edit Persuasion"):
#     st.session_state.edit_persuasion = not st.session_state.edit_persuasion
# if st.session_state.edit_persuasion:
#     row2[0].text_input("Edit Persuasion", st.session_state.prompt)

# if row3[1].button("Edit Intensity"):
#     st.session_state.edit_intensity = not st.session_state.edit_intensity
# if st.session_state.edit_intensity:
#     row3[0].text_input("Edit Intensity", st.session_state.prompt)

prompt = None
if st.button("Edit Prompt"):
    st.session_state.edit_prompt = not st.session_state.edit_prompt
if st.session_state.edit_prompt:
    with open("Prompt/expresivness.txt", 'r', encoding='utf-8') as file:
        prompt = file.read()
    prompt = st.text_area("Edit Prompt", prompt, height="content", key="edit_prompt_text")

# Play button
left, middle, right = st.columns([1.75,1,1])
play = middle.button("Play")

if play:
    # Expression amount
    if not prompt:
        with open("Prompt/expresivness.txt", 'r', encoding='utf-8') as file:
            expression = file.read()
    else:
        expression = prompt

    # Beliefs
    if not beliefs:
        inputfile = "Beliefs/" + mode + ".txt"
        with open(inputfile, 'r', encoding='utf-8') as file:
            beliefs = file.read()
    st.session_state.prompt = expression.format(starting_argument=intensity, beliefs=beliefs)

    st.write("Session Ready!")

    # Initialize conversation with system prompt both in the chat client and in local messages
    st.session_state.chat = client.chat.create(
        model="grok-4-1-fast-reasoning",
        messages=[system(st.session_state.prompt)]
    )

# Chat (only show after user hits Play)
if 'chat' in st.session_state:
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [{'role': 'assistant', 'content': "Hello."}]

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        st.session_state.chat.append(user(prompt))
        aiResponce = st.session_state.chat.sample()
        st.session_state.chat.append(aiResponce)
        response = f"Robert: {aiResponce.content}"
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})