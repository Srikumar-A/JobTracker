import os
from dotenv import load_dotenv
import pandas as pd
from fastapi import FastAPI,Request
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import re # regex for parsing email content
import base64
# httpx for security
import httpx
# supabase postgress for backend
from supabase import create_client
from email.utils import parsedate_to_datetime

#llm
from openai import AsyncOpenAI
import json



load_dotenv()
base_url = os.getenv("BASE_URL")
userId='me'

# openai setup
client=AsyncOpenAI(
    api_key=os.getenv("OPENAI_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

#supabase client setup
SUPABASE_URL=os.getenv("SUPABASE_URL")
SUPABASE_KEY=os.getenv("SUPABASE_KEY")
db=create_client(SUPABASE_URL,SUPABASE_KEY)

app=FastAPI()

layer1_keys=["job","application","interview","offer","candidate","vacancy","opening","hire","recruitment"]
layer2_keys=["recieved","submitted","scheduled","accepted","rejected","interview","assessment","offer","regret","unfortunately","proceed","selected","rejected"]
status_list=["submitted","interview","offer","rejected"] # static
status_dict={
    "recieved":0,
    "submitted":0,
    "scheduled":1,
    "accepted":0,
    "rejected":3,
    "interview":1,
    "assessment":1,
    "offer":2,
    "regret":3,
    "unfortunately":3,
    "proceed":1,
    "selected":1,
    "rejected":3,
    "unsuccessful":3,
    "unknown":0

}
company_name_patterns=[
    r"applying to\s+([A-Z][\w\s&.-]+?)[\s.,!]",
    r"application at\s+([A-Z][\w\s&.-]+?)[\s.,!]",
    r"interest in\s+([A-Z][\w\s&.-]+?)[\s.,!]",
    r"interview with\s+([A-Z][\w\s&.-]+?)[\s.,!]",
    r"joining\s+([A-Z][\w\s&.-]+?)[\s.,!]",
    r"we at\s+([A-Z][\w\s&.-]+?)[\s.,!]",
    r"on behalf of\s+([A-Z][\w\s&.-]+?)[\s.,!]",
    r"sent to\s+([A-Z][\w\s&.-]+?)[\s.,!]",
]
role_patterns = [
    r"for the\s+([A-Z][\w\s/&-]+?)\s+(?:role|position|opening)",
    r"applied for\s+([A-Z][\w\s/&-]+?)\s+(?:at|role|position|[\s.,])",
    r"application for\s+([A-Z][\w\s/&-]+?)\s+(?:at|has|was|is|[\s.,])",
    r"(?:role|position):\s*([A-Z][\w\s/&-]+?)[\s.,\n]",
    r"interview for\s+(?:the\s+)?([A-Z][\w\s/&-]+?)\s+(?:role|position|at|[\s.,])",
    r"regarding\s+(?:the\s+)?([A-Z][\w\s/&-]+?)\s+(?:role|position|opening|at)",
    r"invited.*?for\s+(?:the\s+)?([A-Z][\w\s/&-]+?)\s+(?:role|position|[\s.,])",
    r"offer for\s+(?:the\s+)?([A-Z][\w\s/&-]+?)\s+(?:role|position|at|[\s.,])",
]
# Adding middleware to handle CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can specify specific origins if needed)
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

#helper functions
def is_job_application(text,layer):
    text=text.lower()
    if re.search(r'\b(' + '|'.join(layer) + r')\b', text):
        return True
    return False
async def LLM_JobParser(sub,body):
    system_prompt='''
            You are an information extraction system that processes email content and identifies whether the email is related to a job application.

            The user will provide the subject and body of an email.

            Your task is to:
            1. Determine if the email is related to a job application or hiring process.
            2. Extract relevant information if available.

            A job application email includes (but is not limited to):
            - Job application confirmations
            - Interview invitations
            - Interview scheduling
            - Coding assessments
            - Hiring process updates
            - Rejections
            - Offers
            - Recruiter outreach regarding a role

            If the email is unrelated to job applications, set:
            "is_job_application": false

            Extraction rules:
                - sender: leave as an empty string ("") because it will be filled by the system outside the LLM.
                - date: leave as an empty string ("") because it will be filled by the system outside the LLM.
                - user_id: leave as an empty string ("")
                - mail_id: leave as an empty string ("")

                - status: classify the stage of the job process if applicable. Possible values include:
                    "applied"
                    "submitted"
                    "assessment"
                    "interview"
                    "interview"
                    "rejected"
                    "offer"
                    "unknown"

                - company: extract the company or organization name mentioned in the email. If not identifiable, return "".

            - role: extract the job title mentioned in the email. If not identifiable, return "".

            Output rules:
                - Return ONLY valid JSON.
                - Do NOT include explanations.
                - Do NOT include markdown.
                - Do NOT include extra text.
                - Follow the schema exactly.

                Output schema:

                {
                "status": "",
                "company": "",
                "role": "",
                "is_job_application": false
            }   
            '''
    resp=await client.chat.completions.create(
        model='arcee-ai/trinity-large-preview:free',
        messages=[
            {"role":"system",
             "content":system_prompt},
             {"role":"user",
              "content":"subject: "+sub+" body: "+body}
        ],
        max_tokens=200,
        temperature=0,
        response_format={"type":"json_object"}
    )

    return json.loads(resp.choices[0].message.content)

def extract_body(payload):

    data=payload.get("body",{}).get("data","")
    if data and payload.get("mimeType")=="text/plain":
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    
    for part in payload.get("parts",[]):
        result=extract_body(part)
        if result:
            return result
    if data and payload.get("mimeType") == "text/html":
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    
    for part in payload.get("parts", []):
        data = part.get("body", {}).get("data", "")
        if data and part.get("mimeType") == "text/html":
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    
    return ""

@app.get("/get-email-list")
async def get_email_list(request:Request):
    token=request.headers.get("Authorization")
    response=requests.get(base_url + "/gmail/v1/users/me/messages",
                          headers={"Authorization": token})
    return response.json()

async def get_user_id(token)->str:
    async with httpx.AsyncClient() as client:
        response=await client.get("https://www.googleapis.com/oauth2/v2/userinfo",
                                  headers={"Authorization": token})
        if response.status_code==200:
            return response.json().get("id")
    return None

@app.get("/get-applications")
async def get_applications(request:Request):
    token=request.headers.get("Authorization")
    user_id=await get_user_id(token)
    my_jobs=db.table("job_applications").select("company","date","role","status").eq("user_id",user_id).execute()
    return {"applications":my_jobs.data}

@app.get("/process-applications")
async def process_job_applications(request:Request):
    token=request.headers.get("Authorization")
    response=requests.get(base_url + "/gmail/v1/users/me/messages",
                          headers={"Authorization": token})
    user_id=await get_user_id(token)
    msg_response={}
    # reverse traversing to ensure the checkpointing of latext email is done right
    for i in range(len(response.json().get("messages", []))-1,0,-1):
        msg_id=response.json().get("messages", [])[i].get("id")
        msg_response=requests.get(base_url + f"/gmail/v1/users/me/messages/{msg_id}",
                                  headers={"Authorization": token})
        # if subject contains keywords
        headers=msg_response.json().get("payload", {}).get("headers", [])
        subject=""
        sender=""
        date=""
        for i in range(len(headers)):
            if headers[i].get("name")=="Subject":
                subject=headers[i].get("value")
            elif headers[i].get("name")=="From":
                sender=headers[i].get("value")
            elif headers[i].get("name")=="Date":
                date=headers[i].get("value")
                date=parsedate_to_datetime(date).isoformat()

        

        body=extract_body(msg_response.json().get("payload",{}))

        #check if already seen
        already_seen=(
            db.table('user_chkpts').
            select("*").
            eq("user_id",user_id).
            gt("last_timestamp",date).
            execute()
        )
        if already_seen.data:
            continue
        
        # Rule based system
        flag_check=False
        record={
            "sender":sender,
            "date":date,
            "status":"",
            "company":"",
            "role":"",
            "user_id":"",
            "mail_id":""
        }
        
        if is_job_application(subject,layer1_keys):
            #check for status of the application and retrieve company name
            if is_job_application(body,layer2_keys):
                
                #status classification
                match = re.search(r'\b(' + '|'.join(layer2_keys) + r')\b', body)
                status = match.group(0) if match else "unknown"
                status=status_list[status_dict.get(status,0)]
                # comapany name extraction
                company=""
                for i in company_name_patterns:
                    match=re.search(i,body)
                    if match:
                        company=match.group(1)
                        break
                #position extraction
                role=""
                for i in role_patterns:
                    match=re.search(i,body)
                    if match:
                        role=match.group(1)
                        break
                record["status"]=status
                record["company"]=company
                record["role"]=role
                # store it in database
                record["user_id"]=user_id
                record["mail_id"]=msg_id
                print(msg_id,"------>regex")
                # insert into supabase
                #check if the record of the application exists
                existing_rec=(
                    db.table("job_applications").
                    select("user_id","mail_id").
                    eq("user_id",user_id).
                    eq("company",record.get("company")).
                    eq("role",record.get("role")).
                    execute()
                )
                # adding data based on existing record
                if existing_rec.data:
                    db.table("job_applications").update({"status":record.get("status")}).eq("user_id",record.get("user_id")).eq("company",record.get("company")).eq("role",record.get("role")).execute()
                else:
                    db.table("job_applications").insert(record).execute()

                #update the user_chkpt, the condition already checked above
                #check if the user is loggin in for the first time
                user_exists=db.table("user_chkpts").select("*").eq("user_id",record.get("user_id")).execute()
                if user_exists.data:
                    db.table("user_chkpts").update({"mail_id":record.get("mail_id"),"last_timestamp":date}).eq("user_id",record.get("user_id")).execute()
                else:
                    db.table("user_chkpts").insert({"user_id":record.get("user_id"),"mail_id":record.get("mail_id"),"last_timestamp":record.get("date")}).execute()
                # add to dataset
                # dataset for nlp based model
                db.table("dataset").insert({"subject":subject,"body":body,"target":record.get("status")}).execute()
            else:
               
                flag_check=True
        else:
            flag_check=True
        if flag_check:
            # LLM based parsing1
            part_record=await LLM_JobParser(subject,body)
            record={
                "company":part_record.get("company"),
                "sender":sender,
                "date":date,
                "status":status_list[part_record.get("status",0)],
                "role":part_record.get("role"),
                "user_id":user_id,
                "mail_id":msg_id,
            }
            if part_record.get("is_job_application"):
                print(msg_id,"------->llm")
                existing_rec=(
                        db.table("job_applications").
                        select("user_id","mail_id").
                        eq("user_id",user_id).
                        eq("company",record.get("company")).
                        eq("role",record.get("role")).
                        execute()
                    )
            
                # adding data based on existing record
                if existing_rec.data:
                    db.table("job_applications").update({"status":record.get("status")}).eq("user_id",record.get("user_id")).eq("company",record.get("company")).eq("role",record.get("role")).execute()
                else:
                    db.table("job_applications").insert(record).execute()

                #update the user_chkpt, the condition already checked above
                #check if the user is loggin in for the first time
                user_exists=db.table("user_chkpts").select("*").eq("user_id",record.get("user_id")).execute()
                if user_exists.data:
                    db.table("user_chkpts").update({"mail_id":record.get("mail_id"),"last_timestamp":date}).eq("user_id",record.get("user_id")).execute()
                else:
                    db.table("user_chkpts").insert({"user_id":record.get("user_id"),"mail_id":record.get("mail_id"),"last_timestamp":record.get("date")}).execute()

                # dataset for nlp based model
                db.table("dataset").insert({"subject":subject,"body":body,"target":record.get("status")}).execute()



        

    return msg_response.json()




if __name__=="__main__":
    uvicorn.run("server:app",host="127.0.0.1",port=8000,reload=True)