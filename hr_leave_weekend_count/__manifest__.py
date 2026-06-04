{
    "name": "Time Off - Count Weekend Days",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Time Off",
    "summary": "Add a 'Count Weekend Days' option to Time Off Types",
    "author": "Custom",
    "license": "AGPL-3",
    "depends": ["hr_holidays"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_leave_type_views.xml",
    ],
    "installable": True,
    "application": False,
}
