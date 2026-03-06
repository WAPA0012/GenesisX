"""
GenesisX API Client Example

Demonstrates how to interact with GenesisX via REST API.
"""

import requests
import json


class GenesisXClient:
    """Simple client for GenesisX API."""

    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None

    def login(self, username, password):
        """Login and get access token."""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            return True
        return False

    def send_message(self, message):
        """Send a chat message."""
        if not self.token:
            raise Exception("Not logged in")

        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/api/v1/chat",
            headers=headers,
            json={"message": message}
        )
        return response.json()

    def get_state(self):
        """Get current agent state."""
        if not self.token:
            raise Exception("Not logged in")

        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/api/v1/state",
            headers=headers
        )
        return response.json()


def main():
    """Example usage."""
    print("GenesisX API Client Example")
    print("=" * 50)

    # Create client
    client = GenesisXClient()

    # Login
    print("\n[1] Logging in...")
    if client.login("admin", "admin"):
        print("   ✓ Login successful")
    else:
        print("   ✗ Login failed")
        return

    # Send message
    print("\n[2] Sending message...")
    response = client.send_message("Hello, Genesis!")
    print(f"   Response: {response.get('message', 'N/A')}")

    # Get state
    print("\n[3] Getting current state...")
    state = client.get_state()
    print(f"   Mood: {state.get('mood', 'N/A')}")
    print(f"   Energy: {state.get('energy', 'N/A')}")
    print(f"   Stress: {state.get('stress', 'N/A')}")

    print("\n" + "=" * 50)
    print("Example completed!")


if __name__ == "__main__":
    main()
