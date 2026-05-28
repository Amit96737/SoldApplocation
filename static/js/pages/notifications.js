document.addEventListener('alpine:init', () => {
    Alpine.data('notification', () => ({
        isLoading: false,
        select1: null,
        title: {"en": "", "fr": "", "he": ""},
        description: {"en": "", "fr": "", "he": ""},
        langList: ["en", "fr", "he"],

        init() {
            this.select1 = $('#mySelect2').select2({
                ajax: {
                    url: '/admin/notification/search',
                    data: function (params) {
                        return {
                            search: params.term
                        };
                    },
                    dataType: 'json',
                    delay: 500,
                    processResults: function (data) {
                        return {
                            results: data.map(function (repo) {
                                return {
                                    id: repo.id,
                                    text: repo.fullname,
                                    email_address: repo.email_address,
                                    image: repo.profile_pic
                                };
                            })
                        };
                    },
                    cache: true,
                },
                placeholder: 'Select first based on',
                minimumInputLength: 3,
                templateResult: formatRepo,
                templateSelection: formatRepoSelection
            });

            function formatRepo(repo) {
                if (repo.text === 'All' || !repo.id) {
                    return repo.text; // If no repo, return default text
                }
                return $(
                    '<ul role="list" class="divide-y divide-gray-200 dark:divide-gray-700">\n' +
                    '                <div class="flex items-center">\n' +
                    '                    <div class="flex-shrink-0">\n' +
                    '                        <img class="w-8 h-8 rounded-full" src="' + repo.image + '" alt="Neil image">\n' +
                    '                    </div>\n' +
                    '                    <div class="flex-1 min-w-0 ms-4">\n' +
                    '                        <p class="text-sm font-medium text-gray-900 truncate dark:text-white">\n' +
                    '                           ' + repo.text + '\n' +
                    '                        </p>\n' +
                    '                        <p class="text-sm text-gray-500 truncate dark:text-gray-400">\n' +
                    '                            ' + repo.email_address + '\n' +
                    '                        </p>\n' +
                    '                    </div>\n' +

                    '                </div>\n'
                );
            }

            function formatRepoSelection(repo) {
                if (repo.text === 'All' || !repo.id) {
                    return repo.text;
                }
                return $(
                    '<div class="select2-selection__repository flex items-center">' +
                    '<img src="' + repo.image + '" style="width: 22px; height: 22px; border-radius: 50%; margin-right: 5px;" alt=""/>' +
                    repo.text +
                    '</div>'
                );
            }
        },
        titleLocale: "en",
        descriptionLocale: "en",
        set activeTitleLocale(locale) {
            this.titleLocale = locale;
        },
        set activeDescriptionLocale(locale) {
            this.descriptionLocale = locale;
        },

        onEditTitle() {
            let title = this.title;
            title[this.titleLocale] = this.$refs.titleCtrl.value;
            this.title = title;
        },
        onEditDescription() {
            let description = this.description;
            description[this.descriptionLocale] = this.$refs.descriptionCtrl.value;

            this.description = description;
        },
        sendNotification() {
            // Access the form reference
            const notificationForm = this.$refs.notificationForm;
            const formData = new FormData(notificationForm);
            console.log(this.select1.val());
            formData.append('receiver',this.select1.val());
            formData.append('headings', JSON.stringify(this.title));
            formData.append('contents', JSON.stringify(this.description))
            console.info("here ", formData);
            console.info(this.description);

            axios.post(`/admin/api/notifications`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }).then(response => {
                this.isLoading = false;
                // window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        }
    }))
})




function addUserOptions() {
    const selectElement = document.getElementById('mySelect');
    selectElement.innerHTML = '';
    const customerOption = document.createElement('option');
    customerOption.value = 'customer';
    customerOption.textContent = 'Customer';

    const sellerOption = document.createElement('option');
    sellerOption.value = 'seller';
    sellerOption.textContent = 'Seller';

    selectElement.appendChild(customerOption);
    selectElement.appendChild(sellerOption);
}

function addLocationOptions() {
    const selectElement = document.getElementById('mySelect');
    selectElement.innerHTML = ''; // Clear existing options

    // Fetch locations from the API
    fetch('/admin/api/users/locations')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json(); // Parse the JSON response
        })
        .then(locations => {
            // Use a Set to avoid duplicate locations
            const uniqueLocations = new Set(locations);

            // Create option elements for each unique location
            uniqueLocations.forEach(location => {
                const option = document.createElement('option');
                option.value = location; // Set the value to the location
                option.textContent = location; // Set the display text to the location
                selectElement.appendChild(option); // Append the option to the select element
            });
        })
        .catch(error => {
            console.error('There was a problem with the fetch operation:', error);
        });
}

function handleSelectChange() {
    const selectElement = document.getElementById('basedon');
    const selectedValue = selectElement.value;

    switch (selectedValue) {
        case 'user':
            console.log('User  selected');
            addUserOptions()
            break;
        case 'location':
            console.log('Location selected');
            addLocationOptions()
            break;
        case 'activity':
            console.log('Activity selected');
            break;
        default:
            console.log('No valid selection');
            break;
    }
}

