document.addEventListener('alpine:init', () => {
    Alpine.store('globalState', {
        getErrorMessage(err) {
            var errorMessage;
            if (err.response) {
                // Server responded with a status other than 2xx
                errorMessage = `Error: ${err.response.status} - ${err.response.data.message || err.response.statusText}`;
            } else if (err.request) {
                // No response was received
                errorMessage = 'Error: No response received from the server.';
            } else {
                // Error setting up the request
                errorMessage = `Error: ${err.message}`;
            }
            iziToast.error({
                title: '',
                message: errorMessage,
                position: 'topRight'
            });
        },
        statusClass: {
            'enabled': 'bg-green-400',
            'disabled': 'bg-red-400',
            'suspended': 'bg-yellow-400',
        }
    })
})
