import streamlit as st


if __name__ == "__main__":
    st.title("CyberGuard")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is up?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        response = f"Echo: {prompt}"
        with st.chat_message("assistant"):
            st.markdown(
                """
                ```python
                a = 1
                b = 2
                print(a + b)
                ```
            """
            )
        st.session_state.messages.append({"role": "assistant", "content": response})
