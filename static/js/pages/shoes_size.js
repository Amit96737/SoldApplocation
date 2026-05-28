
document.getElementById('users-search').addEventListener('input', function () {
    console.log("Search input changed:", this.value);
    const searchValue = this.value.toLowerCase();
    const rows = document.querySelectorAll('#table tbody tr');

    rows.forEach(row => {
        const size = row.cells[0].textContent.toLowerCase();
        const type = row.cells[1].textContent.toLowerCase();

        if (size.includes(searchValue) || type.includes(searchValue)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
});


async function AddFormSubmit(event, formElement) {
    event.preventDefault(); 
    const save_btn = document.getElementById('save_btn');
    const formData = new FormData(formElement);
    save_btn.classList.remove('hidden');

        axios.post(`/admin/api/shop/shoes-size`, formData, {
            headers: {
                'Authorization': `${token}`,
                'Content-Type': 'application/json'
            }
        }).then(response => {
            iziToast.success({
                title: 'Success',
                message: response.data.detail,
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


async function EditFormSubmit(event, formElement, id) {
    event.preventDefault(); 
    const save_btn = document.getElementById('save_btn'+id);
    const formData = new FormData(formElement);
    save_btn.classList.remove('hidden');

        axios.patch(`/admin/api/shop/shoes-size/${id}`, formData, {
            headers: {
                'Authorization': `${token}`,
                'Content-Type': 'application/json'
            }
        }).then(response => {
            iziToast.success({
                title: 'Success',
                message: response.data.detail,
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


async function DeleteShoesSize(id) {
    try {
        const response = await axios.delete(`/admin/api/shop/shoes-size/${id}`, {
            headers: {
                'Authorization': `${token}`,
                'Content-Type': 'application/json'
            }
        });

        iziToast.success({
            title: 'Success',
            message: response.data.detail,
            position: 'topRight'
        });
        setTimeout(() => {
            window.location.reload();
        }, 4000);
    } catch (error) {
        console.error("Error deleting shoes size:", error);
        iziToast.error({
            title: '',
            message: "An error occurred:  "+error.message,
            position: 'topRight'
        });
    }
}
