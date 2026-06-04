# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "HR Attendance Mass Create",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Attendances",
    "summary": "Create attendances for all employees in a date range",
    "author": "Custom",
    "license": "AGPL-3",
    "depends": ["hr_attendance"],
    "installable": True,
    "data": [
        "security/ir.model.access.csv",
        "views/hr_attendance_mass_create_wizard_views.xml",
    ],
}
