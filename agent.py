import streamlit as st
from dotenv import load_dotenv
from llama_index.llms.fireworks import Fireworks
import os
from e2b_code_interpreter import CodeInterpreter
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent

# Load environment variables
load_dotenv()

FIREWORK_API_KEY = os.getenv("FIREWORK_API_KEY")
E2B_API_KEY = os.getenv("E2B_API_KEY")


def code_interpret(code: str):
    """Use the code interpreter to run the code."""

    with CodeInterpreter() as sandbox:
        exec = sandbox.notebook.exec_cell(
            code,
            on_stderr=lambda stderr: print("[Code Interpreter]", stderr),
            on_stdout=lambda stdout: print("[Code Interpreter]", stdout),
        )

    if exec.error:
        print("[Code Interpreter ERROR]", exec.error)
    else:
        return exec.results


tool = FunctionTool.from_defaults(
    fn=code_interpret, description="Run code in the code interpreter."
)


def create_agent(model: str):
    """Create an agent with the code interpreter tool."""

    # Create the LLM
    llm = Fireworks(
        model=model,
        api_key=FIREWORK_API_KEY,
    )

    # Create a ReAct agent
    agent = ReActAgent.from_tools([tool], llm=llm, verbose=True)

    return agent
