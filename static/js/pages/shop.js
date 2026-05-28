document.addEventListener('alpine:init', () => {
    Alpine.data('shopPage', () => ({
        searchFieldModel: "",
        categories: typeof categories === 'undefined' ? [] : categories,
        subCategories: typeof subCategories === 'undefined' ? [] : subCategories,
        subCategoriesItems: typeof subCategoriesItems === 'undefined' ? [] : subCategoriesItems,
        colors: typeof colors === 'undefined' ? [] : colors,
        brands: typeof brands === 'undefined' ? [] : brands,
        sizes: typeof sizes === 'undefined' ? [] : sizes,
        translationData: {"en": "", "fr": "", "he": ""},
        localeList: ["en", "fr", "he"],
        isLoading: false,
        translationDataLocale: "en",
        setTranslationData(translation) {
            this.resetTranslationData().then(r => {
                this.translationData = translation;
            } );
        },
        async resetTranslationData() {
            this.translationData = {"en": "", "fr": "", "he": ""};
        },
        get filteredCategories() {
            return this.categories.filter(
                i => i["name"].toLowerCase().startsWith(this.searchFieldModel.toLowerCase())
            )
        },
//        get filteredSubCategoriesItems() {
//            return this.subCategoriesItems.filter(
//                i => i["name"].toLowerCase().startsWith(this.searchFieldModel.toLowerCase())
//            )
//        },
        get filteredSubCategories() {
            return this.subCategories.filter(
                i => i["name"].toLowerCase().startsWith(this.searchFieldModel.toLowerCase())
            )
        },
        get filteredBrands() {
            return this.brands.filter(
                i => i["name"].toLowerCase().startsWith(this.searchFieldModel.toLowerCase())
            )
        },
        get filteredColors() {
            return this.colors.filter(
                i => i["color_name"].toLowerCase().startsWith(this.searchFieldModel.toLowerCase())
            )
        },
        get filteredSizes() {
            return this.sizes.filter(
                i => i["size"].toLowerCase().startsWith(this.searchFieldModel.toLowerCase())
            )
        },
        set activeTranslationLocale(locale) {
            this.translationDataLocale = locale;
        },
        onEditTranslation(transTextCtrl) {
            const newTranslation = document.getElementById(transTextCtrl);
            let translationData = this.translationData;
            translationData[this.translationDataLocale] = newTranslation.value;
            this.translationData = translationData;
        },
        changePriority(categoryId, priority) {
          alert(priority)
          alert(categoryId)
            const payload = {
                'priority': priority
            };
            axios.patch(`/admin/api/shop/category/${categoryId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
//                window.location.reload();
            }).catch(error => {

            });
        },
        toggleIsFeatured(categoryId) {
            const checkBox = document.getElementById(`category-featured${categoryId}`);

            const payload = {
                'featured': checkBox.checked
            };
            axios.patch(`/admin/api/shop/category/${categoryId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        toggleStatus(categoryId) {
            const checkBox = document.getElementById(`category-status${categoryId}`);

            const payload = {
                'enabled': checkBox.checked
            };
            axios.patch(`/admin/api/shop/category/${categoryId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        deleteCategory(categoryId) {
            axios.delete(`/admin/api/shop/category/${categoryId}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        editCategory(categoryId) {
            const payload = {
                'name': this.translationData
            };

            axios.patch(`/admin/api/shop/category/${categoryId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        editColor(colorId) {
            const editColorFormData = document.getElementById(`editColorForm${colorId}`)
            const formData = new FormData(editColorFormData);

            const payload = {
                'color_name': this.translationData,
                'color_code': formData.get('color-code')
            };

            axios.patch(`/admin/api/shop/color/${colorId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        addNewCategory() {
            const payload = {
                'title': this.translationData
            };

            axios.post(`/admin/api/shop/category`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        deleteColor(colorId) {
            axios.delete(`/admin/api/shop/color/${colorId}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        addNewColor() {
            const editColorFormData = document.getElementById('addColorForm')
            const formData = new FormData(editColorFormData);
            const payload = {
                'color_title': this.translationData,
                'color_code': formData.get('color-code')
            };

            axios.post(`/admin/api/shop/color`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },

        resetEditColor(index) {
            const modal = document.getElementById('edit-color' + index);
            if (!modal) return;

            const input = modal.querySelector('input[name="title"]');
            if (!input) return;

            input.value = this.color[index].name;
        },

        resetAddColor() {
            const modal = document.getElementById('add-color');
            if (!modal) return;

            const input = modal.querySelector('input[name="title"]');
            const input_code = modal.querySelector('input[name="color-code"]');
            if (!input) return;
            input.value = '';
            input_code.value = '';
        },

        updateBrandStatus(brandId){
            const checkBox = document.getElementById(`brand-status${brandId}`);
            const payload = {
                'enabled': checkBox.checked,
            };

            axios.patch(`/admin/api/shop/brand/${brandId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        updateBrandFeature(brandId){
            const checkBox = document.getElementById(`brand-feature${brandId}`);
            const payload = {
                'featured': checkBox.checked,
            };

            axios.patch(`/admin/api/shop/brand/${brandId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        addNewBrand() {
            const addBrandForm = document.getElementById('addBrandForm')
            const formData = new FormData(addBrandForm);
            const payload = {
                'brand_name': formData.get('brand-name')
            };

            axios.post(`/admin/api/shop/brand`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        deleteBrand(brandId) {
            axios.delete(`/admin/api/shop/brand/${brandId}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },

      resetEditBrand(index) {
            const modal = document.getElementById('edit-brand' + index);
            if (!modal) return;

            const input = modal.querySelector('input[name="brand-name"]');
            if (!input) return;

            input.value = this.brands[index].name;
        },

        resetAddBrand() {
            const modal = document.getElementById('add-color');
            if (!modal) return;

            const input = modal.querySelector('input[name="brand-name"]');
            if (!input) return;
            input.value = '';
        },


        editBrand(brandId){
            const addBrandForm = document.getElementById(`editBrandForm${brandId}`)
            const formData = new FormData(addBrandForm);
            const payload = {
                'name': formData.get('brand-name')
            };

            axios.patch(`/admin/api/shop/brand/${brandId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        toggleSubCatStatus(subCategoryId) {
            const checkBox = document.getElementById(`sub-category-status${subCategoryId}`);

            const payload = {
                'enabled': checkBox.checked
            };
            axios.patch(`/admin/api/shop/sub-category/${subCategoryId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        toggleSubCatIsFeatured(subCategoryId) {
            const checkBox = document.getElementById(`sub-category-featured${subCategoryId}`);

            const payload = {
                'featured': checkBox.checked
            };
            axios.patch(`/admin/api/shop/sub-category/${subCategoryId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        deleteSubCategory(subcategoryId) {
            axios.delete(`/admin/api/shop/sub-category/${subcategoryId}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        addNewSubCategory() {
            const addNewSubCategoryForm = document.getElementById('subCategoryAddForm')
            const formData = new FormData(addNewSubCategoryForm);
            const payload = {
                'title': this.translationData,
                'parent_category_id': formData.get('parent_category')
            };

            axios.post(`/admin/api/shop/sub-category`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        editSubCategory(subCategoryId) {
            const payload = {
                'name': this.translationData
            };

            axios.patch(`/admin/api/shop/sub-category/${subCategoryId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        deleteSubCategoryItem(subcategoryItemId) {
            axios.delete(`/admin/api/shop/sub-categories/item/${subcategoryItemId}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        addNewSubCategoryItem(subCategoryId) {
            const payload = {
                'title': this.translationData,
            };

            axios.post(`/admin/api/shop/sub-category/${subCategoryId}/item`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        addNewSubSubCategoryItem(subCategoryId){
             const payload = {
                'title': this.translationData,
            };
            console.log(payload)

            axios.post(`/admin/api/shop/sub-sub-category/${subCategoryId}/item`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        addNewSubSubCategoryItemLevel(subCategoryId){
              const payload = {
                'title': this.translationData,
            };
            console.log("p", payload)
                 axios.post(`/admin/api/shop/sub-sub-category/level/${subCategoryId}/item`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        addNewSize() {
            const addSizeForm = document.getElementById('addSizeForm')
            const formData = new FormData(addSizeForm);
            const payload = {
                'size': formData.get('size')
            };

            axios.post(`/admin/api/shop/size`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        deleteSize(sizeId) {
            axios.delete(`/admin/api/shop/size/${sizeId}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
        editSize(sizeId) {
            const editSizeForm = document.getElementById(`editSizeForm${sizeId}`)
            const formData = new FormData(editSizeForm);

            const payload = {
                'size': formData.get('size')
            };

            axios.patch(`/admin/api/shop/size/${sizeId}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.$store.globalState.getErrorMessage(error);
            });
        },
    }))
})
