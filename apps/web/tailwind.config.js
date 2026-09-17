/** @type {import('tailwindcss').Config} */
// Tokens mirror docs/design/screens/samudra.css so the app matches the signed-off screens.
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: '#08337F', 2: '#1F4CA3' },
        peri: { DEFAULT: '#C1CBFF', soft: '#E6EAFF' },
        ink: '#1B1F2A',
        muted: '#56607A',
        faint: '#8A93A8',
        line: '#E3E7F0',
        canvas: '#F5F7FB',
        risk: { red: '#D64545', amber: '#D98A0B', green: '#1E9E6A' },
        zone: '#A3339A',
        storm: '#7C8AA5',
      },
      fontFamily: {
        head: ['"League Spartan"', 'Jost', 'sans-serif'],
        sans: ['Jost', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: { card: '12px', btn: '9px' },
      boxShadow: { card: '0 1px 2px rgba(8,51,127,.06), 0 8px 24px rgba(8,51,127,.10)' },
    },
  },
  plugins: [],
}
