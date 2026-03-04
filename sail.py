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
st.markdown("Are you ready to build democratic skills!")

# Input
mode = st.select_slider('Pick a Mode:', ['Left', 'Lean-Left', 'Center', 'Lean-Right', 'Right'])
pursuasive = st.slider('Pick the pursuation amount:', 0, 100)
argumentative = st.slider('Pick how argumentative it is:', 0, 100)
left, middle, right = st.columns([1.75,1,1])
play = middle.button("Play")

if play:
    # Expression amount
    with open("Prompt/expresivness.txt", 'r', encoding='utf-8') as file:
        expression = file.read()

    # Beliefs
    inputfile = "Beliefs/" + mode + ".txt"
    beliefs = ""
    with open(inputfile, 'r', encoding='utf-8') as file:
        beliefs = file.read()
    st.session_state.prompt = expression.format(starting_argument=argumentative, beliefs=beliefs)

    st.write("Session Ready!")

    # Initialize conversation with system prompt both in the chat client and in local messages
    st.session_state.chat = client.chat.create(
        model="grok-4-1-fast-reasoning",
        messages=[system(st.session_state.prompt)]
    )

# Chat
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