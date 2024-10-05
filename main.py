import streamlit as st
from agent import CyberWorkflow
from llama_index.utils.workflow import (
    draw_all_possible_flows,
)

import asyncio


async def build_ui():
    st.title("CyberGuard")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(placeholder="What is up?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        workflow = CyberWorkflow(timeout=360)
        response = await workflow.run(prompt=prompt)

        with st.chat_message("assistant"):
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})


async def main():
    await build_ui()


if __name__ == "__main__":
    asyncio.run(main())
