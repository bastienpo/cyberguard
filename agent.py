from llama_index.core import PromptTemplate
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


def code_interpret_tool(code: str):
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
    fn=code_interpret_tool, description="Run python code in a sandboxed interpreter."
)


def run_workflow(prompt: str):
    """"""
    # Create the LLM
    llm = Fireworks(
        model="accounts/fireworks/models/llama-v3p1-70b-instruct",
        api_key=FIREWORK_API_KEY,
    )

    # Create the agent
    agent = ReActAgent.from_tools([tool], llm=llm, verbose=True, max_iterations=25)

    # Step 1:
    # Generate a list of potential vulnerabilities
    identification_template = """
    You are a cybersecurity expert. You are given a code snippet.

    Identify a list of potential vulnerabilities in the code.
    
    Example of format:
    - SQL Injection : SQL Injection is a vulnerability that allows an attacker to inject SQL code into a database query.
    - Cross-Site Scripting (XSS) : XSS is a vulnerability that allows an attacker to inject JavaScript code into a web page.

    User's code:
    {query}
    """

    identification_prompt = PromptTemplate(identification_template)

    vulnerabilities = llm.complete(identification_prompt.format(query=prompt))

    report_template = """
    Fix the code vulnerabilities and return some test cases to verify the fix.

    Provide the output of the code execution in table format with ✅ or ❌.

    Vulnerabilities:
    {vulnerabilities}

    User's code:
    {query}
    """

    report_prompt = PromptTemplate(report_template)

    report = agent.chat(
        report_prompt.format(query=prompt, vulnerabilities=vulnerabilities)
    )

    return report
