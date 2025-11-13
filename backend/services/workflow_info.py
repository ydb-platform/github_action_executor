"""
Service for getting workflow information from GitHub API
"""
import os
import base64
import logging
import httpx
import yaml
from backend.services.github_app import get_installation_token, load_private_key

logger = logging.getLogger(__name__)


async def get_workflow_info(owner: str, repo: str, workflow_id: str) -> dict:
    """
    Get workflow information including inputs from GitHub API
    
    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Workflow file name (e.g., "ci.yml") or workflow ID
        
    Returns:
        Dictionary with workflow information including inputs
    """
    # Get GitHub App credentials
    app_id = os.getenv("GITHUB_APP_ID")
    installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    
    if not all([app_id, installation_id]):
        raise ValueError("GITHUB_APP_ID and GITHUB_APP_INSTALLATION_ID must be set")
    
    # Load private key and get installation token
    private_key = load_private_key(private_key_path)
    installation_token = await get_installation_token(app_id, installation_id, private_key)
    
    headers = {
        "Authorization": f"token {installation_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Get workflow information
            workflow_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}"
            response = await client.get(workflow_url, headers=headers)
            
            if response.status_code == 404:
                logger.warning(f"Workflow {workflow_id} not found in {owner}/{repo}")
                return {
                    "found": False,
                    "inputs": {}
                }
            
            response.raise_for_status()
            workflow_data = response.json()
            
            # Get workflow file content to parse inputs
            # GitHub API doesn't directly provide inputs, so we need to get the workflow file
            workflow_path = workflow_data.get("path", f".github/workflows/{workflow_id}")
            
            # Try to get workflow file content
            file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{workflow_path}"
            file_response = await client.get(file_url, headers=headers)
            
            inputs = {}
            if file_response.status_code == 200:
                logger.info(f"Successfully retrieved workflow file content")
                file_data = file_response.json()
                
                # Decode file content
                content = base64.b64decode(file_data["content"]).decode("utf-8")
                
                # Parse YAML
                try:
                    workflow_yaml = yaml.safe_load(content)
                    logger.debug(f"Parsed workflow YAML keys: {list(workflow_yaml.keys()) if workflow_yaml else 'None'}")
                    
                    # Extract inputs from workflow_dispatch
                    if "on" in workflow_yaml and "workflow_dispatch" in workflow_yaml["on"]:
                        workflow_dispatch = workflow_yaml["on"]["workflow_dispatch"]
                        logger.debug(f"Workflow dispatch keys: {list(workflow_dispatch.keys()) if workflow_dispatch else 'None'}")
                        
                        if "inputs" in workflow_dispatch:
                            raw_inputs = workflow_dispatch["inputs"]
                            logger.info(f"Found {len(raw_inputs)} inputs in workflow: {list(raw_inputs.keys())}")
                            
                            # Нормализуем inputs - сохраняем все поля из YAML
                            inputs = {}
                            for input_name, input_config in raw_inputs.items():
                                input_type = input_config.get("type", "string")
                                logger.debug(f"Processing input '{input_name}': type={input_type}, config={input_config}")
                                
                                inputs[input_name] = {
                                    "type": input_type,
                                    "description": input_config.get("description", ""),
                                    "required": input_config.get("required", False),
                                    "default": input_config.get("default")
                                }
                                
                                # Для choice типа - сохраняем options
                                if input_type == "choice":
                                    options = input_config.get("options", [])
                                    inputs[input_name]["options"] = options if isinstance(options, list) else []
                                    logger.debug(f"Input '{input_name}' has {len(inputs[input_name]['options'])} options")
                                
                                # Для boolean - конвертируем default в bool
                                if input_type == "boolean":
                                    default_val = input_config.get("default", False)
                                    if isinstance(default_val, str):
                                        inputs[input_name]["default"] = default_val.lower() in ("true", "1", "yes")
                                    else:
                                        inputs[input_name]["default"] = bool(default_val)
                        else:
                            logger.info("No 'inputs' found in workflow_dispatch")
                    else:
                        logger.info("No 'workflow_dispatch' found in workflow 'on' section")
                except Exception as e:
                    logger.error(f"Failed to parse workflow YAML: {str(e)}", exc_info=True)
            
            result = {
                "found": True,
                "name": workflow_data.get("name", workflow_id),
                "path": workflow_data.get("path"),
                "state": workflow_data.get("state"),
                "inputs": inputs
            }
            logger.info(f"Returning workflow info: found={result['found']}, inputs_count={len(inputs)}")
            return result
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to get workflow info: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            return {
                "found": False,
                "inputs": {}
            }
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting workflow info: {str(e)}", exc_info=True)
        raise

