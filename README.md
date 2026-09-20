# CivicResolve

CivicResolve is a local-first Python + SQLite prototype for structured public-service grievance tracking and operational analysis.

It is an educational portfolio project. It is **not connected to CPGRAMS or any government database**.

## Why this project?

Public grievance systems need structured records, status tracking, prioritisation, duplicate detection, deadlines, and reporting. CivicResolve models those workflows in a small, inspectable system.

## Features

- SQLite database
- Create and manage grievance records
- Categories, areas and priorities
- Status workflow: Open → In Progress → Resolved / Rejected
- Due-date and overdue tracking
- Search across issue, category and area
- Basic duplicate detection using text similarity
- CSV export for analysis/reporting
- Responsive browser interface
- No third-party Python packages required

## Tech Stack

- Python 3
- SQLite
- HTML/CSS
- Python standard library HTTP server
- `difflib.SequenceMatcher` for similarity checking

## Run locally

```bash
python app.py
```

Then open:

`http://127.0.0.1:8000`

On Android with Pydroid, run `app.py` and open the same address in the phone browser.

## Database

The SQLite database is created automatically at:

`data/civicresolve.db`

The repository does not require a pre-built database.

## Data note

The included records are fictional demo data. Do not upload personal or confidential grievance information to a public repository.

## Portfolio value

This project demonstrates:

- Python application structure
- Relational database design
- SQL-backed CRUD operations
- Data validation
- Basic algorithmic similarity matching
- Operational metrics
- Exportable data
- Documentation

## Future scope

- Role-based access
- Authentication
- REST API
- Better NLP-based duplicate classification
- Charts and trend analysis
- PostgreSQL deployment
- Accessibility improvements
- Audit log
- Unit and integration tests

## Project presentation

For a portfolio, describe the project as a prototype for structured grievance operations rather than as an official government system.

Recommended GitHub repository description:

> Python + SQLite prototype for grievance tracking, prioritisation, duplicate detection and operational reporting.

Recommended topics:

`python` `sqlite` `sql` `data-analysis` `e-governance` `database` `portfolio-project`

