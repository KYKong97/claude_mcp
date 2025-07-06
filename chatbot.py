import arxiv
import json
import os
from typing import List
from dotenv import load_dotenv
from google import genai
from google.genai import types
import traceback


PAPER_DIR = "papers"

TOOLS = [
        {
            "name":"search_papers",
            "description":"Search for papers on arXiv",
            "parameters":{
                "type":"object",
                "properties":{
                    "topic":{
                        "type":"string",
                        "description":"The topic to search for"
                    },
                    "max_results":{
                        "type":"integer",
                        "description":"Maximum number of results to retrieve",
                        "default":5
                    }
                },
                "required":["topic"]
            }
        },
        {
            "name":"extract_info",
            "description":"Search for information about a specific paper.",
            "parameters":{
                "type":"object",
                "properties":{
                    "paper_id":{
                        "type":"string",
                        "description":"The ID of the paper to look for."
                    }
                },
                "required":["paper_id"]
            }
        }
        
    ]

def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.
    
    Args:
        topic: The topic to search for
        max_results: Maximum number of results to retrieve (default: 5)
        
    Returns:
        List of paper IDs found in the search
    """
    
    # Use arxiv to find the papers 
    client = arxiv.Client()

    # Search for the most relevant articles matching the queried topic
    search = arxiv.Search(
        query = topic,
        max_results = max_results,
        sort_by = arxiv.SortCriterion.Relevance
    )

    papers = client.results(search)
    
    # Create directory for this topic
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)
    
    file_path = os.path.join(path, "papers_info.json")

    # Try to load existing papers info
    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    # Process each paper and add to papers_info  
    paper_ids = []
    for paper in papers:
        paper_ids.append(paper.get_short_id())
        paper_info = {
            'title': paper.title,
            'authors': [author.name for author in paper.authors],
            'summary': paper.summary,
            'pdf_url': paper.pdf_url,
            'published': str(paper.published.date())
        }
        papers_info[paper.get_short_id()] = paper_info
    
    # Save updated papers_info to json file
    with open(file_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)
    
    print(f"Results are saved in: {file_path}")
    
    return paper_ids

def execute_tool(tool_name, tool_args, mapping_tool_function):
    result = mapping_tool_function[tool_name](**tool_args)

    if result is None:
        result = "The operation completed but didn't return any results."
    elif isinstance(result, list):
        result = ",".join(result)
    elif isinstance(result,dict):
        result = json.dumps(result,indent=2)
    else:
        result = str(result)
    return result

def extract_info(paper_id: str) -> str:
    """
    Search for information about a specific paper across all topic directories.
    
    Args:
        paper_id: The ID of the paper to look for
        
    Returns:
        JSON string with paper information if found, error message if not found
    """
 
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
    
    return f"There's no saved information related to paper {paper_id}."

def process_query(query):
    client = genai.Client(api_key=os.environ['API_KEY'])

    tools = types.Tool(
        function_declarations=TOOLS
    )

    config = types.GenerateContentConfig(tools=[tools])

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config=config
    )
    # Check for a function call
    if response.candidates[0].content.parts[0].function_call:
        function_call = response.candidates[0].content.parts[0].function_call
        print(f"Function to call: {function_call.name}")
        print(f"Arguments: {function_call.args}")
        if function_call.name == "search_papers":
            result = search_papers(**function_call.args)
        elif function_call.name == "extract_info":
            result = extract_info(**function_call.args)
        return result
        #  In a real app, you would call your function here:
        #  result = schedule_meeting(**function_call.args)
    else:
        print("No function call found in the response.")
        print(response.text)

   
def chat_loop():
    print("Type your queries or 'quit' to exit.")
    while True:
        try:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break
            result = process_query(query)
            if result:
                print("Result:")
                print(result)
        except Exception as e:
            print(f"\n Error: {str(e)}")
            traceback.format_exc()

        
def main():
    search_papers("computers")
    extract_info('1310.7911v2')

    

    

    chat_loop()

if __name__=="__main__":
    main()
