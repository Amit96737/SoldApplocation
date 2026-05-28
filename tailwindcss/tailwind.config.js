/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        "../templates/**/*.html",
        "../static/js/**/*.js"
    ],
    theme: {
        fontSize: {
            sm: '0.84rem',
            base: '0.88rem',
            md: '0.92rem',
            lg: '0.94rem',
            xl: '0.98rem',
            xxl: '1.2rem'
        },
        extend: {
            fontFamily: {
                'primary': ['Inter']
            },
            colors: {
                'primary': '#2563EB',
                'text-color': '#636363',
            },
        },
    },
    plugins: [
        require('flowbite/plugin')
    ],
}