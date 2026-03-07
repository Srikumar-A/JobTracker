import os
from dotenv import load_dotenv
import pandas as pd
from fastapi import FastAPI
import requests
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()
base_url = os.getenv("BASE_URL")
userId='me'
SCOPES=["https://www.googleapis.com/auth/gmail.readonly"]

app=FastAPI()

@app.get("/get-email-list")
async def get_email_list():
    response=requests.get(base_url + "/gmail/v1/users/{userId}/messages")
    return response.json()


if __name__=="__main__":
    flow=InstalledAppFlow.from_client_secrets_file(
        {
            "installed":{
                "client_id":os.getenv("CLIENT_ID"),
                "client_secret":os.getenv("CLIENT_SECRET"),
                "redirect_uris":["http://localhost"],
                "auth_uri":"https://accounts.google.com/o/oauth2/auth",
                "token_uri":"https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES
    )
    creds=flow.run_local_server(port=0)
    print("Access Token:", creds.token)
    print("Refresh Token:", creds.refresh_token)
    print("authenticated ...")