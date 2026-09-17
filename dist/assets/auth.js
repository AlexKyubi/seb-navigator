import{AUTH_KEY,DATASET_KEY,loadSetting,saveSetting}from"./core.js";
import{readCommissionFile}from"./commission.js";

const $=id=>document.getElementById(id),form=$("authForm"),fileInput=$("authFile"),submit=$("authSubmit"),status=$("authStatus"),fileName=$("authFileName");
const cleanName=value=>String(value??"").trim().replace(/\s+/g," ");
const show=(message,type="")=>{status.textContent=message;status.dataset.type=type};

fileInput.onchange=()=>{const file=fileInput.files?.[0];fileName.textContent=file?file.name:"Файл не выбран";show("")};
form.onsubmit=async event=>{
  event.preventDefault();
  const firstName=cleanName($("firstName").value),lastName=cleanName($("lastName").value),file=fileInput.files?.[0];
  if(firstName.length<2||lastName.length<2){show("Введите имя и фамилию.","error");return}
  submit.disabled=true;show("Проверяю файл…","loading");
  try{
    const{dataset}=await readCommissionFile(file,{strict:true});
    await saveSetting(DATASET_KEY,dataset);
    await saveSetting(AUTH_KEY,{firstName,lastName,authorizedAt:new Date().toISOString(),validRows:dataset.summary.validRows});
    show("Доступ разрешён.","success");
    location.replace("./index.html");
  }catch{show("Файл не подходит для доступа.","error");fileInput.value="";fileName.textContent="Файл не выбран"}
  finally{submit.disabled=false}
};

(async()=>{const[profile,dataset]=await Promise.all([loadSetting(AUTH_KEY).catch(()=>null),loadSetting(DATASET_KEY).catch(()=>null)]);if(profile?.firstName&&profile?.lastName&&Array.isArray(dataset?.rows)&&dataset.rows.length)location.replace("./index.html")})();
