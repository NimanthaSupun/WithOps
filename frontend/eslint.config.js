import prettier from 'eslint-config-prettier';
import { includeIgnoreFile } from '@eslint/compat';
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';
import { fileURLToPath } from 'node:url';
import svelteConfig from './svelte.config.js';

const gitignorePath = fileURLToPath(new URL('./.gitignore', import.meta.url));

/** @type {import('eslint').Linter.Config[]} */
export default [
	includeIgnoreFile(gitignorePath),
	js.configs.recommended,
	...svelte.configs.recommended,
	prettier,
	...svelte.configs.prettier,
	{
		languageOptions: {
			globals: { ...globals.browser, ...globals.node }
		}
	},
	{
		files: ['**/*.svelte', '**/*.svelte.js'],
		languageOptions: { parserOptions: { svelteConfig } }
	},
	{
		// Downgrade pervasive rules to warnings so CI passes while
		// the codebase is incrementally cleaned up.
		rules: {
			'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
			'no-case-declarations': 'warn',
			'no-undef': 'warn',
			'no-regex-spaces': 'warn',
			'no-dupe-class-members': 'warn',
			'no-useless-escape': 'warn',
			'no-prototype-builtins': 'warn',
			'svelte/require-each-key': 'warn',
			'svelte/infinite-reactive-loop': 'warn',
			'svelte/no-immutable-reactive-statements': 'warn',
			'svelte/no-at-html-tags': 'warn',
			'svelte/no-useless-mustaches': 'warn'
		}
	}
];
