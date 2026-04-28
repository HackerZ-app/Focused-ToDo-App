#To-DO App

A modern, full-stack Multi-Page Application (MPA) designed for deep work, strategic planning, and consistent productivity. Built with a high-performance **No-Build** stack.

---

## ✨ Key Features

### 🛠️ Strategic Kanban Board
Visualize your workflow with a 3-column strategic board. Move tasks from **To-Do** to **Done** with zero-latency HTMX updates.

### ⏱️ Pomodoro Focus Mode
A distraction-free "Deep Work" zone. Features a minimalist 25-minute timer that automatically completes your selected task in the database when the clock hits zero.

### 📈 Insights & Consistency Heatmap
A dedicated analytics dashboard featuring:
- **GitHub-style Heatmap**: A 30-day visual representation of your daily task completion.
- **Gamification System**: Unlock badges (3, 5, 10, 20 tasks) and maintain daily streaks to encourage consistency.

### 💎 High-End UI/UX
- **3D Isometric Loader**: A custom-engineered CSS 3D engine for cinematic page transitions.
- **Dark Mode First**: Fully responsive design with smooth theme transitions.
- **FastAPI Auth**: Secure JWT-based authentication with HTTP-only cookies.

---

## 🏗️ System Architecture

Unlike traditional React apps, this suite uses an **MPA-First** approach.
- **Backend**: FastAPI (Python) handles logic, security, and data aggregation.
- **Frontend**: Jinja2 templates serve as the "Skeleton."
- **Interactivity**: HTMX performs "Partial Swaps," allowing the app to feel like a Single Page App (SPA) while maintaining the lightweight footprint of an MPA.

---

