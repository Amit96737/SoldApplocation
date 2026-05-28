

async function handleFormSubmit(event, formElement) {
    event.preventDefault(); 

    const formData = new FormData(formElement);
  
        axios.post(`/api/v1/subscription/plan`, formData, {
            headers: {
                'Authorization': `${token}`,
                'Content-Type': 'application/json'
            }
        }).then(response => {
            iziToast.success({
                title: 'Success',
                message: response.data.message,
                position: 'topRight'
            });
            setTimeout(() => {
                window.location.reload();
            }, 4000);
        }).catch(error => {
            console.error("Form submission failed:", error);
            iziToast.error({
                title: '',
                message: "An error occurred:  "+error.message,
                position: 'topRight'
            });
        });

}



async function DeletePlan(planId) {

    console.log("Deleting plan with ID:", planId);
    try {
        const response = await axios.delete(`/api/v1/subscription/plan/${planId}`, {
            headers: {
                'Authorization': `${token}`,
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            console.log("Plan deleted successfully:", response.status);
            iziToast.success({
                title: 'Success',
                message: response.data.message,
                position: 'topRight'
            });
            setTimeout(() => {
                window.location.reload();
            }, 3200);
        })
        .catch(error => {
            const errorMessage = error.response?.data?.detail || "You can't delete because users may subscribe this plan. you can only update the plan.";
            iziToast.error({
                title: 'Error',
                message: errorMessage,
                position: 'topRight'
            });
        });

    } catch (error) {
        console.error("Error deleting plan:", error);
        iziToast.error({
            title: '',
            message: "An error occurred:  "+error.message,
            position: 'topRight'
        });
    }

}


async function UpdatePlan(event, formElement) {
    event.preventDefault(); 

    const formData = new FormData(formElement);
    console.log("Updating plan with data:", formData);
    console.log("Form data:", formData.get("id"));
  
        axios.patch(`/api/v1/subscription/plan/${formData.get("id")}`, formData, {
            headers: {
              Authorization: `${token}`,
              "Content-Type": "application/json",
            },
          })
          .then((response) => {
            iziToast.success({
              title: "Success",
              message: response.data.message,
              position: "topRight",
            });
            setTimeout(() => {
              window.location.reload();
            }, 2000);
          })
          .catch((error) => {
            console.error("Form submission failed:", error);
            iziToast.error({
              title: "",
              message: "An error occurred:  " + error.message,
              position: "topRight",
            });
          });

}
