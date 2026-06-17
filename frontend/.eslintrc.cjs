module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: ['react-app'],
  rules: {
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    'no-unused-vars': 'off',
  },
};
