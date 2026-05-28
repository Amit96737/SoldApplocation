document.addEventListener('alpine:init', () => {
    Alpine.data('forumTopicsPage', () => ({
        searchFieldModel: "",
        formTopics: forum_topics,
        isLoading: false,

        get filteredTopics() {
            return this.formTopics.filter(i =>
                this.searchFieldModel.length === 0 ||
                i.title.toLowerCase().includes(this.searchFieldModel.toLowerCase())
            );
        },


        deleteTopic(topicId) {

            axios.delete(`/admin/api/forum/topic?id=${topicId}`, {
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