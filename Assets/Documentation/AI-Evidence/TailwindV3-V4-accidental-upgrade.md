# 🧠 Backlog Dev Guide — Tailwind v4 + DaisyUI Setup

## ⚙️ Prerequisites
- Node.js ≥ 18
- Django Tailwind (used for structure only)
- TailwindCSS v4.1.14
- DaisyUI v5.1.29

---

## 🏗️ File Structure
```
theme/
├── static_src/
│   ├── src/styles.css          → Tailwind input
│   ├── package.json            → Node build setup
│   └── postcss.config.js       → (no longer used, kept for legacy)
│
└── static/css/dist/styles.css  → Final compiled output
```

---

## 🧩 Commands

### Build production CSS
```bash
cd theme/static_src
npm run build
```

### Run Tailwind in watch mode (auto rebuild)
```bash
npm run dev
```

### Rebuild from scratch
```bash
rimraf ../static/css/dist && npm run build
```

---

## 🧭 Django Template Usage

Load Tailwind manually (don’t use `{% tailwind_css %}`):

```django
{% load static %}
<link rel="stylesheet" href="{% static 'css/dist/styles.css' %}">
```

---

## ✅ Notes
- Tailwind v4 no longer uses `content:` in `tailwind.config.js`; instead use `@source` in your CSS.
- DaisyUI loads automatically through Tailwind CLI.
- You can safely delete `django-tailwind` app files if not using the dev server.
