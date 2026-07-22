const ids=["port","token","enabled","onlyBackground"], out=document.querySelector("#result");
chrome.storage.local.get({port:8765,token:"",enabled:true,onlyBackground:false}).then(v=>ids.forEach(id=>document.querySelector(`#${id}`).value=v[id]));
document.querySelector("#save").onclick=async()=>{const v={port:Number(port.value),token:token.value,enabled:enabled.checked,onlyBackground:onlyBackground.checked};await chrome.storage.local.set(v);out.textContent="Saved."};
document.querySelector("#test").onclick=()=>chrome.runtime.sendMessage({type:"test"},r=>out.textContent=r?.ok?"Blink queued.":`Test failed: ${r?.error||"unknown error"}`);
