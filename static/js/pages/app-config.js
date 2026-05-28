document.addEventListener('alpine:init', () => {
    Alpine.data('appConfigPage', () => ({
        isLoading: false,
        selectedFileName: '',
        uploadImage(event) {
            const files = event.target.files;
            if (files.length > 0) {
                const reader = new FileReader();
                reader.onload = () => {
                    this.$refs.accountUploadImg.src = reader.result;
                    this.selectedFileName = event.target.files[0].name
                };
                reader.readAsDataURL(files[0]);
            }
        },

        updatePaymentMethodStatus(paymentMethodID) {
            const checkBox = document.getElementById(`pm-${paymentMethodID}`);

            axios.post(`/admin/api/payment-method?id=${paymentMethodID}&status=${checkBox.checked}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        },

        updatePM(paymentMethodID) {
            this.isLoading = true;
            const formData = this.$refs.pmForm;

            axios.patch(`/admin/api/payment-method?id=${paymentMethodID}`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
                this.$store
            });
        },

        // // Update profile function
        updateAppConfig() {
            this.isLoading = true;
            const formData = this.$refs.appConfigForm;

            axios.patch(`/admin/api/app-config`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);

                this.isLoading = false;
            });
        },
    }))
})


