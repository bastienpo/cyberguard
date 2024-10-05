import streamlit as st
from dotenv import load_dotenv
from llama_index.llms.fireworks import Fireworks
import os
import asyncio

# Load environment variables
load_dotenv()


FIREWORK_API_KEY = os.getenv("FIREWORK_API_KEY")


async def build_ui(agent):
    st.title("CyberGuard")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is up?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Use the LLM to generate a response


        
        response = await agent.acomplete(prompt)

        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})


async def create_agent():
    llm = Fireworks(
        model="accounts/fireworks/models/llama-v3p2-1b-instruct",
        api_key=FIREWORK_API_KEY,
    )

    return llm


async def main():
    llm = await create_agent()
    await build_ui(llm)


if __name__ == "__main__":
    asyncio.run(main())
