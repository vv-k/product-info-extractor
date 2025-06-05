import asyncio
import requests
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.genai import types
from google.adk.tools import FunctionTool
import Agent_one_prompt, Agent_two_prompt
import os
from dotenv import load_dotenv

# litellm = LiteLlm(model="ollama_chat/phi4-mini")
# litellm2 = LiteLlm(model="ollama_chat/gemma3")
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
os.environ["GROQ_API_KEY"] = groq_api_key
litellm = LiteLlm(model="groq/meta-llama/llama-4-scout-17b-16e-instruct")
litellm2 = LiteLlm(model="groq/qwen-qwq-32b")

# @title Define the fetch_web_conten Tool
def fetch_web_content(url: str) -> dict:
    """
   Fetches web content from a given URL using the r.jina.ai service.

   This function takes a URL, prepends it with the r.jina.ai service URL,
   and attempts to fetch the simplified web content. It handles both
   successful and failed requests.

   Args:
       url (str): The target URL to fetch content from.

   Returns:
       dict: A dictionary containing:
        Includes a 'status' key ('success' or 'error').
          If 'success', includes an 'output' key with web content details.
          If 'error', includes an 'error_message' key.

   """
    try:
        print(f"Fetching web content from {url}")
        response = requests.get(f"https://r.jina.ai/{url}")
        response.raise_for_status()
        return {"status": "success", "output": response.text}
    except requests.RequestException as e:
        return {"status": "error", "error_message": str(e)}

fetch_web_content_tool = FunctionTool(func=fetch_web_content)

web_extractor = LlmAgent(
    name="web_extractor",
    model=litellm,
    description="Fetch and provide mobile phone product information",
    instruction=Agent_one_prompt.PROMPT,
    output_key="extracted_content",
    tools=[fetch_web_content_tool]
)

product_feature_extractor = LlmAgent(
    name="extract_product_features",
    model=litellm2,
    description="Extract smartphone product information from web content",
    instruction=Agent_two_prompt.PROMPT
)

root_agent = SequentialAgent(
    name="product_feature_extractor_auditor",
    sub_agents=[web_extractor, product_feature_extractor],
    description="You are a sequential agent, your sub agents are web_extractor and product_feature_extractor. You have to invoke both one by one, and then provide the final output."
)

runner = Runner(agent=root_agent, app_name="ProductInfoExtractor", session_service=InMemorySessionService())

async def main(url: str):
    print(url)
    user_id = "user1"
    session_id = "session1"
    app_name = "ProductInfoExtractor"

    await runner.session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

    content = types.Content(role="user", parts=[types.Part(text=f"Extract product features from this URL: {url}")])

    final_response_text = "Agent did not produce a final response." # Default

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        # You can uncomment the line below to see *all* events during execution
        # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

        # Key Concept: is_final_response() marks the concluding message for the turn.
        if event.is_final_response():
            if event.content and event.content.parts:
                # Assuming text response in the first part
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate: # Handle potential errors/escalations
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            # Add more checks here if needed (e.g., specific error codes)
            break # Stop processing events once the final response is found
    print(f"<<< Agent Response: {final_response_text}")


if __name__ == "__main__":
    url = "https://www.motorola.in/smartphones-motorola-edge-50/p?skuId=445&srsltid=AfmBOoqtxKn01APXgSptbvK5GPG6xVnmji7UlstzjiYS0kz4v23U-wIG"
    output = asyncio.run(main(url))
    print(output)