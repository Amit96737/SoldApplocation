

document.addEventListener("DOMContentLoaded",async  function() {
    const inputs = document.querySelectorAll(".translatable");
    try{
        const response = await fetch('/api/v1/app-config/locale/translation?language_code=fr');
        const translations = await response.json(); 
        console.log("here")
        inputs.forEach(input => {
            const key = input.getAttribute("data-key");
            input.value = translations[key] || "";
        });
        }
    catch(error){
        console.error("Failed to load translations:", error);
    }

  });





document.addEventListener("DOMContentLoaded",async  function() {
    const inputs = document.querySelectorAll(".translatable_he");
    try{
        const response = await fetch('/api/v1/app-config/locale/translation?language_code=he');
        const translations = await response.json(); 
        console.log("here")
        inputs.forEach(input => {
            const key = input.getAttribute("data-key");
            input.value = translations[key] || "";
        });
        }
    catch(error){
        console.error("Failed to load translations:", error);
    }

  });


