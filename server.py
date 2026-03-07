import os
from dotenv import load_dotenv
import pandas as pd
from fastapi import FastAPI,Request
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import re # regex for parsing email content

load_dotenv()
base_url = os.getenv("BASE_URL")
userId='me'

app=FastAPI()


# Adding middleware to handle CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can specify specific origins if needed)
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


@app.get("/get-email-list")
async def get_email_list(request:Request):
    token=request.headers.get("Authorization")
    response=requests.get(base_url + "/gmail/v1/users/me/messages",
                          headers={"Authorization": token})
    return response.json()

@app.get("/job-applications")
async def get_job_applications(request:Request):
    token=request.headers.get("Authorization")
    response=requests.get(base_url + "/gmail/v1/users/me/messages",
                          headers={"Authorization": token})
    for i in range(len(response.json().get("messages", []))):
        msg_id=response.json().get("messages", [])[i].get("id")
        msg_response=requests.get(base_url + f"/gmail/v1/users/me/messages/{msg_id}",
                                  headers={"Authorization": token})
        
        # if subject contains keywords

        #else regex through the body to find job application
    return response.json()


if __name__=="__main__":
    uvicorn.run("server:app",host="127.0.0.1",port=8000,reload=True)