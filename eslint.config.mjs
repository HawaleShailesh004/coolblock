// Shared flat config for packages/* (non-Next TS packages). apps/web carries
// its own Next-specific config (apps/web/eslint.config.mjs).
import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      globals: { ...globals.node, ...globals.browser },
    },
  },
  {
    ignores: ["**/dist/**", "**/.turbo/**", "**/node_modules/**", "**/.next/**", "**/generated/**"],
  },
);
