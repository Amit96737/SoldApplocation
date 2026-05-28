document.addEventListener('alpine:init', () => {
    Alpine.data('authentications', () => ({
        isLoading: false,

        loginUser() {
            this.isLoading = true;
            const loginForm = this.$refs.loginForm;
            const formData = new FormData(loginForm);
            const expires = "";
            axios.post('/admin/login', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                withCredentials: true
            }).then(response => {
                this.isLoading = false;
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
               this.getErrorMessage(error);
            });
        },

        getErrorMessage(err) {
            var errorMessage;
            if (err.response) {
                // Server responded with a status other than 2xx
                errorMessage = `Error: ${err.response.status} - ${err.response.data.message || err.response.statusText}`;
            } else if (err.request) {
                // No response was received
                errorMessage = 'Error: No response received from the server.';
            } else {
                // Error setting up the request
                errorMessage = `Error: ${err.message}`;
            }

            console.log(errorMessage);

            iziToast.error({
                title: '',
                message: errorMessage,
                position: 'topRight'
            });
        }

    }))
})