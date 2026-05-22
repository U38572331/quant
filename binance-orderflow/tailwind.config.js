/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'buy-green': '#1dbf73',
                'sell-red': '#f6465d',
                'dark-bg': '#0b0e11', // Slightly darker for more contrast
                'card-bg': '#161a1e',
                'grid-line': '#1e2329',
                'text-primary': '#eaecef',
                'text-secondary': '#848e9c',
                'neon-blue': '#22d3ee',
                'neon-purple': '#a855f7',
                'poc-yellow': '#facc15',
                'accent-blue': '#3b82f6',
            },
            fontFamily: {
                mono: ['"Roboto Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
            }
        },
    },
    plugins: [],
}
