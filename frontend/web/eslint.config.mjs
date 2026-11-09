import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import jsxA11y from "eslint-plugin-jsx-a11y";
import prettier from "eslint-config-prettier/flat";
export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      ...jsxA11y.flatConfigs.recommended.rules,
      // Scrollable code and output regions must be keyboard reachable.
      "jsx-a11y/no-noninteractive-tabindex": [
        "error",
        { tags: ["pre", "ul"], roles: ["region"] },
      ],
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "src/types/api-schema.d.ts",
    "test-results/**",
    "playwright-report/**",
  ]),
  prettier,
]);
