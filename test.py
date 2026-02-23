import asyncio
from xai_sdk import AsyncClient
from xai_sdk.chat import system, user, assistant

async def main():
    # The client automatically picks up the XAI_API_KEY environment variable
    client = AsyncClient() 
    
    # Create a chat session with an initial system prompt
    chat = client.chat.create(
        model="grok-3", # You can use other models like "grok-4" or "grok-4-1-fast-reasoning"
        messages=[system("You are a helpful and friendly assistant.")]
    )

    print("Welcome to the simple xAI Chatbot! Type 'exit' to end the conversation.")

    while True:
        prompt = input("You: ")
        
        if prompt.lower() == "exit":
            break
        
        # Append the user's message to the conversation history
        chat.append(user(prompt))
        
        # Stream the response for a better interactive experience
        print("Grok: ", end="", flush=True)
        full_response = ""
        async for chunk in chat.stream():
            if chunk.content:
                print(chunk.content, end="", flush=True)
                full_response += chunk.content
        print() # Newline after the full response is printed

        # Append the assistant's full response to the conversation history
        chat.append(assistant(full_response))

if __name__ == "__main__":
    # Run the asynchronous main function
    asyncio.run(main())