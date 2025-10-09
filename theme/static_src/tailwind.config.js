/**
 * Tailwind CSS v4 configuration for the theme app.
 *
 * This file registers the DaisyUI plugin and sets `content` globs so Tailwind
 * and the editor's intellisense can find template and source files.
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "../../**/*.{html,js,py}",
    "../../../**/*.{html,js,py}",
    "../../../../templates/**/*.html",
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: ["light", "dark"],
  },
};