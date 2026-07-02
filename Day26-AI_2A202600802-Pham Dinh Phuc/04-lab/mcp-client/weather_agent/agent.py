"""
Weather Agent - Connects to Remote MCP Server on Cloud Run
Successfully connects to custom MCP HTTP endpoints!
"""
from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCP_SERVER_URL = "http://localhost:8085/mcp"

logger.info(f"🌐 Initializing weather agent with remote MCP server")
logger.info(f"📡 MCP Server: {MCP_SERVER_URL}")

try:
    # Create connection parameters for the remote MCP server
    connection_params = StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,  # Increased timeout for Cloud Run cold starts
    )
    
    # Create the MCP toolset - this will connect to the remote server
    logger.info("🔌 Connecting to MCP server...")
    weather_tools = McpToolset(
        connection_params=connection_params,
    )
    logger.info("✅ MCP toolset created successfully")
    
    # Set up model: Use OpenAI via LiteLLM if OPENAI_API_KEY is configured, otherwise fallback to Gemini
    import os
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and "your_openai" not in openai_key and len(openai_key.strip()) > 30:
        from google.adk.models.lite_llm import LiteLlm
        model_name = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
        logger.info(f"🤖 Configuring OpenAI model ({model_name}) via LiteLLM...")
        model_instance = LiteLlm(
            model=model_name,
            api_key=openai_key
        )
    else:
        logger.info("🤖 Using default Gemini model (gemini-2.5-flash)...")
        model_instance = "gemini-2.5-flash"

    # Create the agent with remote MCP tools
    root_agent = Agent(
        name="weather_agent",
        model=model_instance,
        tools=[weather_tools],
    )
    logger.info(f"✅ Weather agent initialized with remote MCP tools using model: {model_instance}")
    logger.info("   - get_current_weather(city)")
    logger.info("   - get_forecast(city, days)")
    logger.info("   - health_check()")
    logger.info("🎉 Remote MCP connection successful!")
    
except Exception as e:
    logger.error(f"❌ Failed to connect to remote MCP server: {e}")
    logger.error(f"   Server URL: {MCP_SERVER_URL}")
    import traceback
    traceback.print_exc()
    
    # Create a fallback agent without tools
    logger.warning("⚠️  Creating fallback agent without MCP tools")
    # Set up fallback model
    import os
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and "your_openai" not in openai_key and len(openai_key.strip()) > 30:
        from google.adk.models.lite_llm import LiteLlm
        model_name = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
        model_instance = LiteLlm(
            model=model_name,
            api_key=openai_key
        )
    else:
        model_instance = "gemini-2.5-flash"
        
    root_agent = Agent(
        name="weather_agent",
        model=model_instance,
    )

