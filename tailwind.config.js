module.exports = {
  purge: {
    enabled: true,
    content: [
      './templates/**/*.html',
      './static/**/*.js',
    ],
    safelist: [
      // Statuts dynamiques (dashboard)
      'text-green-600', 'text-yellow-600', 'text-red-600', 'text-gray-500',
      // Email vérification (allauth)
      'bg-blue-50', 'border-blue-200', 'bg-yellow-50', 'border-yellow-200',
      'bg-blue-100', 'bg-yellow-100', 'text-blue-600', 'text-yellow-600',
      // Recharge package sélectionné
      'border-blue-500',
    ],
  },
  darkMode: false,
  theme: { extend: {} },
  variants: { extend: {} },
  plugins: [],
}
