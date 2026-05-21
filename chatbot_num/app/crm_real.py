import os
import httpx
from dotenv import load_dotenv

load_dotenv()

CRM_URL = os.getenv("CRM_URL")
CRM_TOKEN = os.getenv("CRM_TOKEN")


async def create_lead(data):

    headers = {
        "Authorization": f"Bearer {CRM_TOKEN}"
    }

    async with httpx.AsyncClient() as client:

        response = await client.post(
            f"{CRM_URL}/leads",
            json=data,
            headers=headers
        )

    return response.json()