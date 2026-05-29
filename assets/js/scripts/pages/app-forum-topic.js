document.addEventListener('alpine:init', () => {
    Alpine.data('forumTopicPage', () => ({
        isLoading: false,
        // Delete forum topic function
        deleteForumTopic(topicId) {
            Swal.fire({
                title: 'Are you sure?',
                text: "You won't be able to revert this!",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Yes, delete it!',
                customClass: {
                    confirmButton: 'btn btn-primary',
                    cancelButton: 'btn btn-outline-danger ml-1'
                },
                buttonsStyling: false
            }).then(function (result) {
                if (result.value) {
                    axios.delete(`/admin/api/forum/topic?topicId=${topicId}`, {
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    }).then(response => {
                        this.isLoading = false;
                        Swal.fire({
                            icon: 'success',
                            title: 'Deleted!',
                            text: 'Topic has been deleted.',
                            customClass: {
                                confirmButton: 'btn btn-success'
                            }
                        }).then(function (result) {
                            window.location.reload();
                        });
                    }).catch(error => {
                        this.isLoading = false;
                    });

                } else if (result.dismiss === Swal.DismissReason.cancel) {
                    Swal.fire({
                        title: 'Cancelled',
                        text: 'Your imaginary file is safe :)',
                        icon: 'error',
                        customClass: {
                            confirmButton: 'btn btn-success'
                        }
                    });
                }
            });
        },
    }))
})


