import json
from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv
from .services.ai_assistant import AIAssistantSystem
from .services.llm_models import GeminiModel, OpenAIModel

import requests
import os

main_bp = Blueprint('main', __name__)

def query_knowledge_graph(kg_service_url, json_query):
    try:
        # Ensure the json_query has the correct structure
        if 'nodes' not in json_query or 'predicates' not in json_query:
            raise ValueError("Invalid JSON query structure")

        # Construct the payload in the format expected by the KG service
        payload = {
            "requests": json_query
        }
        
        print("Sending KG query:", json.dumps(payload, indent=2))  # Debug print
        
        response = requests.post(kg_service_url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error querying knowledge graph: {e}")
        if e.response is not None:
            print(f"Response content: {e.response.text}")  # Print the response content for more detail
        return {"error": f"Failed to query knowledge graph: {str(e)}"}
    except ValueError as e:
        print(f"Error with JSON query structure: {e}")
        return {"error": str(e)}
    

@main_bp.route('/query', methods=['POST'])
def process_query():
    data = request.json
    query = data.get('query')

    if not query:
        return jsonify({"error": "No query provided"}), 400

    config = current_app.config
    model_type = config['llm_model']
    schema_text = open(config['schema_path'], 'r').read()
    
    if model_type == 'openai':
        openai_api_key = os.getenv('OPENAI_API_KEY')
        llm = OpenAIModel(openai_api_key)
    elif model_type == 'gemini':
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        llm = GeminiModel(gemini_api_key)
    else:
        return jsonify({"error": "Invalid model type in configuration"}), 500

    ai_system = AIAssistantSystem(llm, schema_text)
    json_query = ai_system.process_query(query)
    print("================== Json query ===============")
    print(json_query)
    
    kg_response = query_knowledge_graph(config['annotation_service_url'], json_query)
    
    print("================== KG response ===============")
    print(kg_response)
    final_response = ai_system.process_kg_response(query, json_query, kg_response)

    return jsonify(final_response)