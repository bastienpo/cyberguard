from llama_index.core import PromptTemplate
from dotenv import load_dotenv
from llama_index.llms.fireworks import Fireworks
import os
from e2b_code_interpreter import CodeInterpreter
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.agent.lats import LATSAgentWorker
from llama_index.core.agent import AgentRunner
from llama_index.core.workflow import (
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from llama_index.core.workflow import (
    Event,
)

from llama_index.core import Settings

# Load environment variables
load_dotenv()

FIREWORK_API_KEY = os.getenv("FIREWORK_API_KEY")
E2B_API_KEY = os.getenv("E2B_API_KEY")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")

Settings.embed_model = FastEmbedEmbedding(model_name="BAAI/bge-base-en-v1.5")
Settings.llm = Fireworks(
    model="accounts/fireworks/models/llama-v3p1-70b-instruct",
    api_key=FIREWORK_API_KEY,
    max_tokens=4096,
    temperature=0.8,
)

vulnerability_template = """You are a cybersecurity expert. Analyze the following code and identify potential vulnerabilities. 

For each vulnerability, provide a description and a code snippet that demonstrates the vulnerability.

Format of the output:
- SQL Injection : SQL Injection is a vulnerability that allows an attacker to inject SQL code into a database query.
- Cross-Site Scripting (XSS) : XSS is a vulnerability that allows an attacker to inject JavaScript code into a web page.
        
Ensure each vulnerability is on a separate line. Be concise but thorough in your analysis and keep it to one line. If no vulnerabilities are found, state "No vulnerabilities detected."
        
User's code:
{query}
        
Analyze the code above and **list only** the vulnerabilities in the specified format.
"""

fix_template = """Fix the code vulnerabilities and return **only** the fixed code.

Retrieve information about vulnerabilities.

Run the code and to ensure that the code is working.

Identified vulnerabilities:
{vulnerabilities}

User's code:
{query}
"""

test_template = """You are given a code snippet and a list of vulnerabilities.

Generate and run test cases to verify that the fixed code works and fixes the vulnerabilities.

Fixed code:
{fixed_code}

Vulnerabilities:
{vulnerabilities}

Run the test case and output the results of the test cases in markdown table format with OK if the test case passes or KO if it fails or unable to run and the code that was run.
"""


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


def create_rag_tool() -> FunctionTool:
    """Create a RAG tool.

    Args:
        collection_name: The name of the collection to create the RAG tool for.

    Returns:
        FunctionTool: The RAG tool.
    """
    vector_store = QdrantVectorStore(
        collection_name="weakness",
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )

    index = VectorStoreIndex.from_vector_store(vector_store)

    query_engine = RetrieverQueryEngine(
        retriever=index.as_retriever(),
    )

    return FunctionTool.from_defaults(
        fn=query_engine.query,
        name="rag_tool",
        description=("Retrieve information about vulnerabilities."),
    )


code_tool = FunctionTool.from_defaults(
    fn=code_interpret_tool,
    description="Run python code in a sandboxed interpreter to test and fix vulnerabilities.",
)
rag_tool = create_rag_tool()


class VulnerabilityEvent(Event):
    vulnerabilities: str
    prompt: str


class FixVulnerabilityEvent(Event):
    prompt: str
    vulnerabilities: str
    fixed_code: str


class SummaryEvent(Event):
    prompt: str
    vulnerabilities: str
    fixed_code: str
    test_results: str


class CyberWorkflow(Workflow):
    llm = Fireworks(
        model="accounts/fireworks/models/llama-v3p1-70b-instruct",
        api_key=FIREWORK_API_KEY,
        max_tokens=4096,
        temperature=0.8,
    )

    # Create the agent
    react_agent = ReActAgent.from_tools(
        [code_tool, rag_tool], llm=llm, verbose=True, max_iterations=25
    )

    agent_worker = LATSAgentWorker(
        tools=[code_tool, rag_tool], num_expansions=3, max_rollouts=5, llm=llm
    )

    @step
    async def identify_vulnerabilities(self, event: StartEvent) -> VulnerabilityEvent:
        """
        Identify potential vulnerabilities in the code.
        """

        vulnerability_prompt = PromptTemplate(vulnerability_template)

        vulnerabilities = await self.llm.acomplete(
            vulnerability_prompt.format(query=event.prompt)
        )

        return VulnerabilityEvent(
            prompt=event.prompt, vulnerabilities=str(vulnerabilities)
        )

    @step
    async def fix_vulnerabilities(
        self, event: VulnerabilityEvent
    ) -> FixVulnerabilityEvent:
        fix_prompt = PromptTemplate(fix_template)

        fixed_code = await self.react_agent.achat(
            fix_prompt.format(vulnerabilities=event.vulnerabilities, query=event.prompt)
        )

        return FixVulnerabilityEvent(
            prompt=event.prompt,
            vulnerabilities=event.vulnerabilities,
            fixed_code=str(fixed_code),
        )

    @step
    async def test_agent(self, event: FixVulnerabilityEvent) -> SummaryEvent:
        """Generate test cases to verify the fix."""

        test_prompt = PromptTemplate(test_template)

        lats_agent = AgentRunner(self.agent_worker)

        test_results = await lats_agent.achat(
            test_prompt.format(
                fixed_code=event.fixed_code, vulnerabilities=event.vulnerabilities
            )
        )

        return SummaryEvent(
            prompt=event.prompt,
            vulnerabilities=event.vulnerabilities,
            fixed_code=event.fixed_code,
            test_results=str(test_results),
        )

    @step
    async def summarize(self, event: SummaryEvent) -> StopEvent:
        """Summarize the vulnerabilities and the fixed code."""

        summary_template = """Summarize in form of a report the identified vulnerabilities and the fixed code.

        Follow this format:
        ## 1. Vulnerabilities summary

        Vulnerabilities to summarize:
        {vulnerabilities}

        ## 2. Differences

        Original code:
        {query}

        Fixed code:
        {fixed_code}

        ## 3. Test results
        (A markdown table of test cases with code, results and name of the test case.)
        
        Test results:
        {test_results}
        """

        summary = await self.llm.acomplete(
            summary_template.format(
                query=event.prompt,
                vulnerabilities=event.vulnerabilities,
                fixed_code=event.fixed_code,
                test_results=event.test_results,
            )
        )

        return StopEvent(result=str(summary))
