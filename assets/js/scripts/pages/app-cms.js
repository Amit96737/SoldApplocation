document.addEventListener('alpine:init', () => {
    Alpine.data('cmsPage', () => ({
        blogEditor: null,
        isLoading: false,
        title: '',
        init() {
            const select = $('#cms-lang');
            const editor = '#blog-editor-container .editor';

            select.each(function () {
                const $this = $(this);
                $this.wrap('<div class="position-relative"></div>');

                $this.select2({
                    minimumResultsForSearch: Infinity,
                    dropdownAutoWidth: true,
                    dropdownParent: $this.parent()
                });

                select.val(`${lang}`).trigger('change');
            });

            select.on('select2:select', function (e) {
                const data = e.params.data;
                window.location = `/admin/cms/edit/${slug}?lang=` + data['text'];
            })


            // Snow Editor

            const Font = Quill.import('formats/font');
            Font.whitelist = ['sofia', 'slabo', 'roboto', 'inconsolata', 'ubuntu'];
            Quill.register(Font, true);

            this.blogEditor = new Quill(editor, {
                bounds: editor,
                modules: {
                    formula: false,
                    syntax: true,
                    toolbar: [
                        [
                            {
                                font: []
                            },
                            {
                                size: []
                            }
                        ],
                        ['bold', 'italic', 'underline', 'strike'],
                        [
                            {
                                color: []
                            },
                            {
                                background: []
                            }
                        ],
                        [
                            {
                                script: 'super'
                            },
                            {
                                script: 'sub'
                            }
                        ],
                        [
                            {
                                header: '1'
                            },
                            {
                                header: '2'
                            },
                            'blockquote',
                            'code-block'
                        ],
                        [
                            {
                                list: 'ordered'
                            },
                            {
                                list: 'bullet'
                            },
                            {
                                indent: '-1'
                            },
                            {
                                indent: '+1'
                            }
                        ],

                        ['link']
                    ]
                },
                theme: 'snow'
            });

            if(htmlContent != null){
                   this.blogEditor.root.innerHTML = htmlContent
            }
        },

        editCms() {
            const select = $('#cms-lang');
            this.isLoading = true;

            const formData = new FormData(this.$refs.editCmsForm);

            const data = {
                title: formData.get('title'),
                content: this.blogEditor.root.innerHTML,
            };

            const slug = this.$refs.slugTextField.value;
            const selectedValue = select.val();

            axios.patch(`/admin/cms/${slug}?lang=${selectedValue}`, JSON.stringify(data), {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                this.isLoading = false;
                iziToast.success({
                    title: '',
                    message: "Cms updated successfully",
                    position: 'topRight'
                });
            }).catch(error => {
                this.isLoading = false;
                iziToast.error({
                    title: '',
                    message: "An error occurred while updating cms content",
                    position: 'topRight'
                });
            });
        }
    }))
})


