document.addEventListener('alpine:init', () => {
    Alpine.data('usersPage', () => ({
        searchFieldModel: "",
        usersList: usersList,
        select1: null,
        isLoading: false,

        get filteredUsers() {
            return this.usersList.filter(i =>
                this.searchFieldModel.length === 0 ||
                i.fullname.toLowerCase().includes(this.searchFieldModel.toLowerCase()) ||
                i.username.toLowerCase().includes(this.searchFieldModel.toLowerCase())
            );
        },

        deleteUser(userId) {
            this.isLoading = true;
            axios.delete(`/admin/api/user/${userId}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
            });
        },

        editUser(userId) {
            this.isLoading = true;
            const editUserForm = document.getElementById(`editUserForm${userId}`)
            const formData = new FormData(editUserForm)

            axios.patch(`/admin/api/user/${userId}`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            }).then(response => {
                window.location.reload();
            }).catch(error => {
                this.isLoading = false;
                this.$store.globalState.getErrorMessage(error);
            });
        },

        resetEditUser(index) {
            const user = this.filteredUsers[index];
            if (!user) return;

            const modal = document.getElementById('edit-user-modal' + index);
            if (!modal) return;

            modal.querySelectorAll('input').forEach(input => {
                const name = input.name;
                if (!name) return;

                if (input.type === 'file') {
                    input.value = "";
                    return;
                }

                if (user[name] !== undefined) {
                    input.value = user[name];
                }
            });

            modal.querySelectorAll('textarea').forEach(textarea => {
                const name = textarea.name;
                if (!name) return;

                if (user[name] !== undefined) {
                    textarea.value = user[name];
                }
            });

            modal.querySelectorAll('select').forEach(select => {
                const name = select.name;
                if (!name) return;

                if (user[name] !== undefined) {
                    select.value = user[name];
                }
            });
        }
    }))
})