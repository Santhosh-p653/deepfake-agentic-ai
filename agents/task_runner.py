import langgraph
import chromadb
import json

def run_task():
	lg_client=langgraph.Client()
	chroma_client=chromadb.Client()
	result_lg="Langgraph processed"
	result_chroma="Chromadb processed"
	output={"langgraph":result_lg,"chromadb":result_chroma}
	print(json.dumps(output))
if __name__ == "__main__":
	run_task()
