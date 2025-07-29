import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FRESH_API")
ENDPOINT = os.getenv("FRESH_ENDPOINT")

def get_agent_by_id(agent_id):
    url = f"{ENDPOINT}agents/{agent_id}"
    response = requests.get(url, auth=(API_KEY, "X"))
    print(f"🔎 Fetching agent ID {agent_id}... Status: {response.status_code}")

    if response.status_code == 403:
        print("❌ 403 Forbidden - Check your API key, permissions, or endpoint.")
        return
    if response.status_code == 404:
        print("❌ Agent not found.")
        return
    if response.status_code != 200:
        print(f"❌ Unexpected error: {response.status_code}")
        return

    data = response.json().get("agent", {})
    print("\n✅ Agent Information:\n")

    print(f"🆔 ID: {data.get('id')}")
    print(f"👤 Name: {data.get('first_name', '')} {data.get('last_name', '')}")
    print(f"📧 Email: {data.get('email')}")
    print(f"📞 Work Phone: {data.get('work_phone_number')}")
    print(f"📱 Mobile: {data.get('mobile_phone_number')}")
    print(f"💼 Job Title: {data.get('job_title')}")
    print(f"🟢 Active: {data.get('active')}")
    print(f"🎯 Occasional: {data.get('occasional')}")
    print(f"🕒 Last Login: {data.get('last_login_at')}")
    print(f"🕘 Last Active: {data.get('last_active_at')}")
    print(f"📍 Location ID: {data.get('location_id')}")
    print(f"🏠 Address: {data.get('address')}")
    print(f"🌐 Time Zone: {data.get('time_zone')}")
    print(f"📝 Language: {data.get('language')}")
    print(f"🏷️  Custom Fields: {data.get('custom_fields', {})}")

def main():
    try:
        agent_id_input = input("Enter the Agent ID to look up: ").strip()
        if not agent_id_input.isdigit():
            print("❌ Please enter a valid numeric Agent ID.")
            return

        get_agent_by_id(agent_id_input)

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
