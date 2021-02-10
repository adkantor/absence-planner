# Project description

Absence Planner application is a web based application enabling users to record, authorize and visualize vacation requests.

Absence Planner offers role-based tasks and authorizations. Users must log in to use the application,
certain views are limited to certain roles or the view varies based on the logged-in user's roles.

In order to properly use authorizations, users are ordered into hierarcy: each user needs to be provided with a superior.


## Features

- **Requests**
    - List active user's requests in a tabular format
    - Add new request via popup form
- **Approvals**
    - List pending approval tasks (i.e. requests made by direct subordinates) in a tabular format
    - Accept or decline via popup form
- **Calendar view**
    - View requests (depending on role: own / subordinates / whole organisation; all requests or approved absences only) in a calendar format
- **Administration**
    - Change password
    - Add new user
    - Update existing user's data
    - Add / update user allowances
    - List / add request types


## Roles

The following roles have been implemented in the application:

- **employee**: can create new requests; views own entries only in calendar view; can change its password
- **manager**: can authorize requests of direct subordinates; views entries of direct subordinates as well in calendar view
- **hr**: views approved requests af all users in calendar view; can add/update users, allowances and reqest types
- **admin**: can authorize requests of any users; views all entries in calendar view, can add/update users, allowances and reqest types
- **finance**: a role representing finance department
- **markenting**: a role representing marketing department

>**Note**: A user can have multiple roles, e.g.: a user with *employee* and *manager* can have its own requests
but can also authorize requests of its subordinates.


## Languages and frameworks

- Python, Flask (backend) using SQLite database
- Flask-User (authentication, role-based authorizations)
- Flask-SQLAlchemy (data models, database management)
- HTML, Bootstrap, JavaScript, JQuery (frontend)
- Font Awesome (icons)

## Improvement opportunities not yet implemented
- Allow user to modify or deactivate requests
- - Allow user to modify or deactivate request types
- Interactive calendar view (tooltips, create / modify / authorize requests)
- Advanced user management (e.g.: email confirmations, forgotten password)
- Email notification on tasks (e.g.:new approval task, request status change)
- Handling of weekends and public holidays.

## Author
Adam Kantor
