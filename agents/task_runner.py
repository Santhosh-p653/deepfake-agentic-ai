from langgraph_sdk import get_client
import chromadb
import json

def run_task():
	lg_client=get_client(url="http://localhost:8123")
	assistants=lg_client.assistants.search()
	chroma_client=chromadb.Client()
	result_lg=f"Found{len(assistants)}assistants"
	result_chroma="Chromadb processed"
	output={"langgraph":result_lg,"chromadb":result_chroma}
	print(json.dumps(output))
if __name__ == "__main__":
	run_task()
