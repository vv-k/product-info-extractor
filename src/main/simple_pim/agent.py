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
litellm2 = LiteLlm(model="groq/llama-3.3-70b-versatile")
litellm3 = LiteLlm(model="groq/llama-3.3-70b-versatile")

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

from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
from typing import Dict, Any
from typing import Optional
def simple_after_tool_modifier(
        tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:
    """Inspects/modifies the tool result after execution."""
    agent_name = tool_context.agent_name
    tool_name = tool.name
    print(f"[Callback-Tool] After tool call for tool '{tool_name}' in agent '{agent_name}'")
    print(f"[Callback-Tool] Args used: {args}")
    print(f"[Callback-Tool] Original tool_response: {tool_response}")

    # Default structure for function tool results is {"result": <return_value>}
    original_result_value = tool_response.get("status", "")
    # original_result_value = tool_response

    # --- Modification Example ---
    # If the tool was 'get_capital_city' and result is 'Washington, D.C.'
    # if tool_name == 'get_capital_city' and original_result_value == "Washington, D.C.":
    #     print("[Callback] Detected 'Washington, D.C.'. Modifying tool response.")
    #
    #     # IMPORTANT: Create a new dictionary or modify a copy
    #     modified_response = deepcopy(tool_response)
    #     modified_response["result"] = f"{original_result_value} (Note: This is the capital of the USA)."
    #     modified_response["note_added_by_callback"] = True # Add extra info if needed
    #
    #     print(f"[Callback] Modified tool_response: {modified_response}")
    #     return modified_response # Return the modified dictionary

    print(f"[Callback-Tool] Passing original tool response through. {original_result_value} DONE")
    # Return None to use the original tool_response
    return None

from google.adk.agents.callback_context import CallbackContext
def modify_output_after_agent(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Logs exit from an agent and checks 'add_concluding_note' in session state.
    If True, returns new Content to *replace* the agent's original output.
    If False or not present, returns None, allowing the agent's original output to be used.
    """
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()

    print(f"\n[Callback-Agent] Exiting agent: {agent_name} (Inv: {invocation_id})")
    print(f"[Callback-Agent] Current State: {current_state}")

    # Example: Check state to decide whether to modify the final output
    # if current_state.get("add_concluding_note", False):
    #     print(f"[Callback] State condition 'add_concluding_note=True' met: Replacing agent {agent_name}'s output.")
    #     # Return Content to *replace* the agent's own output
    #     return types.Content(
    #         parts=[types.Part(text=f"Concluding note added by after_agent_callback, replacing original output.")],
    #         role="model" # Assign model role to the overriding response
    #     )
    # else:
    print(f"[Callback-Agent] State condition not met: Using agent {agent_name}'s original output.")
    # Return None - the agent's output produced just before this callback will be used.
    return None

from google.adk.models import LlmResponse
def simple_after_model_modifier(
        callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM response after it's received."""
    agent_name = callback_context.agent_name
    print(f"[Callback-LLM] After model call for agent: {agent_name}")

    # --- Inspection ---
    original_text = ""
    if llm_response.content and llm_response.content.parts:
        # Assuming simple text response for this example
        if llm_response.content.parts[0].text:
            original_text = llm_response.content.parts[0].text
            print(f"[Callback-LLM] Inspected original response text: '{original_text[:100]}...'") # Log snippet
        elif llm_response.content.parts[0].function_call:
            print(f"[Callback-LLM] Inspected response: Contains function call '{llm_response.content.parts[0].function_call.name}'. No text modification.")
            return None # Don't modify tool calls in this example
        else:
            print("[Callback-LLM] Inspected response: No text content found.")
            return None
    elif llm_response.error_message:
        print(f"[Callback-LLM] Inspected response: Contains error '{llm_response.error_message}'. No modification.")
        return None
    else:
        print("[Callback-LLM] Inspected response: Empty LlmResponse.")
        return None # Nothing to modify

    # --- Modification Example ---
    # Replace "joke" with "funny story" (case-insensitive)
    search_term = "joke"
    replace_term = "funny story"
    # if search_term in original_text.lower():
    #     print(f"[Callback] Found '{search_term}'. Modifying response.")
    #     modified_text = original_text.replace(search_term, replace_term)
    #     modified_text = modified_text.replace(search_term.capitalize(), replace_term.capitalize()) # Handle capitalization
    #
    #     # Create a NEW LlmResponse with the modified content
    #     # Deep copy parts to avoid modifying original if other callbacks exist
    #     modified_parts = [copy.deepcopy(part) for part in llm_response.content.parts]
    #     modified_parts[0].text = modified_text # Update the text in the copied part
    #
    #     new_response = LlmResponse(
    #         content=types.Content(role="model", parts=modified_parts),
    #         # Copy other relevant fields if necessary, e.g., grounding_metadata
    #         grounding_metadata=llm_response.grounding_metadata
    #     )
    #     print(f"[Callback] Returning modified response.")
    #     return new_response # Return the modified response
    # else:
    #     print(f"[Callback] '{search_term}' not found. Passing original response through.")
    #     # Return None to use the original llm_response
    #     return None


def check_if_agent_should_run(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Logs entry and checks 'skip_llm_agent' in session state.
    If True, returns Content to skip the agent's execution.
    If False or not present, returns None to allow execution.
    """
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    current_state = callback_context.state.to_dict()

    print(f"\n[Callback-Agent] Entering agent: {agent_name} (Inv: {invocation_id})")
    print(f"[Callback-Agent] Current State: {current_state}")

    # Check the condition in session state dictionary
    if current_state.get("skip_llm_agent", False):
        print(f"[Callback-Agent] State condition 'skip_llm_agent=True' met: Skipping agent {agent_name}.")
        # Return Content to skip the agent's run
        return types.Content(
            parts=[types.Part(text=f"Agent {agent_name} skipped by before_agent_callback due to state.")],
            role="model" # Assign model role to the overriding response
        )
    else:
        print(f"[Callback-Agent] State condition not met: Proceeding with agent {agent_name}.")
        # Return None to allow the LlmAgent's normal execution
        return None


web_extractor = LlmAgent(
    name="web_extractor",
    model=litellm,
    description="Fetch and provide mobile phone product information",
    instruction=Agent_one_prompt.PROMPT,
    output_key="extracted_content",
    after_tool_callback=simple_after_tool_modifier,
    before_agent_callback=check_if_agent_should_run,
    after_agent_callback=modify_output_after_agent,
    after_model_callback=simple_after_model_modifier,
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
    # model=litellm3,
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
        print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

        # Key Concept: is_final_response() marks the concluding message for the turn.
        if event.is_final_response():
            if event.content and event.content.parts:
                # Assuming text response in the first part
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate: # Handle potential errors/escalations
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            # Add more checks here if needed (e.g., specific error codes)
            # break # Stop processing events once the final response is found
    print(f"<<< Agent Response: {final_response_text}")


if __name__ == "__main__":
    url = "https://www.motorola.in/smartphones-motorola-edge-50/p?skuId=445&srsltid=AfmBOoqtxKn01APXgSptbvK5GPG6xVnmji7UlstzjiYS0kz4v23U-wIG"
    output = asyncio.run(main(url))
    print(output)