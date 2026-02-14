from langgraph_sdk import get_client
import chromadb
import json

def run_task():
	result={"Langgraph":"NOT_CHECKED","Chromadb":"NOT_CHECKED"}
	try:
		lg_client=get_client(url="http://langgraph:8123")
		lg_client.health()if hasattr(lg_client,"health")else None
		result["Langgraph"]="connected"
	except Exception as e:
		result["Langgraph"]=f"Error:{str(e)}"
	try:
		chroma_client=chromadb.Client()
		chroma_client.heartbeat()if hasattr(chroma_client,"heartbeat") else None
		result["Chromadb"]="connected"
	except Exception as e:
		result["Chromadb"]=f"Error:{str(e)}"

	return result

