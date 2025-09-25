#!/usr/bin/env python3
"""Basic usage example for the MCP Tool Registry."""

import json
import time
from typing import Dict, Any

import requests


class MCPRegistryClient:
    """Simple client for the MCP Tool Registry API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
    
    def register_tool(self, name: str, version: str, description: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new tool."""
        data = {
            "name": name,
            "version": version,
            "description": description,
            "schema": schema
        }
        response = requests.post(f"{self.base_url}/tools", json=data)
        response.raise_for_status()
        return response.json()
    
    def get_tool(self, name: str) -> Dict[str, Any]:
        """Get a specific tool."""
        response = requests.get(f"{self.base_url}/tools/{name}")
        response.raise_for_status()
        return response.json()
    
    def list_tools(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """List all tools."""
        response = requests.get(f"{self.base_url}/tools", params={"page": page, "per_page": per_page})
        response.raise_for_status()
        return response.json()
    
    def search_tools(self, query: str, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """Search tools."""
        response = requests.get(f"{self.base_url}/tools/search", params={"query": query, "page": page, "per_page": per_page})
        response.raise_for_status()
        return response.json()
    
    def update_tool(self, name: str, **updates) -> Dict[str, Any]:
        """Update a tool."""
        response = requests.put(f"{self.base_url}/tools/{name}", json=updates)
        response.raise_for_status()
        return response.json()
    
    def delete_tool(self, name: str) -> Dict[str, Any]:
        """Delete a tool."""
        response = requests.delete(f"{self.base_url}/tools/{name}")
        response.raise_for_status()
        return response.json()


def main():
    """Demonstrate basic usage of the MCP Tool Registry."""
    print("MCP Tool Registry - Basic Usage Example")
    print("=" * 50)
    
    # Initialize client
    client = MCPRegistryClient()
    
    # Example tools to register
    tools = [
        {
            "name": "calculator",
            "version": "1.0.0",
            "description": "A simple calculator tool for basic arithmetic operations",
            "schema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "The arithmetic operation to perform"
                    },
                    "a": {"type": "number", "description": "First operand"},
                    "b": {"type": "number", "description": "Second operand"}
                },
                "required": ["operation", "a", "b"]
            }
        },
        {
            "name": "weather",
            "version": "1.2.0",
            "description": "Get current weather information for a location",
            "schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or location name"},
                    "units": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
                },
                "required": ["location"]
            }
        },
        {
            "name": "file_reader",
            "version": "2.0.0",
            "description": "Read and process text files",
            "schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to read"},
                    "encoding": {"type": "string", "default": "utf-8"},
                    "max_lines": {"type": "integer", "description": "Maximum number of lines to read"}
                },
                "required": ["file_path"]
            }
        }
    ]
    
    try:
        # Register tools
        print("\n1. Registering tools...")
        for tool in tools:
            try:
                result = client.register_tool(**tool)
                print(f"✓ Registered: {result['name']} v{result['version']}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    print(f"⚠ Tool {tool['name']} already exists, skipping...")
                else:
                    raise
        
        # List all tools
        print("\n2. Listing all tools...")
        tools_list = client.list_tools()
        print(f"Total tools: {tools_list['total']}")
        for tool in tools_list['tools']:
            print(f"  - {tool['name']} v{tool['version']}: {tool['description']}")
        
        # Search for tools
        print("\n3. Searching for 'calculator'...")
        search_results = client.search_tools("calculator")
        print(f"Found {search_results['total']} tool(s):")
        for tool in search_results['tools']:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Get specific tool details
        print("\n4. Getting calculator tool details...")
        calculator = client.get_tool("calculator")
        print(f"Name: {calculator['name']}")
        print(f"Version: {calculator['version']}")
        print(f"Description: {calculator['description']}")
        print("Schema:")
        print(json.dumps(calculator['schema'], indent=2))
        
        # Update a tool
        print("\n5. Updating calculator tool...")
        updated_calculator = client.update_tool(
            "calculator",
            version="1.1.0",
            description="An enhanced calculator tool with more operations"
        )
        print(f"✓ Updated: {updated_calculator['name']} v{updated_calculator['version']}")
        
        # Final list
        print("\n6. Final tool list...")
        final_list = client.list_tools()
        for tool in final_list['tools']:
            print(f"  - {tool['name']} v{tool['version']}: {tool['description']}")
        
        print("\n✓ Example completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the MCP Tool Registry.")
        print("Make sure the server is running: uv run mcp-registry --reload")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()