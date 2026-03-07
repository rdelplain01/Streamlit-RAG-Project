from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
import streamlit as st

st.set_page_config(page_title="ElevenLabs Agent", layout="centered")
st.title("ElevenLabs Conversational Agent in Streamlit")

@st.cache_resource
def get_client():
    api_key = st.secrets["ELL_API_KEY"]
    if not api_key:
        st.error("ELL_API_KEY is not set in .env")
        st.stop()
    return ElevenLabs(api_key=api_key)

client = get_client()

@st.cache_resource
def get_agent_id(_client):
    try:
        from elevenlabs import ConversationalConfig
        agent = _client.conversational_ai.agents.create(
            name="Streamlit Script Agent",
            conversation_config=ConversationalConfig(
                agent={
                    "prompt": {
                        "prompt": "You are a helpful and concise assistant.",
                        "llm": "gpt-4o-mini"
                    }
                }
            )
        )
        return agent.agent_id
    except Exception as e:
        st.error(f"Failed to create Agent: {e}")
        st.stop()

agent_id = get_agent_id(client)

@st.cache_resource
def get_chat_history():
    return []

chat_history = get_chat_history()

# Initialize Streamlit Session State
if "conversation" not in st.session_state:
    st.session_state.conversation = None

def start_conversation():
    if st.session_state.conversation is None:
        try:
            # Clear history for new conversation
            chat_history.clear()
            
            st.session_state.conversation = Conversation(
                client=client,
                agent_id=agent_id,
                requires_auth=True,
                audio_interface=DefaultAudioInterface(),
                callback_agent_response=lambda text: chat_history.append({"role": "agent", "text": text}),
                callback_user_transcript=lambda text: chat_history.append({"role": "user", "text": text})
            )
            st.session_state.conversation.start_session()
        except Exception as e:
            st.error(f"Error starting conversation: {e}")
            st.session_state.conversation = None

def stop_conversation():
    if st.session_state.conversation is not None:
        try:
            st.session_state.conversation.end_session()
        except Exception as e:
            st.error(f"Error trying to end session: {e}")
        finally:
            st.session_state.conversation = None

col1, col2 = st.columns(2)

with col1:
    st.button("Start Conversation", on_click=start_conversation, disabled=st.session_state.conversation is not None)

with col2:
    st.button("Stop Conversation", on_click=stop_conversation, disabled=st.session_state.conversation is None)

if st.session_state.conversation is not None:
    st.success("🎙️ Conversation is active! Speak into your microphone.")
else:
    st.info("🔇 Conversation is stopped.")

st.divider()

col_title, col_refresh = st.columns([3, 1])
with col_title:
    st.subheader("Transcript Log")
with col_refresh:
    # Adding a refresh button allows Streamlit to quickly re-render layout 
    # to show new chat messages appended by the background thread.
    st.button("🔄 Refresh Transcript Log")

# Display transcript history
if len(chat_history) == 0:
    st.write("No messages yet.")
else:
    for msg in chat_history:
        if msg["role"] == "agent":
            st.markdown(f"**🤖 Agent:** {msg['text']}")
        else:
            st.markdown(f"**👤 You:** {msg['text']}")
