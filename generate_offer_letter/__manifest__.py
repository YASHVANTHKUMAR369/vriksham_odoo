{
    "name": "HR Offer Letter",
    "version": "1.0",
    "category": "Human Resources",
    "depends": ["base", "web", "hr", "hr_recruitment"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "report/job_offer_letter.xml",
        "wizard/job_offer_letter_wizard.xml",
        "views/hr_applicant_view.xml",
    ],
    'author': 'yash',
    'license': 'LGPL-3',
    "installable": True,
}
