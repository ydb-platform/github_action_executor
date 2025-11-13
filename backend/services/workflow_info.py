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
                # GitHub API не предоставляет inputs напрямую, поэтому парсим YAML вручную
                # Это стандартный подход, так как inputs определены только в YAML файле
                try:
                    workflow_yaml = yaml.safe_load(content)
                    if not workflow_yaml:
                        logger.warning("Workflow YAML is empty or None")
                    else:
                        logger.debug(f"Parsed workflow YAML, top-level keys: {list(workflow_yaml.keys())}")
                    
                    # Extract inputs from workflow_dispatch
                    # В YAML структура: on.workflow_dispatch.inputs
                    if "on" in workflow_yaml:
                        on_section = workflow_yaml["on"]
                        logger.debug(f"Workflow 'on' section type: {type(on_section)}")
                        
                        workflow_dispatch = None
                        
                        # Если on - это словарь (наиболее частый случай)
                        if isinstance(on_section, dict):
                            if "workflow_dispatch" in on_section:
                                workflow_dispatch = on_section["workflow_dispatch"]
                                logger.info("Found workflow_dispatch as dict key in 'on' section")
                        
                        # Если on - это список (редкий случай, но возможен)
                        elif isinstance(on_section, list):
                            for item in on_section:
                                if isinstance(item, dict) and "workflow_dispatch" in item:
                                    workflow_dispatch = item["workflow_dispatch"]
                                    logger.info("Found workflow_dispatch in list within 'on' section")
                                    break
                        
                        if workflow_dispatch:
                            if isinstance(workflow_dispatch, dict):
                                logger.info(f"Workflow dispatch keys: {list(workflow_dispatch.keys())}")
                                
                                if "inputs" in workflow_dispatch:
                                    raw_inputs = workflow_dispatch["inputs"]
                                    if not isinstance(raw_inputs, dict):
                                        logger.warning(f"Inputs is not a dict: {type(raw_inputs)}")
                                    else:
                                        logger.info(f"Found {len(raw_inputs)} inputs in workflow: {list(raw_inputs.keys())}")
                                        
                                        # Нормализуем inputs - сохраняем все поля из YAML
                                        inputs = {}
                                        for input_name, input_config in raw_inputs.items():
                                            if not isinstance(input_config, dict):
                                                logger.warning(f"Input '{input_name}' config is not a dict: {type(input_config)}, skipping")
                                                continue
                                            
                                            input_type = input_config.get("type", "string")
                                            logger.debug(f"Processing input '{input_name}': type={input_type}")
                                            
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
                                                logger.debug(f"Input '{input_name}' (choice) has {len(inputs[input_name]['options'])} options")
                                            
                                            # Для boolean - конвертируем default в bool
                                            elif input_type == "boolean":
                                                default_val = input_config.get("default", False)
                                                if isinstance(default_val, str):
                                                    inputs[input_name]["default"] = default_val.lower() in ("true", "1", "yes")
                                                else:
                                                    inputs[input_name]["default"] = bool(default_val)
                                else:
                                    logger.info("No 'inputs' key found in workflow_dispatch")
                            else:
                                logger.warning(f"Workflow dispatch is not a dict: {type(workflow_dispatch)}")
                        else:
                            logger.info("No 'workflow_dispatch' found in workflow 'on' section")
                    else:
                        logger.info("No 'on' section found in workflow YAML")
                except yaml.YAMLError as e:
                    logger.error(f"YAML parsing error: {str(e)}", exc_info=True)
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

