TEST_CREDENTIALS = {
    "2024001": {
        "email": "student1@ue.edu.ph",
        "access_code": "ACCESS123",
        "name": "Maria Santos",
        "program": "BS Psychology",
        "year": 2,
    },
    "2024002": {
        "email": "student2@ue.edu.ph",
        "access_code": "ACCESS456",
        "name": "Juan dela Cruz",
        "program": "BS Computer Science",
        "year": 3,
    },
    "2024003": {
        "email": "student3@ue.edu.ph",
        "access_code": "ACCESS789",
        "name": "Ana Reyes",
        "program": "BS Nursing",
        "year": 1,
    },
    # Counselor accounts are recognized by role == "counselor", so adding a
    # counselor is a change to this table, not to app/api/auth.py. Names are
    # deliberately generic until real staff are onboarded.
    "COUNSELOR01": {
        "email": "counselor01",
        "access_code": "counsel123",
        "name": "Dr. Patricia Lim",
        "role": "counselor",
    },
    "COUNSELOR02": {
        "email": "counselor02",
        "access_code": "counsel202",
        "name": "Guidance Counselor 2",
        "role": "counselor",
    },
    "COUNSELOR03": {
        "email": "counselor03",
        "access_code": "counsel303",
        "name": "Guidance Counselor 3",
        "role": "counselor",
    },
    "COUNSELOR04": {
        "email": "counselor04",
        "access_code": "counsel404",
        "name": "Guidance Counselor 4",
        "role": "counselor",
    },
    "COUNSELOR05": {
        "email": "counselor05",
        "access_code": "counsel505",
        "name": "Guidance Counselor 5",
        "role": "counselor",
    },
}