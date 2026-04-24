module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs', 'node_modules'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh', 'react-hooks'],
  rules: {
    // Catches missing deps in useEffect/useCallback/useMemo — prevents stale closures & timer leaks
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',

    // Fast refresh compatibility — disabled: too many pre-existing files exporting helpers alongside components
    'react-refresh/only-export-components': 'off',

    // Too many pre-existing `any` usages — enforce gradually in a follow-up
    '@typescript-eslint/no-explicit-any': 'off',

    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
  },
};
