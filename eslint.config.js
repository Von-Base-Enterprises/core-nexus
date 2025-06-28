import js from '@eslint/js';
import globals from 'globals';

export default [
  js.configs.recommended,
  {
    languageOptions: {
      globals: {
        ...globals.node,
        ...globals.es2022,
      },
      ecmaVersion: 2022,
      sourceType: 'module',
    },
    rules: {
      'no-unused-vars': 'warn',
      'no-console': 'off',
    },
    ignores: [
      'node_modules/**',
      '.yarn/**',
      'dist/**',
      'build/**',
      '**/*.min.js',
      'python/**',
      'jarvis/**',
      '*.json',
      '*.md',
      '*.yml',
      '*.yaml',
    ],
  },
];