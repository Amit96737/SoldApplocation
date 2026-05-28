document.addEventListener('alpine:init', () => {
    Alpine.data('languagesPage', () => ({
        isLoading: false, uploadImage(event) {
            const files = event.target.files;
            if (files.length > 0) {
                const reader = new FileReader();
                reader.onload = () => {
                    this.$refs.accountUploadImg.src = reader.result;
                };
                reader.readAsDataURL(files[0]);
            }
        },

        // Add Translation function
        addTranslation() {
            this.isLoading = true;
            const formData = this.$refs.addTranslationForm;

            axios.post(`/admin/api/localization`, formData, {
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
        changeLanguageStatus(languageCode) {
            const checkBox = document.getElementById(`lang-${languageCode}`);

            axios.patch(`/admin/api/language?code=${languageCode}`, {
                'status': checkBox.checked
            }, {
                headers: {
                    'Content-Type': 'application/json'
                },

            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        },

        saveLocalization(key, index) {
            const localizationValue = document.getElementById(`transInput${index}`)

            const data = {
                "key": key,
                "value": localizationValue.value
            };

            axios.patch(`/admin/api/settings/localization?lang=${lang}`, JSON.stringify(data), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                this.isLoading = false;
                iziToast.success({
                    title: '', message: "Translation edited successfully", position: 'topRight'
                });
            }).catch(error => {
                this.isLoading = false;
                iziToast.error({
                    title: '', message: "An error occurred while editing translation data", position: 'topRight'
                });
            });
        }
    }))
})

