import {CONFIG} from "./config.js";

//------------------Global Variables------------------//
let GOOGLE_CLIENT_ID=CONFIG.GOOGLE_CLIENT_ID;
let API_BASE_URL=CONFIG.API_BASE_URL;

//------------------User context------------------//
// and eventlistner for google login
document.getElementById("google-login-btn").addEventListener("click",()=>{
    const redirect_uri="http://localhost:5500/frontend/callback.html";
    const scope="https://www.googleapis.com/auth/gmail.readonly";
    const authUrl = "https://accounts.google.com/o/oauth2/v2/auth" +
                `?client_id=${GOOGLE_CLIENT_ID}` +
                `&redirect_uri=${encodeURIComponent(redirect_uri)}` +
                `&response_type=token` +
                `&scope=${encodeURIComponent(scope)}`;
    const popup = window.open(authUrl, "Google Login", "width=500,height=600");

    window.addEventListener("message", (event)=> {
        if (event.data.type=="google-auth"){
            const token=event.data.token;
            //display the dashboard and hide login button
            document.getElementById("login-screen").style.display="none";
            //document.getElementById("dashboard").style.display="block";
            sessionStorage.setItem("user",token);
            console.log(token);
            fetchEmails(token);
        };
    });
    async function fetchUserInfo(token){
        const res=await fetch("https://www.googleapis.com/oauth2/v3/userinfo",{
            headers:{ Authorization:`Bearer ${token}`}
        });
        const data=await res.json();
        


        
    }

});

//------------------State------------------//
async function fetchEmails(token){
    const res=await fetch(`${API_BASE_URL}job-applications`,{
        headers:{ Authorization:`Bearer ${token}`}
    });
    const data=await res.json();
    console.log(data);
}

//------------------Functions------------------//