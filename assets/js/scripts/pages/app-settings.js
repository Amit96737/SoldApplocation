document.addEventListener('alpine:init', () => {
    Alpine.data('settingsPage', () => ({
        isLoading: false,
        uploadImage(event) {
            const files = event.target.files;
            if (files.length > 0) {
                const reader = new FileReader();
                reader.onload = () => {
                    this.$refs.accountUploadImg.src = reader.result;
                };
                reader.readAsDataURL(files[0]);
            }
        },

        // Update profile function
        updateProfile() {
            this.isLoading = true;
            const formData = this.$refs.adminProfileForm;

            axios.patch(`/admin/api/settings/profile/update-profile`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }).then(response => {
                this.isLoading = false;
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        },
        // Change language status
        changeLanguageStatus(languageCode, languageId) {
            const checkBox = document.getElementById(`checkBox${languageId}`);

            axios.post(`/admin/api/settings/languages/change-status?lang_code=${languageCode}&value=${checkBox.checked}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                this.isLoading = false;
                iziToast.success({
                    title: 'Success!!',
                    message: "Language status updated successfully.",
                    position: 'topRight'
                });
            }).catch(error => {
                iziToast.error({
                    title: '',
                    message: "An error occurred while editing translation data",
                    position: 'topRight'
                });
            });
        },

        saveLocalization(key, index) {
            const localizationForm = document.getElementById(`localizationForm${index}`)

            const formData = new FormData(localizationForm)
            const data = {
                "key": key,
                "value": formData.get('trans-value')
            };

            axios.patch(`/admin/api/settings/localization?lang=${lang}`, JSON.stringify(data), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                this.isLoading = false;
                iziToast.success({
                    title: '',
                    message: "Translation edited successfully",
                    position: 'topRight'
                });
            }).catch(error => {
                this.isLoading = false;
                iziToast.error({
                    title: '',
                    message: "An error occurred while editing translation data",
                    position: 'topRight'
                });
            });
        }
    }))
})


