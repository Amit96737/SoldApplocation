document.addEventListener('alpine:init', () => {
    Alpine.data('settingsPage', () => ({
        isLoading: false, currentTab: 0, set activeTab(index) {
            this.currentTab = index;
        }, isTabActive(index) {
            return index === this.currentTab;
        }, uploadImage(event) {
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

        // Update password function
        changePassword() {
            this.isLoading = true;
            const formData = this.$refs.adminPasswordForm;

            axios.patch(`/admin/api/settings/profile/change-password`, formData, {
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

        // 

    }))
})


