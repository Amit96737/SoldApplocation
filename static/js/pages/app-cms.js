document.addEventListener('alpine:init', () => {
    Alpine.data('appCms', () => ({
        isLoading: false,
        select1: null,
        quill: null,
        title: title,
        description: content,
        langList: ["en", "fr", "he"],
        titleLocale: "en",
        descriptionLocale: "en",
        init() {
            this.quill = new Quill('#editor', {
                theme: 'snow'
            });

              this.quill.root.innerHTML = this.description[this.descriptionLocale];

            // Listen for text change events
            this.quill.on('text-change', () => {
                let description = this.description;
                description[this.descriptionLocale] = this.quill.root.innerHTML;
                this.description = description;
            });


        },
        set activeTitleLocale(locale) {
            this.titleLocale = locale;
        },
        set activeDescriptionLocale(locale) {
            this.descriptionLocale = locale;
            this.quill.root.innerHTML = this.description[locale]; // Set new content
        },

        onEditTitle() {
            let title = this.title;
            title[this.titleLocale] = this.$refs.titleCtrl.value;
            this.title = title;
        },

        editCms(slug) {
            this.isLoading = true;
            const payload = {
                "title": this.title,
                "content": this.description,
            }
            axios.patch(`/admin/api/cms/edit/${slug}`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        },
        addCms() {
            this.isLoading = true;
            const payload = {
                "slug": this.$refs.cmsSlug.value,
                "title": this.title,
                "content": this.description,
            }
            axios.post(`/admin/api/cms`, JSON.stringify(payload), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location = `/admin/cms/${this.$refs.cmsSlug.value}`;
            }).catch(error => {
                this.isLoading = false;
                window.location.reload();
            });
        },
        deleteCms(slug) {
            this.isLoading = true;
            axios.delete(`/admin/api/cms/${slug}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {

            }).catch(error => {
                this.isLoading = false;
            });
        }
    }))
})