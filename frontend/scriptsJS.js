import {CONFIG} from "./config.js";

//------------------Global Variables------------------//
let GOOGLE_CLIENT_ID=CONFIG.GOOGLE_CLIENT_ID;
let API_BASE_URL=CONFIG.API_BASE_URL;

//------------------User context------------------//
// and eventlistner for google login
document.getElementById("google-login-btn").addEventListener("click",()=>{
    const redirect_uri="http://localhost:5500/frontend/callback.html";
    const scope = "openid email profile https://www.googleapis.com/auth/gmail.readonly";
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
            document.getElementById("job-dashboard").style.display="block";
            sessionStorage.setItem("user",token);
            fetchApplications(token);
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

// processing emails
async function fetchEmails(token){
    showLoading();
    const res=await fetch(`${API_BASE_URL}process-applications`,{
        headers:{ Authorization:`Bearer ${token}`}
    });
    const data=await res.json();
    hideLoading();
}


async function fetchApplications(token){
    const res = await fetch(`${API_BASE_URL}get-applications`,{
        headers:{Authorization:`Bearer ${token}`}
    });
     const data = await res.json();
    const container = document.querySelector(".job-applications");
    container.innerHTML = "";

    if (!data.applications || data.applications.length === 0) {
        container.innerHTML = `<div class="empty-state">No applications tracked yet</div>`;
        return;
    }

    data.applications.forEach(app => {
        const entry = document.createElement("div");
        entry.className = "job-application-entry";
        entry.innerHTML = `
            <div class="company">${app.company || "Unknown"}</div>
            <div class="position">${app.role || "Unknown"}</div>
            <div><span class="status-badge ${(app.status || "").toLowerCase()}">${app.status || "Unknown"}</span></div>
            <div class="date">${app.date ? app.date.split("T")[0] : "—"}</div>
        `;
        entry.addEventListener("click",()=>openEditModal(app));
        container.appendChild(entry);
    });

    // Update stat cards
    const apps = data.applications;
    document.querySelector(".card-indi:nth-child(1) .value-card").textContent = apps.length;
    document.querySelector(".card-indi:nth-child(2) .value-card").textContent = apps.filter(a => a.status === "Rejected").length;
    document.querySelector(".card-indi:nth-child(3) .value-card").textContent = apps.filter(a => ["interview", "offer", "assessment"].includes(a.status)).length;
}
//modal view for crud
function openEditModal(app){
    document.getElementById("editId").value=app.mail_id;
    document.getElementById("editCompany").value=app.company ||"";
    document.getElementById("editRole").value=app.role || "";
    document.getElementById("editStatus").value=app.status || "applied";
    document.getElementById("crudRow").classList.add("active");

}
//cancel button
document.getElementById('cancelEdit').addEventListener("click",()=>{
    document.getElementById("crudRow").classList.remove("active");
});
// save changes
document.getElementById("saveEdit").addEventListener("click",async ()=>{
    const id=document.getElementById("editId").value;
    const updated={
        company:document.getElementById("editCompany").value,
        role:document.getElementById("editRole").value,
        status:document.getElementById("editStatus").value
    };
    const token=sessionStorage.getItem("user");
    await fetch(`${CONFIG.API_BASE_URL}update-application/${id}`,{
        method:"PUT",
        headers:{
            "Authorization":`Bearer ${token}`,
            "Content-Type":"application/json"
        },
        body:JSON.stringify(updated)
    });
    document.getElementById("crudRow").classList.remove("active");
    fetchApplications(token);
})
//modal delete for each record
document.getElementById("deleteEdit").addEventListener("click",async ()=>{
    const token=sessionStorage.getItem("user");
    const id=document.getElementById("editId").value;
    await fetch(`${CONFIG.API_BASE_URL}delete-record/${id}`,{
        method:"DELETE",
        headers:{"Authorization":`Bearer ${token}`}
    });
    document.getElementById("crudRow").classList.remove('active');
    fetchApplications(token);

})

//------------------Functions------------------//\
document.getElementById("logoutBtn").addEventListener("click", () => {
    sessionStorage.clear();
    window.location.reload();
});
function showLoading(){
    document.getElementById("loadingOverlay").classList.add("active");
}
function hideLoading(){
    document.getElementById("loadingOverlay").classList.remove("active");
}
document.getElementById("refreshBtn").addEventListener("click",()=>{
    const token=sessionStorage.getItem("user");
    fetchEmails(token);
    fetchApplications(token);
})