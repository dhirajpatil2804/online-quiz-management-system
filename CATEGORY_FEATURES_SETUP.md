# Category Management Feature Update

This update adds category management to the existing Flask Online Quiz Management System.

## Features included

- Admin can create main categories and one level of subcategories.
- Admin can assign multiple active categories to each teacher and student.
- Teachers can create and edit quizzes only in categories assigned to them.
- Students see published quizzes only from categories assigned to them.
- Student quiz start, instructions, and active attempt routes check category assignment server-side.
- Previously submitted quiz results remain available to the student who owns the attempt.
- Admin dashboard includes a Category Management link.

## Important behavior

Assignments are exact category assignments. For example, assigning `Data Science` does not automatically assign its `Power BI` subcategory; assign both if needed.

Existing quizzes with no category are not shown to students. A teacher may edit an unattempted existing quiz and choose one of their assigned categories. Existing submitted results and attempt data are not deleted.

## Apply to your working project

1. Keep your current project and database backup. Do not replace the database or rerun old migrations.
2. Copy the updated `app` folder from this package into your project folder, allowing the updated source/templates to replace matching files.
3. Do not copy or create a `.env` file from this package; it is intentionally excluded. Keep credentials in your own local `.env` and Render environment settings.
4. Run locally with your virtual environment activated:
   ```bat
   python -m flask --app run routes
   python -m flask --app run run
   ```
5. Sign in as admin and open **Category Management** from the admin dashboard.
6. Create main categories and subcategories, assign categories to teachers and students, then test with separate accounts.
7. Test a teacher attempting to submit a category that was not assigned (the server should reject it) and a student opening a quiz URL from an unassigned category (the server should reject it).
8. Commit and push the source changes, then deploy on Render. Ensure Render's `DATABASE_URL` contains your rotated Neon credentials.

## Security

This package excludes `.env`, `.git`, virtual environments, and Python cache files. Never commit database passwords or secret keys to GitHub. If any credential was exposed, rotate it and update local/Render settings.

## Validation note

The modified Python files passed Python syntax compilation during preparation. Run the app and exercise the workflows in your own environment before deploying to production.
