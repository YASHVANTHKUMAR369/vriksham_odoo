{
    "name": "HR Expense Multi Level Approval",
    "version": "19.0.1.0",
    "depends": ["hr_expense", "mail"],
    "author": "Custom",
    "category": "Human Resources",
    "summary": "Dynamic multi level approval for expenses",
    "data": [
        "security/ir.model.access.csv",
        "views/approval_step_views.xml",
        "views/hr_expense_views.xml",
    ],
    "installable": True,
    "application": False,
    'license': 'LGPL-3',
}
