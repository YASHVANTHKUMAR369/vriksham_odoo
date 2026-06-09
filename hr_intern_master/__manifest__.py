{
    "name": "HR Intern Master",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "summary": "Manage interns with offer letter and completion certificate",
    "author": "ICore",
    "license": "LGPL-3",
    "depends": ["base", "hr", "mail", "web"],
    "data": [
        "security/intern_groups.xml",
        "security/ir.model.access.csv",
        "report/intern_report.xml",
        "views/intern_master_views.xml",
    ],
    "installable": True,
}
