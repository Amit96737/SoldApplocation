document.addEventListener('alpine:init', () => {
    Alpine.data('bannersPage', () => ({
        searchFieldModel: "",
        banners: banners,
        isLoading: false,
        get filteredBanners() {
            return this.banners.filter(
                i => i["redirect_path"].toLowerCase().startsWith(this.searchFieldModel.toLowerCase())
            )
        },
        uploadBannerImage(event, targetId) {
            console.log(targetId);
            const files = event.target.files;
            if (files.length > 0) {
                const reader = new FileReader();
                reader.onload = () => {
                    document.getElementById(targetId).src = reader.result;
                };
                reader.readAsDataURL(files[0]);
            }
        },
        setImage(img, targetId) {
            document.getElementById(targetId).src = img;
        },
        updateBannerStatus(bannerId) {
            const checkBox = document.getElementById(`banner-${bannerId}`);

            const formData = new FormData();
            formData.append("enabled", checkBox.checked);

            axios.patch(`/admin/api/banner/${bannerId}`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        },
        addBanner() {
            this.isLoading = true;
            const addBannerForm = this.$refs.addBannerForm;
            const formData = new FormData(addBannerForm);

            if (formData.get('banner_img').size === 0) {
                iziToast.info({
                    title: '',
                    message: "Upload banner image",
                    position: 'topRight'
                });
                this.isLoading = false;
                return;
            }

            axios.post(`/admin/api/banner`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        },

        editBanner(bannerId) {
            this.isLoading = true;
            const editBannerForm =  document.getElementById(`editBannerForm${bannerId}`);
            const formData = new FormData(editBannerForm);

            axios.patch(`/admin/api/banner/${bannerId}`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        },

        deleteBanner(bannerId) {
            axios.delete(`/admin/api/banner/${bannerId}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        },
    }))
})
