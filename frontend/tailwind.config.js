/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'risk-low': '#10b981',
        'risk-medium': '#f59e0b',
        'risk-high': '#ef4444',
        'status-resolved': '#10b981',
        'status-pending': '#f59e0b',
        'status-executing': '#3b82f6',
        'status-escalated': '#ef4444',
      }
    },
  },
  plugins: [],
}
