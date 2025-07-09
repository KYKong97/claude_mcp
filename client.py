import os
from mcp import ClientSession, StdioServerParameters

from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
from typing import List
import asyncio
import nest_asyncio
from google import genai
from google.genai import types


nest_asyncio.apply()

load_dotenv()

class MCP_ChatBot:
    def __init__(self):
        self.session: ClientSession = None
        self.gemini_client = genai.Client(api_key=os.environ['API_KEY'])
        self.available_tools:List[dict] = []

    async def process_query(self, query:str):

        config = types.GenerateContentConfig(
            tools=self.available_tools
        )
        response = self.gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
            config=config
        )

        if response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            print(f"Function to call: {function_call.name}")
            print(f"Arguments: {function_call.args}")

            result = await self.session.call_tool(
                function_call.name,
                function_call.args
            )
            print("Result:")
            print(result.content[0].text)
            return result
        else:
            print("No Function called")
            print(response.text)
    
    async def chat_loop(self):
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
        
                if query.lower() == 'quit':
                    break
                    
                await self.process_query(query)
                print("\n")
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def connect_to_server_and_run(self):
        server_params = StdioServerParameters(
            command="uv",
            args=["run","research_server.py"],
            env=None
        )

        async with stdio_client(server_params) as (read,write):
            async with ClientSession(read, write) as session:
                self.session = session
                await session.initialize()

                response = await session.list_tools()

                tools = response.tools
                print("\nConnected to server with tools:", [tool.name for tool in tools])

                self.available_tools = [
                    types.Tool(
                        function_declarations=[
                            {
                                "name":t.name,
                                "description":t.description,
                                "parameters":{
                                    k:v
                                    for k,v in t.inputSchema.items()
                                    if k not in ["additionalProperties", "$schema"]
                                }
                            }
                        ]
                    )
                    for t in tools
                ]

                await self.chat_loop()

async def main():
    chatbot = MCP_ChatBot()
    await chatbot.connect_to_server_and_run()

if __name__ == "__main__":
    asyncio.run(main())




        