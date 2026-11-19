// ESLint flat config for the Expo SDK 58 template (per eslint-config-expo docs).
const { defineConfig, globalIgnores } = require('eslint/config');

const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  globalIgnores(['dist/*', 'node_modules/*', '.expo/*', '.expo-shared/*']),
]);
